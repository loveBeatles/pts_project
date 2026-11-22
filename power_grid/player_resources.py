from collections import Counter
from collections.abc import Sequence

from power_grid.interfaces import InterfaceResourceMarket
from power_grid.player_power_plants import PlayerPowerPlants
from power_grid.simple_types import PowerPlantNumber, RequestError, Resource


class PlayerResources:
    """Own resources and coordinate their use with the player's power plants."""

    _resources: list[Resource]
    _power_plants: PlayerPowerPlants
    _resource_market: InterfaceResourceMarket

    def __init__(
        self,
        power_plants: PlayerPowerPlants,
        resource_market: InterfaceResourceMarket,
        resources: Sequence[Resource] = (),
    ) -> None:
        """Create a resource inventory and reject contents that cannot be stored."""
        self._power_plants = power_plants
        self._resource_market = resource_market
        self._resources = list(resources)
        if not self._power_plants.can_store_resources(self._resources):
            raise ValueError("The power plants cannot store the starting resources.")

    @property
    def resources(self) -> list[Resource]:
        return self._resources.copy()

    def remove_power_plant(
        self,
        ppn: PowerPlantNumber,
        removed_resources: Sequence[Resource],
    ) -> RequestError | None:
        remaining = self._inventory_without(removed_resources)
        if remaining is None:
            return RequestError("The player does not own all specified resources.")

        error = self._power_plants.remove_power_plant(ppn, remaining)
        if error is not None:
            return error

        self._resources = remaining
        return None

    def number_of_connectable_cities(self) -> int:
        return self._power_plants.number_of_connectable_cities(self._resources)

    def buy_resources(self, resources: Sequence[Resource]) -> RequestError | None:
        """Buy resources only when available and the resulting inventory fits."""
        requested = list(resources)
        if self._resource_market.get_price(requested) is None:
            return RequestError("The requested resources are not available.")

        new_inventory = self._resources + requested
        if not self._power_plants.can_store_resources(new_inventory):
            return RequestError("The power plants cannot store the requested resources.")

        self._resource_market.take_resources(requested)
        self._resources = new_inventory
        return None

    def use_power_plant(
        self,
        ppns: Sequence[PowerPlantNumber],
        resources_to_burn: Sequence[Resource],
    ) -> int | RequestError:
        """Validate and consume fuel, returning the number of cities supplied."""
        fuel = list(resources_to_burn)
        remaining = self._inventory_without(fuel)
        if remaining is None:
            return RequestError("The player does not own all specified fuel.")

        result = self._power_plants.use_power_plant(ppns, fuel)
        if isinstance(result, RequestError):
            return result

        self._resources = remaining
        return result

    def _inventory_without(
        self, resources_to_remove: Sequence[Resource]
    ) -> list[Resource] | None:
        """Return the inventory after removing a multiset, or None if it is absent."""
        to_remove = Counter(resources_to_remove)
        if any(to_remove[resource] > self._resources.count(resource) for resource in to_remove):
            return None

        remaining = self._resources.copy()
        for resource in resources_to_remove:
            remaining.remove(resource)
        return remaining
