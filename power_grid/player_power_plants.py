from collections import Counter
from itertools import combinations
from typing import Sequence

from power_grid.simple_types import PowerPlant, PowerPlantNumber, RequestError, Resource


class PlayerPowerPlants:
    """Track owned plants and calculate storage and production capabilities."""

    MAX_POWER_PLANTS = 3
    _power_plants: list[PowerPlant]

    def __init__(self, power_plants: Sequence[PowerPlant] = ()) -> None:
        """Create an owner with up to three plants, including an empty set."""
        plant_numbers = [plant.number for plant in power_plants]
        if len(power_plants) > self.MAX_POWER_PLANTS:
            raise ValueError("A player cannot own more than three power plants.")
        if len(plant_numbers) != len(set(plant_numbers)):
            raise ValueError("Power plant numbers must be unique.")
        self._power_plants = list(power_plants)

    def best_power_plant(self) -> PowerPlantNumber:
        if not self._power_plants:
            raise ValueError("The player does not own a power plant.")
        return max(self._power_plants, key=lambda plant: plant.number.number).number

    def receive_power_plant(self, power_plant: PowerPlant) -> bool:
        if len(self._power_plants) >= self.MAX_POWER_PLANTS:
            return False
        if any(plant.number == power_plant.number for plant in self._power_plants):
            return False
        self._power_plants.append(power_plant)
        return True

    def remove_power_plant(
        self, ppn: PowerPlantNumber, new_resources: Sequence[Resource]
    ) -> RequestError | None:
        """new_resources represents the player's complete inventory after the
        removal and any resource transfers or returns have been decided."""

        plant_to_remove = next((plant for plant in self._power_plants if plant.number == ppn), None)
        if plant_to_remove is None:
            return RequestError("The player does not own that power plant.")

        remaining_plants = [plant for plant in self._power_plants if plant.number != ppn]
        if not self._resources_fit(remaining_plants, new_resources):
            return RequestError("The remaining power plants cannot store those resources.")

        self._power_plants = remaining_plants
        return None

    def number_of_connectable_cities(self, resources: Sequence[Resource]) -> int:
        maximum = 0
        for number_to_use in range(len(self._power_plants) + 1):
            for plants in combinations(self._power_plants, number_to_use):
                if self._can_fuel_plants(plants, resources, allow_unused=True):
                    maximum = max(maximum, sum(plant.number_of_cities for plant in plants))
        return maximum

    def can_store_resources(self, resources: Sequence[Resource]) -> bool:
        return self._resources_fit(self._power_plants, resources)

    def use_power_plant(
        self,
        ppns: Sequence[PowerPlantNumber],
        resources_to_burn: Sequence[Resource],
    ) -> int | RequestError:
        """This method does not consume resources. The owning resource component
        should remove the validated fuel from its inventory after success."""
        
        if len(ppns) != len(set(ppns)):
            return RequestError("A power plant cannot be selected more than once.")

        selected_numbers = set(ppns)
        plants = [plant for plant in self._power_plants if plant.number in selected_numbers]
        if len(plants) != len(ppns):
            return RequestError("The player does not own every selected power plant.")

        if not self._can_fuel_plants(plants, resources_to_burn):
            return RequestError("The selected resources cannot fuel those power plants.")

        return sum(plant.number_of_cities for plant in plants)

    @classmethod
    def _resources_fit(cls, plants: Sequence[PowerPlant], resources: Sequence[Resource]) -> bool:
        return cls._can_assign_resources(plants, resources, storage=True)

    @classmethod
    def _can_fuel_plants(
        cls,
        plants: Sequence[PowerPlant],
        resources: Sequence[Resource],
        allow_unused: bool = False,
    ) -> bool:
        return cls._can_assign_resources(plants, resources, storage=False, allow_unused=allow_unused)

    @staticmethod
    def _can_assign_resources(
        plants: Sequence[PowerPlant],
        resources: Sequence[Resource],
        storage: bool,
        allow_unused: bool = False,
    ) -> bool:
        """Assign resource counts to compatible plants without exceeding limits."""
        available = Counter(resources)

        def assign_plant(plant_index: int) -> bool:
            if plant_index == len(plants):
                return allow_unused or not any(available.values())

            plant = plants[plant_index]
            limit = plant.resource_amount * (2 if storage else 1)
            accepted = tuple(dict.fromkeys(plant.accepted_resources))

            def assign_resource_type(resource_index: int, remaining: int) -> bool:
                if resource_index == len(accepted):
                    if not storage and remaining != 0:
                        return False
                    return assign_plant(plant_index + 1)

                resource = accepted[resource_index]
                maximum = min(available[resource], remaining)
                for count in range(maximum + 1):
                    available[resource] -= count
                    if assign_resource_type(resource_index + 1, remaining - count):
                        available[resource] += count
                        return True
                    available[resource] += count
                return False

            return assign_resource_type(0, limit)

        return assign_plant(0)

