from __future__ import annotations
from power_grid.interfaces import (
    InterfaceTownsCheckAndBumpStep,
    InterfacePowerPlantMarketCheckAndBumpStep,
    InterfaceResourceMarketCheckAndBumpStep,
)


class CheckAndBumpStep:
    _step: int
    _num_players: int
    _towns: InterfaceTownsCheckAndBumpStep
    _power_plant_market: InterfacePowerPlantMarketCheckAndBumpStep
    _resource_market: InterfaceResourceMarketCheckAndBumpStep

    def __init__(self, num_players: int,
                 towns: InterfaceTownsCheckAndBumpStep,
                 power_plant_market: InterfacePowerPlantMarketCheckAndBumpStep,
                 resource_market: InterfaceResourceMarketCheckAndBumpStep) -> None:
        assert 2 <= num_players <= 6
        self._step = 1
        self._num_players = num_players
        self._towns = towns
        self._power_plant_market = power_plant_market
        self._resource_market = resource_market

    def get_step(self) -> int:
        return self._step

    def _step2_threshold(self) -> int:
        return 6 if self._num_players == 6 else 7

    def _start_step2(self) -> None:
        self._step = 2
        self._towns.start_step2()
        self._power_plant_market.start_step2()
        self._resource_market.start_step2()

    def _start_step3(self) -> None:
        self._step = 3
        self._towns.start_step3()
        self._power_plant_market.start_step3()
        self._resource_market.start_step3()

    def check_and_bump_to_step2(self) -> None:
        if self._step != 1:
            return
        if self._towns.get_max_number_of_houses() >= self._step2_threshold():
            self._start_step2()

    def check_and_bump_to_step3(self) -> None:
        if self._step >= 3:
            return
        if not self._power_plant_market.is_step3_start():
            return
        if self._step == 1:
            self._start_step2()
        self._start_step3()
