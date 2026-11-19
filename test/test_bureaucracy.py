from __future__ import annotations

from collections.abc import Sequence
import unittest

from power_grid.interfaces import (
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceResourceMarket,
)
from power_grid.phases.bureaucracy import Bureaucracy
from power_grid.simple_types import (
    PhaseStatus,
    PlayerColor,
    PowerPlantNumber,
    RequestError,
    Resource,
)


class StubPowerBoard(InterfacePlayerBoardFacade):
    def __init__(self, fail_next: bool = False) -> None:
        self.fail_next = fail_next
        self.used_calls: list[tuple[list[PowerPlantNumber], list[Resource]]] = []

    def use_power_plants(
        self, ppns: Sequence[PowerPlantNumber], resources_to_burn: Sequence[Resource]
    ) -> RequestError | None:
        if self.fail_next:
            self.fail_next = False
            return RequestError("Invalid fuel selection.")
        self.used_calls.append((list(ppns), list(resources_to_burn)))
        return None


class SpyResourceMarket(InterfaceResourceMarket):
    def __init__(self) -> None:
        self.refill_count = 0

    def refill(self) -> None:
        self.refill_count += 1


class SpyPowerPlantMarket(InterfacePowerPlantMarket):
    def __init__(self) -> None:
        self.prepare_count = 0

    def prepare_next_turn(self) -> None:
        self.prepare_count += 1


class TestBureaucracy(unittest.TestCase):
    def test_bureaucracy_forward_order_and_market_refresh(self) -> None:
        boards = {
            PlayerColor.RED: StubPowerBoard(),
            PlayerColor.BLUE: StubPowerBoard(),
        }
        res_market = SpyResourceMarket()
        plant_market = SpyPowerPlantMarket()
        phase = Bureaucracy(boards, res_market, plant_market)
        phase.start_phase([PlayerColor.RED, PlayerColor.BLUE])

        self.assertIsInstance(
            phase.use_power_plants(PlayerColor.BLUE, [], []), RequestError
        )

        # Red goes first; markets must not refresh yet
        self.assertEqual(
            phase.use_power_plants(
                PlayerColor.RED, [PowerPlantNumber(3)], [Resource.OIL, Resource.OIL]
            ),
            PhaseStatus.PHASE_CONTINUES,
        )
        self.assertEqual(res_market.refill_count, 0)
        self.assertEqual(plant_market.prepare_count, 0)

        # Blue goes last; markets refresh once upon phase completion
        self.assertEqual(
            phase.use_power_plants(PlayerColor.BLUE, [], []), PhaseStatus.PHASE_ENDS
        )
        self.assertEqual(res_market.refill_count, 1)
        self.assertEqual(plant_market.prepare_count, 1)
