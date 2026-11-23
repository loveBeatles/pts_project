import json
from collections.abc import Sequence

from power_grid.interfaces import (
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceResourceMarket,
)
from power_grid.player_money import PlayerMoney
from power_grid.player_power_plants import PlayerPowerPlants
from power_grid.player_resources import PlayerResources
from power_grid.simple_types import PowerPlantNumber, RequestError, Resource


class PlayerFacade(InterfacePlayerBoardFacade):
    """Delegate player-board operations to the relevant state components."""

    _player_money: PlayerMoney
    _player_power_plants: PlayerPowerPlants
    _player_resources: PlayerResources
    _power_plant_market: InterfacePowerPlantMarket
    _resource_market: InterfaceResourceMarket

    def __init__(
        self,
        player_money: PlayerMoney,
        player_power_plants: PlayerPowerPlants,
        player_resources: PlayerResources,
        power_plant_market: InterfacePowerPlantMarket,
        resource_market: InterfaceResourceMarket,
    ) -> None:
        """Store the player's components and market interfaces."""
        self._player_money = player_money
        self._player_power_plants = player_power_plants
        self._player_resources = player_resources
        self._power_plant_market = power_plant_market
        self._resource_market = resource_market

    def best_power_plant_number(self) -> PowerPlantNumber:
        return self._player_power_plants.best_power_plant()

    def outstanding_money(self) -> int:
        return self._player_money.current_money

    def spend_money(self, amount: int) -> None:
        self._player_money.spend_money(amount)

    def number_of_connectable_cities(self) -> int:
        return self._player_resources.number_of_connectable_cities()

    def has_enough_money(self, amount: int) -> bool:
        return self._player_money.has_enough_money(amount)

    def receive_power_plant(self, ppn: PowerPlantNumber, price: int) -> bool:
        """Buy and add a plant if possible."""
        if price < 0 or not self._player_money.has_enough_money(price):
            return False
        if not self._player_power_plants.can_receive_power_plant(ppn):
            return False
        if self._power_plant_market.can_take_power_plant(ppn, price) is not None:
            return False

        power_plant = self._power_plant_market.take_power_plant(ppn)
        if not self._player_power_plants.receive_power_plant(power_plant):
            raise RuntimeError("Power plant preflight and receipt results differ.")

        self._player_money.spend_money(price)
        return True

    def remove_power_plant(
        self, ppn: PowerPlantNumber, removed_resources: Sequence[Resource]
    ) -> RequestError | None:
        return self._player_resources.remove_power_plant(ppn, removed_resources)

    def buy_resources(self, resources: Sequence[Resource]) -> RequestError | None:
        requested = list(resources)
        price = self._resource_market.get_price(requested)
        if price is None:
            return RequestError("The requested resources are not available.")
        if not self._player_money.has_enough_money(price):
            return RequestError("The player does not have enough money.")

        error = self._player_resources.buy_resources(requested)
        if error is not None:
            return error

        self._player_money.spend_money(price)
        return None

    def use_power_plants(
        self,
        ppns: Sequence[PowerPlantNumber],
        resources_to_burn: Sequence[Resource],
    ) -> RequestError | None:
        result = self._player_resources.use_power_plant(ppns, resources_to_burn)
        if isinstance(result, RequestError):
            return result
        return None

    def state(self) -> str:
        best_plant_number: int | None
        try:
            best_plant_number = self.best_power_plant_number().number
        except ValueError:
            best_plant_number = None

        state: dict[str, int | list[str] | None] = {
            "money": self.outstanding_money(),
            "best_power_plant_number": best_plant_number,
            "connectable_cities": self.number_of_connectable_cities(),
            "resources": [resource.name for resource in self._player_resources.resources],
        }
        return json.dumps(state)
