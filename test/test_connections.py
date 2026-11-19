from __future__ import annotations
import unittest
from power_grid.connections import Connections


class TestConnections(unittest.TestCase):
    def setUp(self) -> None:
        #   A --5-- B --3-- C
        #   |               |
        #   +------10-------+
        #   C --4-- D,   E --2-- F (separate component)
        self.connections: Connections = Connections([
            ("A", "B", 5),
            ("B", "C", 3),
            ("A", "C", 10),
            ("C", "D", 4),
            ("E", "F", 2),
        ])

    def test_first_house_is_free(self) -> None:
        self.assertEqual(
            self.connections.calculate_connecting_cost([], ["A"]), 0)

    def test_empty_targets_cost_nothing(self) -> None:
        self.assertEqual(
            self.connections.calculate_connecting_cost(["A"], []), 0)
        self.assertEqual(self.connections.calculate_connecting_cost([], []), 0)

    def test_first_house_then_chain(self) -> None:
        self.assertEqual(
            self.connections.calculate_connecting_cost([], ["A", "B", "C"]), 5 + 3)

    def test_direct_neighbour(self) -> None:
        self.assertEqual(
            self.connections.calculate_connecting_cost(["A"], ["B"]), 5)

    def test_shortest_path_preferred_over_direct_edge(self) -> None:
        self.assertEqual(
            self.connections.calculate_connecting_cost(["A"], ["C"]), 8)

    def test_multi_hop_path(self) -> None:
        self.assertEqual(
            self.connections.calculate_connecting_cost(["A"], ["D"]), 12)

    def test_cheapest_source_in_network_is_used(self) -> None:
        self.assertEqual(
            self.connections.calculate_connecting_cost(["A", "C"], ["D"]), 4)

    def test_targets_extend_network_sequentially(self) -> None:
        # A->C costs 8, then D is reached from C for 4
        self.assertEqual(
            self.connections.calculate_connecting_cost(["A"], ["C", "D"]), 8 + 4)

    def test_order_of_targets_matters(self) -> None:
        # A->D costs 12, then C is reached from D for 4
        self.assertEqual(
            self.connections.calculate_connecting_cost(["A"], ["D", "C"]), 12 + 4)

    def test_target_already_in_network_is_free(self) -> None:
        self.assertEqual(
            self.connections.calculate_connecting_cost(["A"], ["A"]), 0)

    def test_unreachable_town_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.connections.calculate_connecting_cost(["A"], ["E"])

    def test_unknown_town_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.connections.calculate_connecting_cost(["A"], ["Z"])

    def test_unreachable_after_first_house_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.connections.calculate_connecting_cost([], ["A", "F"])


if __name__ == "__main__":
    unittest.main()
