# pylint: disable=unused-argument, duplicate-code
from typing import Sequence
from power_grid.simple_types import Resource


class InterfaceResourcePoolResourceMarket:
    def can_take_resources_from_storage_space(self, resources: Sequence[Resource]) -> bool:
        assert False

    def get_from_storage_space(self, resources: Sequence[Resource]) -> None:
        assert False

    def take_resources(self, resources: Sequence[Resource]) -> list[Resource]:
        assert False

    def to_string(self) -> str:
        assert False


class InterfaceTownsCheckAndBumpStep:
    def get_max_number_of_houses(self) -> int:
        assert False

    def start_step2(self) -> None:
        assert False

    def start_step3(self) -> None:
        assert False


class InterfacePowerPlantMarketCheckAndBumpStep:
    def is_step3_start(self) -> bool:
        assert False

    def start_step2(self) -> None:
        assert False

    def start_step3(self) -> None:
        assert False


class InterfaceResourceMarketCheckAndBumpStep:
    def start_step2(self) -> None:
        assert False

    def start_step3(self) -> None:
        assert False
