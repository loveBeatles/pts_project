from __future__ import annotations

from collections.abc import Mapping, Sequence

from power_grid.interfaces import InterfacePlayerBoardFacade
from power_grid.phases.turn_based_phase import TurnBasedPhase
from power_grid.simple_types import PhaseStatus, PlayerColor, RequestError, Resource


class BuyingResources(TurnBasedPhase):
    """Manages Phase 3 where players buy fuel in reverse player order"""

    def __init__(
        self, player_boards: Mapping[PlayerColor, InterfacePlayerBoardFacade]
    ) -> None:
        super().__init__()
        self._player_boards = player_boards

    def start_phase(self, player_order: Sequence[PlayerColor]) -> None:
        # Phase 3 runs in reverse player order (last place buys first)
        self._init_turns(list(reversed(player_order)))

    def buy_resources(
        self, player: PlayerColor, removed_resources: Sequence[Resource]
    ) -> PhaseStatus | RequestError:
        turn_error = self._validate_active_player(player)
        if turn_error is not None:
            return turn_error

        purchase_error = self._player_boards[player].buy_resources(removed_resources)
        if purchase_error is not None:
            return purchase_error

        return self._advance_turn()
