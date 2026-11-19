from __future__ import annotations
from power_grid.interfaces import (
    InterfaceCheckAndBumpStep,
    InterfacePowerPlantMarket,
    InterfaceResourceMarket,
    InterfaceTowns,
)


class CheckAndBumpStep(InterfaceCheckAndBumpStep):
    _step: int
    _num_players: int
    _towns: InterfaceTowns
    _power_plant_market: InterfacePowerPlantMarket
    _resource_market: InterfaceResourceMarket

    def __init__(self, num_players: int,
                 towns: InterfaceTowns,
                 power_plant_market: InterfacePowerPlantMarket,
                 resource_market: InterfaceResourceMarket) -> None:
        assert 2 <= num_players <= 6
        self._step = 1
        self._num_players = num_players
        self._towns = towns
        self._power_plant_market = power_plant_market
        self._resource_market = resource_market

    def get_step(self) -> int:
        return self._step

    def _step_2_threshold(self) -> int:
        return 6 if self._num_players == 6 else 7

    def _start_step_2(self) -> None:
        self._step = 2
        self._towns.start_step_2()
        self._power_plant_market.start_step_2()
        self._resource_market.start_step_2()

    def _start_step_3(self) -> None:
        self._step = 3
        self._towns.start_step_3()
        self._power_plant_market.start_step_3()
        self._resource_market.start_step_3()

    def check_and_bump_to_step_2(self) -> None:
        if self._step != 1:
            return
        if self._towns.get_max_number_of_houses() >= self._step_2_threshold():
            self._start_step_2()

    def check_and_bump_to_step_3(self) -> None:
        if self._step >= 3:
            return
        if not self._power_plant_market.is_step_3_start():
            return
        if self._step == 1:
            self._start_step_2()
        self._start_step_3()
