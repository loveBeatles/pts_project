from __future__ import annotations

from collections.abc import Mapping, Sequence

from power_grid.interfaces import (
    InterfaceCheckAndBumpStep,
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceTowns,
)
from power_grid.phases.turn_based_phase import TurnBasedPhase
from power_grid.simple_types import PhaseStatus, PlayerColor, RequestError


class BuildingHouses(TurnBasedPhase):
    """Manages Phase 4 where players connect cities in reverse player order"""

    def __init__(
        self,
        player_boards: Mapping[PlayerColor, InterfacePlayerBoardFacade],
        towns: InterfaceTowns,
        power_plant_market: InterfacePowerPlantMarket,
        check_and_bump_step: InterfaceCheckAndBumpStep,
    ) -> None:
        super().__init__()
        self._player_boards = player_boards
        self._towns = towns
        self._power_plant_market = power_plant_market
        self._check_and_bump_step = check_and_bump_step

    def start_phase(self, player_order: Sequence[PlayerColor]) -> None:
        # Phase 4 runs in reverse player order (last place builds first)
        self._init_turns(list(reversed(player_order)))

    def build_houses(
        self, player: PlayerColor, town_names: Sequence[str]
    ) -> PhaseStatus | RequestError:
        turn_error = self._validate_active_player(player)
        if turn_error is not None:
            return turn_error

        board = self._player_boards[player]
        cost_or_error = self._towns.buy_houses(
            player, town_names, board.outstanding_money()
        )
        if isinstance(cost_or_error, RequestError):
            return cost_or_error

        if cost_or_error > 0:
            board.spend_money(cost_or_error)

        self._power_plant_market.remove_power_plants_cheaper_than(
            self._towns.get_max_number_of_houses()
        )

        status = self._advance_turn()
        if status == PhaseStatus.PHASE_ENDS:
            self._check_and_bump_step.check_and_bump_to_step_2()
        return status
