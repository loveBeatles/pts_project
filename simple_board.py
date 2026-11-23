from __future__ import annotations
from typing import Sequence
from power_grid.interfaces import InterfacePlayerBoardFacade
from power_grid.simple_types import PowerPlant, PowerPlantNumber, RequestError, Resource


class SimpleBoard(InterfacePlayerBoardFacade):
    """Minimal player board for integration tests.

    Replace with the real PlayerBoardFacade once it is merged into main.
    """

    def __init__(self, money: int) -> None:
        self.money = money
        self.plants: list[PowerPlant] = []
        self.used: list[list[PowerPlantNumber]] = []

    def outstanding_money(self) -> int:
        return self.money

    def has_enough_money(self, amount: int) -> bool:
        return amount <= self.money

    def spend_money(self, amount: int) -> None:
        assert amount <= self.money
        self.money -= amount

    def receive_power_plant(self, power_plant: PowerPlant, price: int) -> bool:
        if len(self.plants) >= 3:
            return False
        self.spend_money(price)
        self.plants.append(power_plant)
        return True

    def best_power_plant_number(self) -> PowerPlantNumber:
        return max(p.number for p in self.plants)

    def use_power_plants(self, ppns: Sequence[PowerPlantNumber],
                         resources_to_burn: Sequence[Resource]) -> RequestError | None:
        owned = [p.number for p in self.plants]
        if any(ppn not in owned for ppn in ppns):
            return RequestError("Player does not own the power plant.")
        self.used.append(list(ppns))
        return None
