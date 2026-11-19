from __future__ import annotations

from collections.abc import Sequence
import unittest

from power_grid.interfaces import InterfacePlayerBoardFacade
from power_grid.phases.buying_resources import BuyingResources
from power_grid.simple_types import PhaseStatus, PlayerColor, RequestError, Resource


class StubBuyBoard(InterfacePlayerBoardFacade):
    def __init__(self, fail_next: bool = False) -> None:
        self.fail_next = fail_next
        self.purchased: list[list[Resource]] = []

    def buy_resources(self, resources: Sequence[Resource]) -> RequestError | None:
        if self.fail_next:
            self.fail_next = False
            return RequestError("Insufficient funds or storage.")
        self.purchased.append(list(resources))
        return None


class TestBuyingResources(unittest.TestCase):
    def test_buying_resources_reverse_order_and_completion(self) -> None:
        boards = {
            PlayerColor.RED: StubBuyBoard(),
            PlayerColor.BLUE: StubBuyBoard(),
            PlayerColor.GREEN: StubBuyBoard(),
        }
        phase = BuyingResources(boards)
        phase.start_phase([PlayerColor.RED, PlayerColor.BLUE, PlayerColor.GREEN])

        # Reverse order: Green -> Blue -> Red
        self.assertEqual(
            phase.buy_resources(PlayerColor.RED, []),
            RequestError("It is not this player's turn."),
        )
        self.assertEqual(
            phase.buy_resources(PlayerColor.GREEN, [Resource.COAL]),
            PhaseStatus.PHASE_CONTINUES,
        )
        self.assertEqual(
            phase.buy_resources(PlayerColor.BLUE, []),
            PhaseStatus.PHASE_CONTINUES,
        )
        self.assertEqual(
            phase.buy_resources(PlayerColor.RED, [Resource.OIL]),
            PhaseStatus.PHASE_ENDS,
        )
        self.assertEqual(boards[PlayerColor.GREEN].purchased, [[Resource.COAL]])
        self.assertEqual(boards[PlayerColor.BLUE].purchased, [[]])
        self.assertEqual(boards[PlayerColor.RED].purchased, [[Resource.OIL]])

    def test_buying_resources_error_does_not_skip_turn(self) -> None:
        boards = {
            PlayerColor.RED: StubBuyBoard(fail_next=True),
            PlayerColor.BLUE: StubBuyBoard(),
        }
        phase = BuyingResources(boards)
        phase.start_phase([PlayerColor.BLUE, PlayerColor.RED])

        result = phase.buy_resources(PlayerColor.RED, [Resource.URANIUM])
        self.assertIsInstance(result, RequestError)
        self.assertEqual(
            phase.buy_resources(PlayerColor.RED, []), PhaseStatus.PHASE_CONTINUES
        )
        self.assertEqual(
            phase.buy_resources(PlayerColor.BLUE, []), PhaseStatus.PHASE_ENDS
        )
