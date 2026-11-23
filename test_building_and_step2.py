"""Integration: Towns + Connections + BuildingHouses + CheckAndBumpStep
+ PowerPlantMarket + ResourceMarket + ResourcePool.

Scenario: Red builds a network of 7 towns, which starts step 2 at the end
of the building phase. In step 2 Blue can build a second house in Red's town.
"""
from __future__ import annotations
import json
import unittest
from typing import Sequence
from power_grid.check_and_bump_step import CheckAndBumpStep
from power_grid.connections import Connections
from power_grid.interfaces import InterfacePlayerBoardFacade, InterfaceShuffler
from power_grid.phases.building_houses import BuildingHouses
from power_grid.power_plant_market import PowerPlantMarket
from power_grid.resource_market import ResourceMarket
from power_grid.resource_pool import ResourcePool
from power_grid.simple_types import (
    PhaseStatus, PlayerColor, PowerPlant, PowerPlantNumber, RequestError, Resource,
)
from power_grid.towns import Towns
from .simple_board import SimpleBoard

RED, BLUE = PlayerColor.RED, PlayerColor.BLUE


class NoShuffle(InterfaceShuffler):
    def shuffle(self, power_plants: Sequence[PowerPlant]) -> list[PowerPlant]:
        return list(power_plants)


def plant(number: int) -> PowerPlant:
    return PowerPlant(PowerPlantNumber(number), [Resource.COAL], 2, 1)


class TestBuildingAndStep2(unittest.TestCase):
    def setUp(self) -> None:
        names = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]
        # chain T1 -3- T2 -3- ... -3- T8
        connections = Connections([(a, b, 3) for a, b in zip(names, names[1:])])
        self.towns = Towns(names, connections)
        self.power_plant_market = PowerPlantMarket(
            [plant(n) for n in range(3, 11)], [plant(n) for n in range(11, 20)], NoShuffle())
        pool = ResourcePool({r: 30 for r in Resource})
        pattern = {
            1: {Resource.COAL: 3, Resource.OIL: 2, Resource.GARBAGE: 1, Resource.URANIUM: 1},
            2: {Resource.COAL: 4, Resource.OIL: 2, Resource.GARBAGE: 2, Resource.URANIUM: 1},
            3: {Resource.COAL: 3, Resource.OIL: 4, Resource.GARBAGE: 3, Resource.URANIUM: 1},
        }
        self.resource_market = ResourceMarket(pool, [], pattern)
        self.step = CheckAndBumpStep(2, self.towns, self.power_plant_market,
                                     self.resource_market)
        self.boards: dict[PlayerColor, InterfacePlayerBoardFacade] = {
            RED: SimpleBoard(200), BLUE: SimpleBoard(60)}
        self.phase = BuildingHouses(self.boards, self.towns, self.power_plant_market,
                                    self.step)

    def test_scenario(self) -> None:
        # Player order Red, Blue -> Blue builds first in phase 4
        self.phase.start_phase([RED, BLUE])
        self.assertIsInstance(self.phase.build_houses(RED, ["T1"]), RequestError)
        self.assertEqual(self.phase.build_houses(BLUE, ["T8"]), PhaseStatus.PHASE_CONTINUES)
        self.assertEqual(self.boards[BLUE].outstanding_money(), 50)

        red_towns = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
        self.assertEqual(self.phase.build_houses(RED, red_towns), PhaseStatus.PHASE_ENDS)
        # 7 houses x 10 + 6 connections x 3
        self.assertEqual(self.boards[RED].outstanding_money(), 200 - 70 - 18)
        self.assertEqual(self.towns.get_max_number_of_houses(), 7)

        # Plants 3..7 removed because Red has 7 houses, then step 2 removed the lowest
        self.assertEqual(self.step.get_step(), 2)
        market = json.loads(self.power_plant_market.state())
        self.assertEqual(market["step"], 2)
        self.assertEqual(market["current"], [9, 10, 11, 12])

        # Step 2 refill pattern is used
        self.resource_market.refill()
        resources = json.loads(self.resource_market.to_string())
        self.assertEqual(resources["coal"], 4)
        self.assertEqual(resources["pool"]["coal"], 26)

        # Second space of a town is open now (15) for Blue, connected from T8
        self.phase.start_phase([RED, BLUE])
        self.assertEqual(self.phase.build_houses(BLUE, ["T7"]), PhaseStatus.PHASE_CONTINUES)
        self.assertEqual(self.boards[BLUE].outstanding_money(), 50 - 15 - 3)
        self.assertEqual(json.loads(self.towns.state())["towns"]["T7"], ["Red", "Blue"])


if __name__ == "__main__":
    unittest.main()
