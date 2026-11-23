from __future__ import annotations
import json
import unittest
from typing import Sequence
from power_grid.interfaces import InterfaceConnections
from power_grid.simple_types import PlayerColor, RequestError
from power_grid.towns import Towns

RED, BLUE, GREEN = PlayerColor.RED, PlayerColor.BLUE, PlayerColor.GREEN


class ConnectionsFake(InterfaceConnections):
    """Every connection costs 5 per new town, except the very first house."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], list[str]]] = []

    def calculate_connecting_cost(self, from_towns: Sequence[str],
                                  to_towns: Sequence[str]) -> int:
        self.calls.append((list(from_towns), list(to_towns)))
        if "Nowhere" in to_towns:
            raise ValueError("unreachable")
        new = len(to_towns) - (0 if from_towns else 1)
        return 5 * max(new, 0)


class TestTowns(unittest.TestCase):
    def setUp(self) -> None:
        self.connections = ConnectionsFake()
        self.towns = Towns(["A", "B", "C", "Nowhere"], self.connections)

    def test_first_house_costs_only_space(self) -> None:
        self.assertEqual(self.towns.buy_houses(RED, ["A"], 50), 10)
        self.assertEqual(self.towns.get_number_of_houses(RED), 1)

    def test_connection_cost_is_added_and_own_towns_are_passed(self) -> None:
        self.towns.buy_houses(RED, ["A"], 50)
        self.assertEqual(self.towns.buy_houses(RED, ["B", "C"], 50), 10 + 10 + 10)
        self.assertEqual(self.connections.calls[-1], (["A"], ["B", "C"]))

    def test_empty_purchase_is_free(self) -> None:
        self.assertEqual(self.towns.buy_houses(RED, [], 0), 0)

    def test_not_enough_money_changes_nothing(self) -> None:
        result = self.towns.buy_houses(RED, ["A", "B"], 24)
        self.assertIsInstance(result, RequestError)
        self.assertEqual(self.towns.get_number_of_houses(RED), 0)

    def test_exact_money_is_enough(self) -> None:
        self.assertEqual(self.towns.buy_houses(RED, ["A", "B"], 25), 25)

    def test_only_one_house_per_town_in_step1(self) -> None:
        self.towns.buy_houses(RED, ["A"], 50)
        self.assertIsInstance(self.towns.buy_houses(BLUE, ["A"], 50), RequestError)

    def test_step2_opens_second_space_for_15(self) -> None:
        self.towns.buy_houses(RED, ["A"], 50)
        self.towns.start_step2()
        self.assertEqual(self.towns.buy_houses(BLUE, ["A"], 50), 15)
        self.assertIsInstance(self.towns.buy_houses(GREEN, ["A"], 50), RequestError)

    def test_step3_opens_third_space_for_20(self) -> None:
        self.towns.start_step2()
        self.towns.buy_houses(RED, ["A"], 50)
        self.towns.buy_houses(BLUE, ["A"], 50)
        self.towns.start_step3()
        self.assertEqual(self.towns.buy_houses(GREEN, ["A"], 50), 20)

    def test_player_cannot_build_twice_in_town(self) -> None:
        self.towns.start_step2()
        self.towns.buy_houses(RED, ["A"], 50)
        self.assertIsInstance(self.towns.buy_houses(RED, ["A"], 50), RequestError)

    def test_invalid_requests(self) -> None:
        self.assertIsInstance(self.towns.buy_houses(RED, ["X"], 50), RequestError)
        self.assertIsInstance(self.towns.buy_houses(RED, ["A", "A"], 50), RequestError)
        self.assertIsInstance(self.towns.buy_houses(RED, ["A", "Nowhere"], 50), RequestError)
        self.assertEqual(self.towns.get_number_of_houses(RED), 0)

    def test_max_number_of_houses(self) -> None:
        self.assertEqual(self.towns.get_max_number_of_houses(), 0)
        self.towns.buy_houses(RED, ["A"], 50)
        self.towns.buy_houses(BLUE, ["B", "C"], 50)
        self.assertEqual(self.towns.get_max_number_of_houses(), 2)

    def test_state(self) -> None:
        self.towns.buy_houses(RED, ["B"], 50)
        state = json.loads(self.towns.state())
        self.assertEqual(state["step"], 1)
        self.assertEqual(state["towns"]["B"], ["Red"])


if __name__ == "__main__":
    unittest.main()
