from collections import Counter
from collections.abc import Sequence
import unittest

from power_grid.interfaces import InterfaceResourceMarket, InterfaceResourcePoolPlayerResources
from power_grid.player_power_plants import PlayerPowerPlants
from power_grid.player_resources import PlayerResources
from power_grid.simple_types import PowerPlant, PowerPlantNumber, RequestError, Resource


class ResourceMarketFake(InterfaceResourceMarket):
    def __init__(self, available: Sequence[Resource]) -> None:
        self.available = list(available)
        self.take_calls: list[list[Resource]] = []

    def get_price(self, resources: Sequence[Resource]) -> int | None:
        requested = Counter(resources)
        available = Counter(self.available)
        if all(count <= available[resource] for resource, count in requested.items()):
            return 1
        return None

    def take_resources(self, resources: Sequence[Resource]) -> None:
        requested = list(resources)
        self.take_calls.append(requested)
        for resource in requested:
            self.available.remove(resource)


class ResourcePoolSpy(InterfaceResourcePoolPlayerResources):
    def __init__(self) -> None:
        self.returned: list[Resource] = []

    def return_resources(self, resources: Sequence[Resource]) -> None:
        self.returned.extend(resources)


class TestPlayerResources(unittest.TestCase):
    @staticmethod
    def make_plant(
        number: int,
        accepted_resources: Sequence[Resource],
        resource_amount: int,
        number_of_cities: int,
    ) -> PowerPlant:
        return PowerPlant(
            PowerPlantNumber(number),
            list(accepted_resources),
            resource_amount,
            number_of_cities,
        )

    def make_player(
        self,
        plants: Sequence[PowerPlant] = (),
        starting_resources: Sequence[Resource] = (),
        market_resources: Sequence[Resource] = (),
    ) -> tuple[PlayerResources, PlayerPowerPlants, ResourceMarketFake]:
        power_plants = PlayerPowerPlants(plants)
        market = ResourceMarketFake(market_resources)
        player = PlayerResources(power_plants, market, starting_resources)
        return player, power_plants, market

    # Constructor and inventory tests

    def test_initial_inventory_defaults_to_empty(self) -> None:
        player, _, _ = self.make_player()
        self.assertEqual(player.resources, [])

    def test_initial_inventory_is_copied_and_must_fit(self) -> None:
        plant = self.make_plant(3, [Resource.COAL], 1, 1)
        starting_resources = [Resource.COAL]
        player, _, _ = self.make_player([plant], starting_resources)
        starting_resources.append(Resource.COAL)

        self.assertEqual(player.resources, [Resource.COAL])

        with self.assertRaises(ValueError):
            self.make_player([plant], [Resource.COAL] * 3)

    def test_resources_property_returns_a_copy(self) -> None:
        player, _, _ = self.make_player(
            [self.make_plant(3, [Resource.COAL], 1, 1)],
            [Resource.COAL],
        )

        exposed_inventory = player.resources
        exposed_inventory.clear()

        self.assertEqual(player.resources, [Resource.COAL])

    # buy_resources tests

    def test_buy_resources(self) -> None:
        player, _, market = self.make_player(
            [self.make_plant(3, [Resource.COAL], 1, 1)],
            [Resource.COAL],
            [Resource.COAL, Resource.COAL],
        )

        result = player.buy_resources([Resource.COAL])

        self.assertIsNone(result)
        self.assertEqual(player.resources, [Resource.COAL, Resource.COAL])
        self.assertEqual(market.available, [Resource.COAL])
        self.assertEqual(market.take_calls, [[Resource.COAL]])

    def test_buy_resources_rejects_unavailable_resources(self) -> None:
        player, _, market = self.make_player(
            [self.make_plant(3, [Resource.COAL], 1, 1)],
            [Resource.COAL],
            [Resource.COAL],
        )

        result = player.buy_resources([Resource.COAL, Resource.COAL])

        self.assertIsInstance(result, RequestError)
        self.assertEqual(player.resources, [Resource.COAL])
        self.assertEqual(market.available, [Resource.COAL])
        self.assertEqual(market.take_calls, [])

    def test_buy_resources_rejects_insufficient_storage(self) -> None:
        player, _, market = self.make_player(
            [self.make_plant(3, [Resource.COAL], 1, 1)],
            [Resource.COAL],
            [Resource.COAL, Resource.COAL],
        )

        result = player.buy_resources([Resource.COAL, Resource.COAL])

        self.assertIsInstance(result, RequestError)
        self.assertEqual(player.resources, [Resource.COAL])
        self.assertEqual(market.available, [Resource.COAL, Resource.COAL])
        self.assertEqual(market.take_calls, [])

    # remove_power_plant tests

    def test_remove_power_plant(self) -> None:
        player, plants, _ = self.make_player(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.OIL], 1, 1),
            ],
            [Resource.COAL, Resource.OIL],
        )

        result = player.remove_power_plant(PowerPlantNumber(4), [Resource.OIL])

        self.assertIsNone(result)
        self.assertEqual(player.resources, [Resource.COAL])
        self.assertEqual(plants.best_power_plant(), PowerPlantNumber(3))

    def test_remove_power_plant_rejects_invalid_requests(self) -> None:
        player, plants, _ = self.make_player(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.OIL], 1, 1),
            ],
            [Resource.COAL, Resource.OIL],
        )

        # The player does not own the requested resource.
        result = player.remove_power_plant(
            PowerPlantNumber(4), [Resource.GARBAGE]
        )
        self.assertIsInstance(result, RequestError)

        # The remaining resources would not fit after removing the plant.
        result = player.remove_power_plant(PowerPlantNumber(4), [])
        self.assertIsInstance(result, RequestError)

        # The requested power plant does not exist.
        result = player.remove_power_plant(PowerPlantNumber(5), [])
        self.assertIsInstance(result, RequestError)

        self.assertEqual(player.resources, [Resource.COAL, Resource.OIL])
        self.assertEqual(plants.best_power_plant(), PowerPlantNumber(4))

    # number_of_connectable_cities tests

    def test_number_of_connectable_cities(self) -> None:
        player, _, _ = self.make_player(
            [
                self.make_plant(3, [Resource.COAL], 2, 3),
                self.make_plant(13, [], 0, 2),
            ],
            [Resource.COAL, Resource.COAL],
        )

        self.assertEqual(player.number_of_connectable_cities(), 5)

    # use_power_plant tests

    def test_use_power_plant_consumes_fuel_after_success(self) -> None:
        player, _, _ = self.make_player(
            [self.make_plant(3, [Resource.COAL], 2, 3)],
            [Resource.COAL, Resource.COAL, Resource.COAL],
        )

        result = player.use_power_plant(
            [PowerPlantNumber(3)], [Resource.COAL, Resource.COAL]
        )

        self.assertEqual(result, 3)
        self.assertEqual(player.resources, [Resource.COAL])

    def test_use_power_plant_rejects_invalid_requests_without_consuming_fuel(self) -> None:
        player, _, _ = self.make_player(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.OIL], 1, 1),
            ],
            [Resource.COAL, Resource.COAL, Resource.OIL],
        )

        # The player does not own the selected power plant.
        result = player.use_power_plant([PowerPlantNumber(5)], [Resource.COAL])
        self.assertIsInstance(result, RequestError)

        # The same power plant is selected twice.
        result = player.use_power_plant(
            [PowerPlantNumber(3), PowerPlantNumber(3)],
            [Resource.COAL, Resource.COAL],
        )
        self.assertIsInstance(result, RequestError)

        # The player does not own enough fuel.
        result = player.use_power_plant(
            [PowerPlantNumber(3)], [Resource.COAL] * 3
        )
        self.assertIsInstance(result, RequestError)

        # The fuel is incompatible with the selected power plant.
        result = player.use_power_plant([PowerPlantNumber(3)], [Resource.OIL])
        self.assertIsInstance(result, RequestError)

        # Too much fuel is supplied.
        result = player.use_power_plant(
            [PowerPlantNumber(3)], [Resource.COAL, Resource.COAL]
        )
        self.assertIsInstance(result, RequestError)

        self.assertEqual(
            player.resources,
            [Resource.COAL, Resource.COAL, Resource.OIL],
        )


    # Returning resources to the general supply

    def test_burnt_fuel_returns_to_pool(self) -> None:
        pool = ResourcePoolSpy()
        player = PlayerResources(
            PlayerPowerPlants([self.make_plant(3, [Resource.COAL], 2, 1)]),
            ResourceMarketFake([]),
            [Resource.COAL, Resource.COAL, Resource.COAL],
            resource_pool=pool,
        )
        player.use_power_plant([PowerPlantNumber(3)], [Resource.COAL, Resource.COAL])
        self.assertEqual(pool.returned, [Resource.COAL, Resource.COAL])

    def test_failed_use_returns_nothing_to_pool(self) -> None:
        pool = ResourcePoolSpy()
        player = PlayerResources(
            PlayerPowerPlants([self.make_plant(3, [Resource.COAL], 2, 1)]),
            ResourceMarketFake([]),
            [Resource.COAL],
            resource_pool=pool,
        )
        player.use_power_plant([PowerPlantNumber(3)], [Resource.COAL, Resource.COAL])
        self.assertEqual(pool.returned, [])

    def test_discarded_resources_return_to_pool(self) -> None:
        pool = ResourcePoolSpy()
        player = PlayerResources(
            PlayerPowerPlants([
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.OIL], 1, 1),
            ]),
            ResourceMarketFake([]),
            [Resource.COAL, Resource.OIL],
            resource_pool=pool,
        )
        player.remove_power_plant(PowerPlantNumber(4), [Resource.OIL])
        self.assertEqual(pool.returned, [Resource.OIL])

if __name__ == "__main__":
    unittest.main()
