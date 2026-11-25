from __future__ import annotations
import json
from collections import Counter
from typing import Mapping, Sequence
from power_grid.interfaces import (
    InterfaceResourcePoolPlayerResources,
    InterfaceResourcePoolResourceMarket,
)
from power_grid.simple_types import Resource


class ResourcePool(InterfaceResourcePoolResourceMarket, InterfaceResourcePoolPlayerResources):
    """General supply of resources that are neither on the market nor owned by players.

    The market refills from here, burnt resources come back here, and when a row of
    the market is empty, resources can be bought directly from here (storage space).
    """
    _resources: dict[Resource, int]

    def __init__(self, resources: Mapping[Resource, int]) -> None:
        assert all(resources.get(x, 0) >= 0 for x in Resource)
        self._resources = {x: resources.get(x, 0) for x in Resource}

    def can_take_resources_from_storage_space(self, resources: Sequence[Resource]) -> bool:
        wanted = Counter(resources)
        return all(wanted[x] <= self._resources[x] for x in Resource)

    def get_from_storage_space(self, resources: Sequence[Resource]) -> None:
        assert self.can_take_resources_from_storage_space(resources)
        for resource in resources:
            self._resources[resource] -= 1

    def take_resources(self, resources: Sequence[Resource]) -> list[Resource]:
        """Takes as many of the requested resources as are available."""
        taken: list[Resource] = []
        for resource in resources:
            if self._resources[resource] > 0:
                self._resources[resource] -= 1
                taken.append(resource)
        return taken

    def return_resources(self, resources: Sequence[Resource]) -> None:
        """Burnt or discarded resources go back to the supply."""
        for resource in resources:
            self._resources[resource] += 1

    def to_string(self) -> str:
        return json.dumps({x.name.lower(): self._resources[x] for x in Resource})
