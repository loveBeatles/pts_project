from __future__ import annotations

from collections.abc import Mapping, Sequence

from power_grid.interfaces import (
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceResourceMarket,
)
from power_grid.phases.turn_based_phase import TurnBasedPhase
from power_grid.simple_types import (
    PhaseStatus,
    PlayerColor,
    PowerPlantNumber,
    RequestError,
    Resource,
)


class Bureaucracy(TurnBasedPhase):
    """Manages Phase 5 where players power cities and markets refresh"""

    def __init__(
        self,
        player_boards: Mapping[PlayerColor, InterfacePlayerBoardFacade],
        resource_market: InterfaceResourceMarket,
        power_plant_market: InterfacePowerPlantMarket,
    ) -> None:
        super().__init__()
        self._player_boards = player_boards
        self._resource_market = resource_market
        self._power_plant_market = power_plant_market

    def start_phase(self, player_order: Sequence[PlayerColor]) -> None:
        # Phase 5 runs in forward player order (first place acts first)
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

        power_error = self._player_boards[player].use_power_plants(
            ppns, resources_to_burn
        )
        if power_error is not None:
            return power_error

        status = self._advance_turn()
        if status == PhaseStatus.PHASE_ENDS:
            # Refill markets once all players have finished powering cities
            self._resource_market.refill()
            self._power_plant_market.prepare_next_turn()
        return status
