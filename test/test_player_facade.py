from collections import Counter
from collections.abc import Sequence
import json
import unittest

from power_grid.interfaces import InterfacePowerPlantMarket, InterfaceResourceMarket
from power_grid.player_facade import PlayerFacade
from power_grid.player_money import PlayerMoney
from power_grid.player_power_plants import PlayerPowerPlants
from power_grid.player_resources import PlayerResources
from power_grid.simple_types import (
    PlayerColor,
    PowerPlant,
    PowerPlantNumber,
    RequestError,
    Resource,
)


class ResourceMarketFake(InterfaceResourceMarket):
    def __init__(self, resources: Sequence[Resource], price_per_resource: int = 5) -> None:
        self.resources = list(resources)
        self.price_per_resource = price_per_resource
        self.take_calls: list[list[Resource]] = []

    def get_price(self, resources: Sequence[Resource]) -> int | None:
        requested = Counter(resources)
        available = Counter(self.resources)
        if any(count > available[resource] for resource, count in requested.items()):
            return None
        return len(resources) * self.price_per_resource

    def take_resources(self, resources: Sequence[Resource]) -> None:
        requested = list(resources)
        self.take_calls.append(requested)
        for resource in requested:
            self.resources.remove(resource)


class PowerPlantMarketFake(InterfacePowerPlantMarket):
    def __init__(self, power_plants: Sequence[PowerPlant]) -> None:
        self.power_plants = {plant.number: plant for plant in power_plants}
        self.take_calls: list[PowerPlantNumber] = []

    def can_take_power_plant(
        self, ppn: PowerPlantNumber, price: int
    ) -> RequestError | None:
        if ppn not in self.power_plants:
            return RequestError("Power plant is not on the market.")
        if price < ppn.number:
            return RequestError("Bid is below the minimum price.")
        return None

    def take_power_plant(self, ppn: PowerPlantNumber) -> PowerPlant:
        self.take_calls.append(ppn)
        return self.power_plants.pop(ppn)


class TestPlayerFacade(unittest.TestCase):
    @staticmethod
    def make_plant(
        number: int,
        resources: Sequence[Resource],
        resource_amount: int,
        number_of_cities: int,
    ) -> PowerPlant:
        return PowerPlant(
            PowerPlantNumber(number),
            list(resources),
            resource_amount,
            number_of_cities,
        )

    def make_facade(
        self,
        owned_plants: Sequence[PowerPlant] = (),
        starting_resources: Sequence[Resource] = (),
        market_resources: Sequence[Resource] = (),
        market_plants: Sequence[PowerPlant] = (),
        starting_money: int = 50,
        resource_price: int = 5,
    ) -> tuple[PlayerFacade, PlayerMoney, PlayerPowerPlants, PlayerResources,
               ResourceMarketFake, PowerPlantMarketFake]:
        money = PlayerMoney(PlayerColor.RED, starting_money)
        power_plants = PlayerPowerPlants(owned_plants)
        resource_market = ResourceMarketFake(market_resources, resource_price)
        resources = PlayerResources(power_plants, resource_market, starting_resources)
        power_plant_market = PowerPlantMarketFake(market_plants)
        facade = PlayerFacade(
            money,
            power_plants,
            resources,
            power_plant_market,
            resource_market,
        )
        return (
            facade,
            money,
            power_plants,
            resources,
            resource_market,
            power_plant_market,
        )

    def test_facade_delegates_basic_queries_and_spending(self) -> None:
        facade, money, _, _, _, _ = self.make_facade(
            [self.make_plant(3, [Resource.COAL], 1, 2)],
            [Resource.COAL],
        )

        self.assertEqual(facade.best_power_plant_number(), PowerPlantNumber(3))
        self.assertEqual(facade.outstanding_money(), 50)
        self.assertTrue(facade.has_enough_money(50))
        self.assertEqual(facade.number_of_connectable_cities(), 2)

        facade.spend_money(12)

        self.assertEqual(money.current_money, 38)

    def test_receive_power_plant_coordinates_market_plants_and_money(self) -> None:
        new_plant = self.make_plant(5, [Resource.OIL], 1, 2)
        facade, money, power_plants, _, _, plant_market = self.make_facade(
            [self.make_plant(3, [Resource.COAL], 1, 1)],
            market_plants=[new_plant],
        )

        received = facade.receive_power_plant(PowerPlantNumber(5), 8)

        self.assertTrue(received)
        self.assertEqual(money.current_money, 42)
        self.assertEqual(power_plants.best_power_plant(), PowerPlantNumber(5))
        self.assertEqual(plant_market.take_calls, [PowerPlantNumber(5)])

    def test_receive_power_plant_failure_does_not_change_player_or_market(self) -> None:
        market_plant = self.make_plant(10, [], 0, 2)
        existing = [
            self.make_plant(3, [Resource.COAL], 1, 1),
            self.make_plant(4, [Resource.OIL], 1, 1),
            self.make_plant(5, [Resource.GARBAGE], 1, 1),
        ]
        facade, money, _, _, _, plant_market = self.make_facade(
            existing,
            market_plants=[market_plant],
        )

        received = facade.receive_power_plant(PowerPlantNumber(10), 10)

        self.assertFalse(received)
        self.assertEqual(money.current_money, 50)
        self.assertEqual(plant_market.take_calls, [])
        self.assertIn(PowerPlantNumber(10), plant_market.power_plants)

    def test_receive_power_plant_rejects_unaffordable_bid_without_market_change(
        self,
    ) -> None:
        market_plant = self.make_plant(5, [Resource.OIL], 1, 2)
        facade, money, _, _, _, plant_market = self.make_facade(
            market_plants=[market_plant],
            starting_money=4,
        )

        received = facade.receive_power_plant(PowerPlantNumber(5), 5)

        self.assertFalse(received)
        self.assertEqual(money.current_money, 4)
        self.assertEqual(plant_market.take_calls, [])

    def test_remove_power_plant_delegates_resource_discard_and_removal(self) -> None:
        facade, money, power_plants, resources, _, _ = self.make_facade(
            [
                self.make_plant(3, [Resource.COAL], 1, 1),
                self.make_plant(4, [Resource.OIL], 1, 1),
            ],
            [Resource.COAL, Resource.OIL],
        )

        result = facade.remove_power_plant(PowerPlantNumber(4), [Resource.OIL])

        self.assertIsNone(result)
        self.assertEqual(resources.resources, [Resource.COAL])
        self.assertEqual(power_plants.best_power_plant(), PowerPlantNumber(3))
        self.assertEqual(money.current_money, 50)

    def test_buy_resources_charges_money_only_after_success(self) -> None:
        facade, money, _, resources, market, _ = self.make_facade(
            [self.make_plant(3, [Resource.COAL], 1, 1)],
            market_resources=[Resource.COAL],
            starting_money=20,
            resource_price=7,
        )

        result = facade.buy_resources([Resource.COAL])

        self.assertIsNone(result)
        self.assertEqual(money.current_money, 13)
        self.assertEqual(resources.resources, [Resource.COAL])
        self.assertEqual(market.resources, [])

    def test_buy_resources_failure_preserves_money_inventory_and_market(self) -> None:
        facade, money, _, resources, market, _ = self.make_facade(
            [self.make_plant(3, [Resource.COAL], 1, 1)],
            market_resources=[Resource.COAL, Resource.COAL],
            starting_money=10,
            resource_price=6,
        )

        result = facade.buy_resources([Resource.COAL, Resource.COAL])

        self.assertIsInstance(result, RequestError)
        self.assertEqual(money.current_money, 10)
        self.assertEqual(resources.resources, [])
        self.assertEqual(market.resources, [Resource.COAL, Resource.COAL])

    def test_use_power_plants_delegates_and_consumes_fuel(self) -> None:
        facade, _, _, resources, _, _ = self.make_facade(
            [self.make_plant(3, [Resource.COAL], 2, 3)],
            [Resource.COAL, Resource.COAL, Resource.COAL],
        )

        result = facade.use_power_plants(
            [PowerPlantNumber(3)], [Resource.COAL, Resource.COAL]
        )

        self.assertIsNone(result)
        self.assertEqual(resources.resources, [Resource.COAL])

    def test_failed_power_plant_use_preserves_inventory(self) -> None:
        facade, _, _, resources, _, _ = self.make_facade(
            [self.make_plant(3, [Resource.COAL], 1, 1)],
            [Resource.COAL],
        )

        result = facade.use_power_plants([PowerPlantNumber(4)], [Resource.COAL])

        self.assertIsInstance(result, RequestError)
        self.assertEqual(resources.resources, [Resource.COAL])

    def test_state_serializes_public_player_summary(self) -> None:
        facade, _, _, _, _, _ = self.make_facade(
            [self.make_plant(3, [Resource.COAL], 1, 2)],
            [Resource.COAL],
        )

        state = json.loads(facade.state())

        self.assertEqual(state["money"], 50)
        self.assertEqual(state["best_power_plant_number"], 3)
        self.assertEqual(state["connectable_cities"], 2)
        self.assertEqual(state["resources"], ["COAL"])


if __name__ == "__main__":
    unittest.main()
