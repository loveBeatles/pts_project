from __future__ import annotations
import json
import unittest
from typing import Any, Sequence
from power_grid.interfaces import InterfaceShuffler
from power_grid.power_plant_market import PowerPlantMarket
from power_grid.simple_types import PowerPlant, PowerPlantNumber, RequestError, Resource


def plant(number: int) -> PowerPlant:
    return PowerPlant(PowerPlantNumber(number), [Resource.COAL], 2, 1)


def plants(*numbers: int) -> list[PowerPlant]:
    return [plant(n) for n in numbers]


class ReversingShuffler(InterfaceShuffler):
    def __init__(self) -> None:
        self.calls = 0

    def shuffle(self, power_plants: Sequence[PowerPlant]) -> list[PowerPlant]:
        self.calls += 1
        return list(reversed(power_plants))


class TestPowerPlantMarket(unittest.TestCase):
    def setUp(self) -> None:
        self.shuffler = ReversingShuffler()
        self.market = PowerPlantMarket(plants(10, 3, 8, 4, 6, 9, 5, 7),
                                       plants(20, 13, 30), self.shuffler)

    def state(self) -> Any:
        return json.loads(self.market.state())

    def test_initial_market_is_sorted_and_split(self) -> None:
        self.assertEqual(self.state()["current"], [3, 4, 5, 6])
        self.assertEqual(self.state()["future"], [7, 8, 9, 10])

    def test_can_take_only_current_market_with_minimal_bid(self) -> None:
        self.assertIsNone(self.market.can_take_power_plant(PowerPlantNumber(5), 5))
        self.assertIsNone(self.market.can_take_power_plant(PowerPlantNumber(5), 12))
        self.assertIsInstance(self.market.can_take_power_plant(PowerPlantNumber(5), 4),
                              RequestError)
        self.assertIsInstance(self.market.can_take_power_plant(PowerPlantNumber(7), 7),
                              RequestError)
        self.assertIsInstance(self.market.can_take_power_plant(PowerPlantNumber(20), 20),
                              RequestError)

    def test_take_draws_replacement(self) -> None:
        taken = self.market.take_power_plant(PowerPlantNumber(4))
        self.assertEqual(taken, plant(4))
        self.assertEqual(self.state()["current"], [3, 5, 6, 7])
        self.assertEqual(self.state()["future"], [8, 9, 10, 20])

    def test_remove_lowest(self) -> None:
        self.market.remove_lowest_power_plant()
        self.assertEqual(self.state()["current"], [4, 5, 6, 7])

    def test_remove_cheaper_than_includes_equal(self) -> None:
        self.market.remove_power_plants_cheaper_than(5)
        self.assertEqual(self.state()["current"], [6, 7, 8, 9])
        self.assertEqual(self.state()["future"], [10, 13, 20, 30])

    def test_prepare_next_turn_moves_highest_under_deck(self) -> None:
        self.market.prepare_next_turn()
        self.assertEqual(self.state()["future"], [7, 8, 9, 20])
        self.assertEqual(self.state()["deck_size"], 3)

    def test_step3_card_is_drawn_after_deck(self) -> None:
        self.market.prepare_next_turn()          # 10 under the Step 3 card, 20 drawn
        self.market.take_power_plant(PowerPlantNumber(3))   # draws 13
        self.market.take_power_plant(PowerPlantNumber(4))   # draws 30
        self.assertFalse(self.market.is_step3_start())
        self.market.take_power_plant(PowerPlantNumber(5))   # draws the Step 3 card
        self.assertTrue(self.market.is_step3_start())
        self.assertEqual(self.shuffler.calls, 1)
        self.assertEqual(len(self.state()["current"] + self.state()["future"]), 7)
        self.market.take_power_plant(PowerPlantNumber(6))   # 10 from the new stack
        self.assertIn(10, self.state()["current"] + self.state()["future"])

    def test_start_step2_removes_lowest(self) -> None:
        self.market.start_step2()
        self.assertEqual(self.state()["current"], [4, 5, 6, 7])
        self.assertEqual(self.state()["step"], 2)

    def _reach_step3(self) -> None:
        self.market.start_step2()                # 3 removed, 20 drawn
        self.market.prepare_next_turn()          # 20 under the Step 3 card, 13 drawn
        self.market.take_power_plant(PowerPlantNumber(4))   # draws 30
        self.market.take_power_plant(PowerPlantNumber(5))   # draws the Step 3 card
        self.assertTrue(self.market.is_step3_start())
        self.market.start_step3()

    def test_start_step3_has_six_buyable_plants(self) -> None:
        self._reach_step3()
        self.assertFalse(self.market.is_step3_start())
        self.assertEqual(self.state()["current"], [7, 8, 9, 10, 13, 30])
        self.assertEqual(self.state()["future"], [])
        self.assertIsNone(self.market.can_take_power_plant(PowerPlantNumber(30), 30))

    def test_prepare_next_turn_in_step3_removes_lowest(self) -> None:
        self._reach_step3()
        self.market.prepare_next_turn()
        self.assertEqual(self.state()["current"], [8, 9, 10, 13, 20, 30])

if __name__ == "__main__":
    unittest.main()
