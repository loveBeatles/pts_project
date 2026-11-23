from __future__ import annotations
import json
from typing import Sequence
from power_grid.interfaces import (
    InterfaceConnections,
    InterfaceTowns,
    InterfaceTownsCheckAndBumpStep,
)
from power_grid.simple_types import PlayerColor, RequestError


class Towns(InterfaceTowns, InterfaceTownsCheckAndBumpStep):
    """Keeps track of houses in towns.

    Each town has three spaces costing 10, 15 and 20. In step N only the first
    N spaces of every town can be used, and a player can have at most one house
    in a town.
    """
    HOUSE_PRICES: tuple[int, int, int] = (10, 15, 20)

    _houses: dict[str, list[PlayerColor]]
    _connections: InterfaceConnections
    _step: int

    def __init__(self, town_names: Sequence[str], connections: InterfaceConnections) -> None:
        assert len(set(town_names)) == len(town_names)
        self._houses = {name: [] for name in town_names}
        self._connections = connections
        self._step = 1

    def _towns_of(self, player: PlayerColor) -> list[str]:
        return [name for name, owners in self._houses.items() if player in owners]

    def _validate(self, player: PlayerColor, town_names: Sequence[str]) -> RequestError | None:
        if len(set(town_names)) != len(town_names):
            return RequestError("A town is listed more than once.")
        for name in town_names:
            if name not in self._houses:
                return RequestError(f"Unknown town {name}.")
            if player in self._houses[name]:
                return RequestError(f"Player already has a house in {name}.")
            if len(self._houses[name]) >= self._step:
                return RequestError(f"No free space in {name} in step {self._step}.")
        return None

    def buy_houses(self, player: PlayerColor, town_names: Sequence[str],
                   max_money: int) -> int | RequestError:
        """Builds houses if the player can afford them. Returns the total cost
        (connections plus house prices); nothing changes on error."""
        names = list(town_names)
        error = self._validate(player, names)
        if error is not None:
            return error
        try:
            connection_cost = self._connections.calculate_connecting_cost(
                self._towns_of(player), names)
        except ValueError:
            return RequestError("Some town cannot be connected.")
        house_cost = sum(Towns.HOUSE_PRICES[len(self._houses[name])] for name in names)
        total = connection_cost + house_cost
        if total > max_money:
            return RequestError(f"Building costs {total}, player has only {max_money}.")
        for name in names:
            self._houses[name].append(player)
        return total

    def get_number_of_houses(self, player: PlayerColor) -> int:
        return len(self._towns_of(player))

    def get_max_number_of_houses(self) -> int:
        counts: dict[PlayerColor, int] = {}
        for owners in self._houses.values():
            for owner in owners:
                counts[owner] = counts.get(owner, 0) + 1
        return max(counts.values(), default=0)

    def start_step2(self) -> None:
        assert self._step == 1
        self._step = 2

    def start_step3(self) -> None:
        assert self._step < 3
        self._step = 3

    def state(self) -> str:
        return json.dumps({
            "step": self._step,
            "towns": {name: [p.value for p in owners] for name, owners in self._houses.items()},
        })
