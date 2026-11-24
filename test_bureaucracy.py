from __future__ import annotations

from collections.abc import Sequence
import unittest

from power_grid.interfaces import (
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceResourceMarket,
    InterfaceTowns,
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
    def __init__(self, fail_next: bool = False, cities: int = 0) -> None:
        self.fail_next = fail_next
        self.cities = cities
        self.used_calls: list[tuple[list[PowerPlantNumber], list[Resource]]] = []
        self.income_calls: list[int] = []

    def use_power_plants(
        self, ppns: Sequence[PowerPlantNumber], resources_to_burn: Sequence[Resource]
    ) -> int | RequestError:
        if self.fail_next:
            self.fail_next = False
            return RequestError("Invalid fuel selection.")
        self.used_calls.append((list(ppns), list(resources_to_burn)))
        return self.cities

    def receive_income(self, powered_cities: int) -> None:
        self.income_calls.append(powered_cities)


class StubTowns(InterfaceTowns):
    def __init__(self, houses: dict[PlayerColor, int]) -> None:
        self.houses = houses

    def get_number_of_houses(self, player: PlayerColor) -> int:
        return self.houses.get(player, 0)


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
        phase = Bureaucracy(boards, res_market, plant_market, StubTowns({}))
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

    def test_income_is_limited_by_houses(self) -> None:
        red = StubPowerBoard(cities=5)
        blue = StubPowerBoard(cities=2)
        towns = StubTowns({PlayerColor.RED: 3, PlayerColor.BLUE: 4})
        phase = Bureaucracy({PlayerColor.RED: red, PlayerColor.BLUE: blue},
                            SpyResourceMarket(), SpyPowerPlantMarket(), towns)
        phase.start_phase([PlayerColor.RED, PlayerColor.BLUE])
        phase.use_power_plants(PlayerColor.RED, [PowerPlantNumber(3)], [])
        phase.use_power_plants(PlayerColor.BLUE, [PowerPlantNumber(4)], [])
        self.assertEqual(red.income_calls, [3])
        self.assertEqual(blue.income_calls, [2])

    def test_failed_use_gives_no_income(self) -> None:
        red = StubPowerBoard(fail_next=True, cities=1)
        phase = Bureaucracy({PlayerColor.RED: red}, SpyResourceMarket(),
                            SpyPowerPlantMarket(), StubTowns({PlayerColor.RED: 1}))
        phase.start_phase([PlayerColor.RED])
        self.assertIsInstance(phase.use_power_plants(PlayerColor.RED, [], []), RequestError)
        self.assertEqual(red.income_calls, [])
