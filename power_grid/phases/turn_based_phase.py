from __future__ import annotations

from collections.abc import Sequence
import json

from power_grid.simple_types import PhaseStatus, PlayerColor, RequestError


class TurnBasedPhase:
    """Base class managing sequential player turns within a game phase"""

    def __init__(self) -> None:
        self._turn_order: list[PlayerColor] = []
        self._current_index: int = 0

    def _init_turns(self, order: Sequence[PlayerColor]) -> None:
        self._turn_order = list(order)
        self._current_index = 0

    def _validate_active_player(self, player: PlayerColor) -> RequestError | None:
        if self._current_index >= len(self._turn_order):
            return RequestError("Phase is not active.")
        if player != self._turn_order[self._current_index]:
            return RequestError("It is not this player's turn.")
        return None

    def _advance_turn(self) -> PhaseStatus:
        self._current_index += 1
        if self._current_index >= len(self._turn_order):
            return PhaseStatus.PHASE_ENDS
        return PhaseStatus.PHASE_CONTINUES

    def get_state(self) -> str:
        current = (
            self._turn_order[self._current_index].value
            if self._current_index < len(self._turn_order)
            else None
        )
        remaining = [p.value for p in self._turn_order[self._current_index :]]
        return json.dumps({"current_player": current, "remaining_players": remaining})
