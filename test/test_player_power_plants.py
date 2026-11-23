import unittest

from power_grid.player_power_plants import PlayerPowerPlants
from power_grid.simple_types import PowerPlant, PowerPlantNumber, RequestError, Resource


class TestPlayerPowerPlants(unittest.TestCase):
    @staticmethod
    def make_plant(
        number: int,
        accepted: list[Resource],
        amount: int,
        cities: int,
    ) -> PowerPlant:
        return PowerPlant(PowerPlantNumber(number), accepted, amount, cities)

    # Constructor tests

    def test_constructor_rejects_too_many_or_duplicate_plants(self) -> None:
        plant = self.make_plant(3, [Resource.COAL], 1, 1)

        with self.assertRaises(ValueError):
            PlayerPowerPlants([plant, plant, plant, plant])
        with self.assertRaises(ValueError):
            PlayerPowerPlants([plant, plant])

    # best_power_plant tests

    def test_best_power_plant(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(14, [Resource.GARBAGE], 2, 2),
                self.make_plant(7, [], 0, 2),
            ]
        )
        self.assertEqual(plants.best_power_plant(), PowerPlantNumber(14))

        with self.assertRaises(ValueError):
            PlayerPowerPlants().best_power_plant()

    # receive_power_plant tests

    def test_receive_power_plant(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.OIL], 1, 1),
            ]
        )

        self.assertTrue(plants.receive_power_plant(self.make_plant(5, [], 0, 1)))
        self.assertFalse(plants.receive_power_plant(self.make_plant(5, [], 0, 1)))
        self.assertFalse(plants.receive_power_plant(self.make_plant(6, [], 0, 1)))
        self.assertEqual(plants.best_power_plant(), PowerPlantNumber(5))

    # can_store_resources tests

    def test_can_store_resources(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 2, 1),
                self.make_plant(4, [Resource.OIL, Resource.COAL], 2, 1),
            ]
        )

        self.assertTrue(
            plants.can_store_resources([Resource.COAL] * 4 + [Resource.OIL] * 4)
        )
        self.assertFalse(
            plants.can_store_resources([Resource.COAL] * 5 + [Resource.OIL] * 4)
        )
        self.assertFalse(plants.can_store_resources([Resource.URANIUM]))

    def test_can_store_resources_with_hybrid_plant(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.COAL, Resource.OIL], 1, 1),
            ]
        )
        self.assertTrue(
            plants.can_store_resources([Resource.COAL] * 2 + [Resource.OIL] * 2)
        )

    # remove_power_plant tests

    def test_remove_power_plant(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.OIL], 1, 1),
            ]
        )

        self.assertIsNone(
            plants.remove_power_plant(
                PowerPlantNumber(4), [Resource.COAL, Resource.COAL]
            )
        )
        self.assertEqual(plants.best_power_plant(), PowerPlantNumber(3))

    def test_remove_power_plant_rejects_invalid_removal(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.OIL], 1, 1),
            ]
        )

        invalid_inventory = plants.remove_power_plant(
            PowerPlantNumber(4), [Resource.OIL]
        )
        unknown_plant = plants.remove_power_plant(PowerPlantNumber(5), [])

        self.assertIsInstance(invalid_inventory, RequestError)
        self.assertIsInstance(unknown_plant, RequestError)
        self.assertEqual(plants.best_power_plant(), PowerPlantNumber(4))

    # number_of_connectable_cities tests

    def test_number_of_connectable_cities(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 2, 3),
                self.make_plant(4, [Resource.OIL], 1, 2),
                self.make_plant(5, [], 0, 4),
            ]
        )

        self.assertEqual(
            plants.number_of_connectable_cities([Resource.COAL, Resource.COAL]), 7
        )
        self.assertEqual(plants.number_of_connectable_cities([]), 4)

    def test_number_of_connectable_cities_with_hybrid_plant(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 1, 2),
                self.make_plant(4, [Resource.COAL, Resource.OIL], 1, 3),
            ]
        )
        self.assertEqual(
            plants.number_of_connectable_cities([Resource.COAL, Resource.OIL]), 5
        )

    # use_power_plant tests

    def test_use_power_plant(self) -> None:
        plants = PlayerPowerPlants(
            [
                self.make_plant(3, [Resource.COAL], 1, 3),
                self.make_plant(4, [Resource.COAL, Resource.OIL], 1, 2),
            ]
        )
        selection = [PowerPlantNumber(3), PowerPlantNumber(4)]
        fuel = [Resource.COAL, Resource.OIL]

        self.assertEqual(plants.use_power_plant(selection, fuel), 5)
        self.assertEqual(plants.use_power_plant(selection, fuel), 5)

    def test_use_power_plant_rejects_invalid_selection_or_fuel(self) -> None:
        plants = PlayerPowerPlants([self.make_plant(3, [Resource.COAL], 2, 3)])

        # Unowned power plant
        self.assertIsInstance(
            plants.use_power_plant([PowerPlantNumber(4)], [Resource.COAL]),
            RequestError,
        )

        # Duplicate power plant
        self.assertIsInstance(
            plants.use_power_plant(
                [PowerPlantNumber(3), PowerPlantNumber(3)],
                [Resource.COAL] * 4,
            ),
            RequestError,
        )

        # Insufficient resources
        self.assertIsInstance(
            plants.use_power_plant([PowerPlantNumber(3)], [Resource.COAL]),
            RequestError,
        )

        # Incompatible resource type
        self.assertIsInstance(
            plants.use_power_plant(
                [PowerPlantNumber(3)],
                [Resource.COAL, Resource.OIL],
            ),
            RequestError,
        )

        # Too many resources
        self.assertIsInstance(
            plants.use_power_plant([PowerPlantNumber(3)], [Resource.COAL] * 3),
            RequestError,
        )

    def test_use_ecological_power_plant_without_fuel(self) -> None:
        plants = PlayerPowerPlants([self.make_plant(13, [], 0, 1)])
        self.assertEqual(plants.use_power_plant([PowerPlantNumber(13)], []), 1)


if __name__ == "__main__":
    unittest.main()
