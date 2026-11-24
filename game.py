from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from power_grid.interfaces import (
    InterfaceAuctionPowerPlants,
    InterfaceBuildingHouses,
    InterfaceBureaucracy,
    InterfaceBuyingResources,
    InterfaceCheckAndBumpStep,
    InterfaceDeterminePlayerOrder,
    InterfacePlayerBoardFacade,
    InterfaceTowns,
)
from power_grid.simple_types import (
    GamePhase,
    PhaseStatus,
    PlayerColor,
    PowerPlantNumber,
    RequestError,
    Resource,
    SerializedGameState,
)


@dataclass(frozen=True)
class GamePhases:
    auction: InterfaceAuctionPowerPlants
    buying_resources: InterfaceBuyingResources
    building_houses: InterfaceBuildingHouses
    bureaucracy: InterfaceBureaucracy


@dataclass(frozen=True)
class GameComponents:
    player_boards: Mapping[PlayerColor, InterfacePlayerBoardFacade]
    towns: InterfaceTowns
    player_order: InterfaceDeterminePlayerOrder
    step: InterfaceCheckAndBumpStep


class Game:
    """Puts the phases together and switches between them.

    Round: auction -> buying resources -> building houses -> bureaucracy.
    After the auction of the first round the player order is determined again.
    The game ends after building houses once a player reaches the end-of-game
    number of houses; the winner is decided by DeterminePlayerOrder.game_result.
    """

    END_GAME_HOUSES: dict[int, int] = {2: 21, 3: 17, 4: 17, 5: 15, 6: 14}

    _order: list[PlayerColor]
    _phases: GamePhases
    _components: GameComponents
    _phase: GamePhase
    _round: int

    def __init__(self, initial_order: Sequence[PlayerColor], phases: GamePhases,
                 components: GameComponents) -> None:
        assert len(initial_order) in Game.END_GAME_HOUSES
        assert set(initial_order) == set(components.player_boards)
        self._order = list(initial_order)
        self._phases = phases
        self._components = components
        self._round = 1
        self._phase = GamePhase.AUCTION_POWER_PLANTS
        self._phases.auction.start_phase(self._order, first_round=True)

    @property
    def phase(self) -> GamePhase:
        return self._phase

    @property
    def player_order(self) -> list[PlayerColor]:
        return list(self._order)

    # ----- phase 2: auction -----

    def start_auction(self, player: PlayerColor, ppn: PowerPlantNumber,
                      price: int) -> PhaseStatus | RequestError:
        return self._auction_action(
            lambda: self._phases.auction.start_auction(player, ppn, price))

    def raise_bid(self, player: PlayerColor, price: int) -> PhaseStatus | RequestError:
        return self._auction_action(lambda: self._phases.auction.raise_bid(player, price))

    def pass_bid(self, player: PlayerColor) -> PhaseStatus | RequestError:
        return self._auction_action(lambda: self._phases.auction.pass_bid(player))

    def pass_auction(self, player: PlayerColor) -> PhaseStatus | RequestError:
        return self._auction_action(lambda: self._phases.auction.pass_phase(player))

    def discard_power_plant(self, player: PlayerColor, ppn: PowerPlantNumber,
                            removed_resources: Sequence[Resource]) -> PhaseStatus | RequestError:
        return self._auction_action(lambda: self._phases.auction.discard_power_plant(
            player, ppn, removed_resources))

    # ----- phases 3-5 -----

    def buy_resources(self, player: PlayerColor,
                      resources: Sequence[Resource]) -> PhaseStatus | RequestError:
        error = self._check_phase(GamePhase.BUY_RESOURCES)
        if error is not None:
            return error
        status = self._phases.buying_resources.buy_resources(player, resources)
        if status == PhaseStatus.PHASE_ENDS:
            self._components.step.check_and_bump_to_step3()
            self._phase = GamePhase.BUY_HOUSES
            self._phases.building_houses.start_phase(self._order)
        return status

    def build_houses(self, player: PlayerColor,
                     town_names: Sequence[str]) -> PhaseStatus | RequestError:
        error = self._check_phase(GamePhase.BUY_HOUSES)
        if error is not None:
            return error
        status = self._phases.building_houses.build_houses(player, town_names)
        if status != PhaseStatus.PHASE_ENDS:
            return status
        if self._components.towns.get_max_number_of_houses() >= \
                Game.END_GAME_HOUSES[len(self._order)]:
            self._phase = GamePhase.GAME_END
            return PhaseStatus.GAME_ENDS
        self._components.step.check_and_bump_to_step3()
        self._phase = GamePhase.BUREAUCRACY
        self._phases.bureaucracy.start_phase(self._order)
        return status

    def use_power_plants(self, player: PlayerColor, ppns: Sequence[PowerPlantNumber],
                         resources_to_burn: Sequence[Resource]) -> PhaseStatus | RequestError:
        error = self._check_phase(GamePhase.BUREAUCRACY)
        if error is not None:
            return error
        status = self._phases.bureaucracy.use_power_plants(player, ppns, resources_to_burn)
        if status == PhaseStatus.PHASE_ENDS:
            self._components.step.check_and_bump_to_step3()
            self._round += 1
            self._order = self._components.player_order.reorder()
            self._phase = GamePhase.AUCTION_POWER_PLANTS
            self._phases.auction.start_phase(self._order)
        return status

    def game_result(self) -> list[PlayerColor] | RequestError:
        error = self._check_phase(GamePhase.GAME_END)
        if error is not None:
            return error
        return self._components.player_order.game_result()

    def state(self) -> SerializedGameState:
        phase_states = {
            GamePhase.AUCTION_POWER_PLANTS: self._phases.auction.get_state,
            GamePhase.BUY_RESOURCES: self._phases.buying_resources.get_state,
            GamePhase.BUY_HOUSES: self._phases.building_houses.get_state,
            GamePhase.BUREAUCRACY: self._phases.bureaucracy.get_state,
        }
        get_phase_state = phase_states.get(self._phase)
        return SerializedGameState(json.dumps({
            "round": self._round,
            "step": self._components.step.get_step(),
            "phase": self._phase.value,
            "player_order": [p.value for p in self._order],
            "phase_state": None if get_phase_state is None else json.loads(get_phase_state()),
            "players": {color.value: json.loads(board.state())
                        for color, board in self._components.player_boards.items()},
        }))

    # ----- helpers -----

    def _check_phase(self, expected: GamePhase) -> RequestError | None:
        if self._phase != expected:
            return RequestError(f"Action not allowed in phase {self._phase.value}.")
        return None

    def _auction_action(self, action: Callable[[], PhaseStatus | RequestError]
                        ) -> PhaseStatus | RequestError:
        error = self._check_phase(GamePhase.AUCTION_POWER_PLANTS)
        if error is not None:
            return error
        status = action()
        if status == PhaseStatus.PHASE_ENDS:
            if self._round == 1:
                self._order = self._components.player_order.reorder()
            self._components.step.check_and_bump_to_step3()
            self._phase = GamePhase.BUY_RESOURCES
            self._phases.buying_resources.start_phase(self._order)
        return status
