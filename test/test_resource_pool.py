from __future__ import annotations
import json
import unittest
from power_grid.resource_pool import ResourcePool
from power_grid.simple_types import Resource

C, O, G, U = Resource.COAL, Resource.OIL, Resource.GARBAGE, Resource.URANIUM


class TestResourcePool(unittest.TestCase):
    def setUp(self) -> None:
        self.pool = ResourcePool({C: 3, O: 1, G: 0, U: 2})

    def test_take_returns_only_available(self) -> None:
        self.assertEqual(self.pool.take_resources([O, O, O, G]), [O])
        self.assertEqual(self.pool.take_resources([O]), [])

    def test_take_all_requested(self) -> None:
        self.assertEqual(self.pool.take_resources([C, C, U]), [C, C, U])
        self.assertEqual(json.loads(self.pool.to_string()),
                         {"coal": 1, "oil": 1, "garbage": 0, "uranium": 1})

    def test_storage_space(self) -> None:
        self.assertTrue(self.pool.can_take_resources_from_storage_space([C, C, C, U]))
        self.assertFalse(self.pool.can_take_resources_from_storage_space([O, O]))
        self.assertFalse(self.pool.can_take_resources_from_storage_space([G]))
        self.pool.get_from_storage_space([C, C])
        self.assertFalse(self.pool.can_take_resources_from_storage_space([C, C]))

    def test_return_resources(self) -> None:
        self.pool.return_resources([G, G, O])
        self.assertEqual(self.pool.take_resources([G, G, G]), [G, G])
        self.assertEqual(self.pool.take_resources([O, O, O]), [O, O])

    def test_missing_resources_default_to_zero(self) -> None:
        pool = ResourcePool({C: 1})
        self.assertEqual(pool.take_resources([U]), [])


if __name__ == "__main__":
    unittest.main()
