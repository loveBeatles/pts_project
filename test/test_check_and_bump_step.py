from __future__ import annotations
import unittest
from power_grid.check_and_bump_step import CheckAndBumpStep
from power_grid.interfaces import (
    InterfaceTowns,
    InterfacePowerPlantMarket,
    InterfaceResourceMarket,
)


class TownsFake(InterfaceTowns):
    max_houses: int
    calls: list[str]

    def __init__(self, calls: list[str]) -> None:
        self.max_houses = 0
        self.calls = calls

    def get_max_number_of_houses(self) -> int:
        return self.max_houses

    def start_step_2(self) -> None:
        self.calls.append("towns.step2")

    def start_step_3(self) -> None:
        self.calls.append("towns.step3")


class PowerPlantMarketFake(InterfacePowerPlantMarket):
    step3_start: bool
    calls: list[str]

    def __init__(self, calls: list[str]) -> None:
        self.step3_start = False
        self.calls = calls

    def is_step_3_start(self) -> bool:
        return self.step3_start

    def start_step_2(self) -> None:
        self.calls.append("power_plant_market.step2")

    def start_step_3(self) -> None:
        self.calls.append("power_plant_market.step3")


class ResourceMarketFake(InterfaceResourceMarket):
    calls: list[str]

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def start_step_2(self) -> None:
        self.calls.append("resource_market.step2")

    def start_step_3(self) -> None:
        self.calls.append("resource_market.step3")


STEP2_CALLS = ["towns.step2",
               "power_plant_market.step2", "resource_market.step2"]
STEP3_CALLS = ["towns.step3",
               "power_plant_market.step3", "resource_market.step3"]


class TestCheckAndBumpStep(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[str] = []
        self.towns: TownsFake = TownsFake(self.calls)
        self.power_plant_market: PowerPlantMarketFake = PowerPlantMarketFake(
            self.calls)
        self.resource_market: ResourceMarketFake = ResourceMarketFake(
            self.calls)

    def make(self, num_players: int) -> CheckAndBumpStep:
        return CheckAndBumpStep(num_players, self.towns,
                                self.power_plant_market, self.resource_market)

    def test_starts_in_step1(self) -> None:
        self.assertEqual(self.make(3).get_step(), 1)
        self.assertEqual(self.calls, [])

    def test_step2_not_triggered_below_threshold(self) -> None:
        bump = self.make(4)
        self.towns.max_houses = 6
        bump.check_and_bump_to_step_2()
        self.assertEqual(bump.get_step(), 1)
        self.assertEqual(self.calls, [])

    def test_step2_triggered_at_seven_for_five_players(self) -> None:
        bump = self.make(5)
        self.towns.max_houses = 7
        bump.check_and_bump_to_step_2()
        self.assertEqual(bump.get_step(), 2)
        self.assertEqual(self.calls, STEP2_CALLS)

    def test_step2_triggered_above_threshold_for_two_players(self) -> None:
        bump = self.make(2)
        self.towns.max_houses = 9
        bump.check_and_bump_to_step_2()
        self.assertEqual(bump.get_step(), 2)

    def test_step2_threshold_for_six_players(self) -> None:
        bump = self.make(6)
        self.towns.max_houses = 5
        bump.check_and_bump_to_step_2()
        self.assertEqual(bump.get_step(), 1)
        self.towns.max_houses = 6
        bump.check_and_bump_to_step_2()
        self.assertEqual(bump.get_step(), 2)
        self.assertEqual(self.calls, STEP2_CALLS)

    def test_step2_happens_only_once(self) -> None:
        bump = self.make(3)
        self.towns.max_houses = 7
        bump.check_and_bump_to_step_2()
        bump.check_and_bump_to_step_2()
        self.assertEqual(bump.get_step(), 2)
        self.assertEqual(self.calls, STEP2_CALLS)

    def test_step3_not_triggered_without_card(self) -> None:
        bump = self.make(3)
        bump.check_and_bump_to_step_3()
        self.assertEqual(bump.get_step(), 1)
        self.assertEqual(self.calls, [])

    def test_step3_from_step2(self) -> None:
        bump = self.make(3)
        self.towns.max_houses = 7
        bump.check_and_bump_to_step_2()
        self.power_plant_market.step3_start = True
        bump.check_and_bump_to_step_3()
        self.assertEqual(bump.get_step(), 3)
        self.assertEqual(self.calls, STEP2_CALLS + STEP3_CALLS)

    def test_step3_from_step1_goes_through_step2(self) -> None:
        bump = self.make(4)
        self.power_plant_market.step3_start = True
        bump.check_and_bump_to_step_3()
        self.assertEqual(bump.get_step(), 3)
        self.assertEqual(self.calls, STEP2_CALLS + STEP3_CALLS)

    def test_step3_happens_only_once(self) -> None:
        bump = self.make(4)
        self.power_plant_market.step3_start = True
        bump.check_and_bump_to_step_3()
        bump.check_and_bump_to_step_3()
        self.assertEqual(bump.get_step(), 3)
        self.assertEqual(self.calls, STEP2_CALLS + STEP3_CALLS)

    def test_no_step2_after_step3(self) -> None:
        bump = self.make(4)
        self.power_plant_market.step3_start = True
        bump.check_and_bump_to_step_3()
        self.towns.max_houses = 10
        bump.check_and_bump_to_step_2()
        self.assertEqual(bump.get_step(), 3)
        self.assertEqual(self.calls, STEP2_CALLS + STEP3_CALLS)


if __name__ == "__main__":
    unittest.main()
