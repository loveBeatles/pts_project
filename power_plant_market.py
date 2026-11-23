from __future__ import annotations
import json
import random
from typing import Sequence
from power_grid.interfaces import (
    InterfacePowerPlantMarket,
    InterfacePowerPlantMarketCheckAndBumpStep,
    InterfaceShuffler,
)
from power_grid.simple_types import PowerPlant, PowerPlantNumber, RequestError


class RandomShuffler(InterfaceShuffler):
    def shuffle(self, power_plants: Sequence[PowerPlant]) -> list[PowerPlant]:
        return random.sample(list(power_plants), len(power_plants))


class PowerPlantMarket(InterfacePowerPlantMarket, InterfacePowerPlantMarketCheckAndBumpStep):
    """Visible power plants plus the draw stack.

    Steps 1 and 2: 8 visible plants, the 4 cheapest form the current market
    (can be bought), the other 4 the future market.
    Step 3: up to 6 visible plants, all of them can be bought.

    The Step 3 card lies under `deck`. Plants returned under the stack go below
    it. When the card is drawn, plants below it are shuffled to form a new stack
    and is_step3_start() becomes true.
    """
    VISIBLE_BEFORE_STEP3 = 8
    CURRENT_BEFORE_STEP3 = 4
    VISIBLE_IN_STEP3 = 6

    _visible: list[PowerPlant]
    _deck: list[PowerPlant]
    _below_step3_card: list[PowerPlant]
    _step3_card_drawn: bool
    _step: int
    _shuffler: InterfaceShuffler

    def __init__(self, visible: Sequence[PowerPlant], deck: Sequence[PowerPlant],
                 shuffler: InterfaceShuffler) -> None:
        """deck is ordered from top to bottom; the Step 3 card is under it."""
        assert len(visible) <= PowerPlantMarket.VISIBLE_BEFORE_STEP3
        numbers = [p.number for p in list(visible) + list(deck)]
        assert len(numbers) == len(set(numbers))
        self._visible = sorted(visible, key=lambda p: p.number)
        self._deck = list(deck)
        self._below_step3_card = []
        self._step3_card_drawn = False
        self._step = 1
        self._shuffler = shuffler

    def _current_market_size(self) -> int:
        if self._step == 3:
            return PowerPlantMarket.VISIBLE_IN_STEP3
        return PowerPlantMarket.CURRENT_BEFORE_STEP3

    def _current_market(self) -> list[PowerPlant]:
        return self._visible[:self._current_market_size()]

    def _draw(self) -> None:
        """Draws one card and puts it to the visible plants (if it is a plant)."""
        if self._deck:
            self._visible.append(self._deck.pop(0))
            self._visible.sort(key=lambda p: p.number)
        elif not self._step3_card_drawn:
            self._step3_card_drawn = True
            self._deck = self._shuffler.shuffle(self._below_step3_card)
            self._below_step3_card = []

    def _put_under_deck(self, plant: PowerPlant) -> None:
        if self._step3_card_drawn:
            self._deck.append(plant)
        else:
            self._below_step3_card.append(plant)

    def _remove_lowest(self) -> None:
        if self._visible:
            self._visible.pop(0)

    def can_take_power_plant(self, ppn: PowerPlantNumber, price: int) -> RequestError | None:
        if all(p.number != ppn for p in self._current_market()):
            return RequestError(f"Power plant {ppn.number} is not in the current market.")
        if price < ppn.number:
            return RequestError(f"Minimal bid for power plant {ppn.number} is {ppn.number}.")
        return None

    def take_power_plant(self, ppn: PowerPlantNumber) -> PowerPlant:
        plant = next(p for p in self._current_market() if p.number == ppn)
        self._visible.remove(plant)
        self._draw()
        return plant

    def remove_lowest_power_plant(self) -> None:
        """Used when nobody bought a plant during the auction phase."""
        self._remove_lowest()
        self._draw()

    def remove_power_plants_cheaper_than(self, value: int) -> None:
        """Removes plants whose number is not higher than value (the number of
        houses of the leading player) and replaces them."""
        while self._visible and self._visible[0].number.number <= value:
            self._remove_lowest()
            self._draw()

    def prepare_next_turn(self) -> None:
        """Bureaucracy: in steps 1 and 2 the highest plant goes under the stack,
        in step 3 the lowest plant is removed from the game."""
        if not self._visible:
            return
        if self._step == 3:
            self._remove_lowest()
        else:
            self._put_under_deck(self._visible.pop())
        self._draw()

    def is_step3_start(self) -> bool:
        return self._step3_card_drawn and self._step < 3

    def start_step2(self) -> None:
        assert self._step == 1
        self._step = 2
        self._remove_lowest()
        self._draw()

    def start_step3(self) -> None:
        assert self._step < 3
        self._step = 3
        self._remove_lowest()
        if not self._step3_card_drawn:
            self._step3_card_drawn = True
            self._deck = self._deck + self._shuffler.shuffle(self._below_step3_card)
            self._below_step3_card = []
        while len(self._visible) > PowerPlantMarket.VISIBLE_IN_STEP3:
            self._put_under_deck(self._visible.pop())

    def state(self) -> str:
        current = self._current_market()
        return json.dumps({
            "step": self._step,
            "current": [p.number.number for p in current],
            "future": [p.number.number for p in self._visible[len(current):]],
            "deck_size": len(self._deck) + len(self._below_step3_card),
            "step3_card_drawn": self._step3_card_drawn,
        })
