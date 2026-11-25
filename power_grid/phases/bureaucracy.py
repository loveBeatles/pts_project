from __future__ import annotations

from collections.abc import Mapping, Sequence

from power_grid.interfaces import (
    InterfaceBureaucracy,
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceResourceMarket,
    InterfaceTowns,
)
from power_grid.phases.turn_based_phase import TurnBasedPhase
from power_grid.simple_types import (
    PhaseStatus,
    PlayerColor,
    PowerPlantNumber,
    RequestError,
    Resource,
)


class Bureaucracy(TurnBasedPhase, InterfaceBureaucracy):
    """Manages Phase 5 where players power cities, collect income, and refresh markets"""

    def __init__(
        self,
        player_boards: Mapping[PlayerColor, InterfacePlayerBoardFacade],
        resource_market: InterfaceResourceMarket,
        power_plant_market: InterfacePowerPlantMarket,
        towns: InterfaceTowns,
    ) -> None:
        super().__init__()
        self._player_boards = player_boards
        self._resource_market = resource_market
        self._power_plant_market = power_plant_market
        self._towns = towns

    def start_phase(self, player_order: Sequence[PlayerColor]) -> None:
        # Phase 5 runs in forward player order (first place acts first).
        self._init_turns(player_order)

    def use_power_plants(
        self,
        player: PlayerColor,
        ppns: Sequence[PowerPlantNumber],
        resources_to_burn: Sequence[Resource],
    ) -> PhaseStatus | RequestError:
        turn_error = self._validate_active_player(player)
        if turn_error is not None:
            return turn_error

        board = self._player_boards[player]
        cities_or_error = board.use_power_plants(ppns, resources_to_burn)
        if isinstance(cities_or_error, RequestError):
            return cities_or_error

        powered_cities = min(
            cities_or_error, self._towns.get_number_of_houses(player)
        )
        board.receive_income(powered_cities)

        status = self._advance_turn()
        if status == PhaseStatus.PHASE_ENDS:
            self._resource_market.refill()
            self._power_plant_market.prepare_next_turn()
        return status
