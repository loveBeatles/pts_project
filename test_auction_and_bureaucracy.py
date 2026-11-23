"""Integration: AuctionPowerPlants + PowerPlantMarket + Bureaucracy
+ ResourceMarket + ResourcePool.

Scenario: two players auction power plants (with a bidding war), then power
their cities; at the end of bureaucracy the resource market refills from the
pool and the highest plant of the future market goes under the stack.
"""
from __future__ import annotations
import json
import unittest
from typing import Sequence
from power_grid.interfaces import InterfacePlayerBoardFacade, InterfaceShuffler
from power_grid.phases.auction_power_plants import AuctionPowerPlants
from power_grid.phases.bureaucracy import Bureaucracy
from power_grid.power_plant_market import PowerPlantMarket
from power_grid.resource_market import ResourceMarket
from power_grid.resource_pool import ResourcePool
from power_grid.simple_types import (
    PhaseStatus, PlayerColor, PowerPlant, PowerPlantNumber, RequestError, Resource,
)
from .simple_board import SimpleBoard

RED, BLUE = PlayerColor.RED, PlayerColor.BLUE
CONT, END = PhaseStatus.PHASE_CONTINUES, PhaseStatus.PHASE_ENDS


class NoShuffle(InterfaceShuffler):
    def shuffle(self, power_plants: Sequence[PowerPlant]) -> list[PowerPlant]:
        return list(power_plants)


def plant(number: int) -> PowerPlant:
    return PowerPlant(PowerPlantNumber(number), [Resource.COAL], 2, 1)


class TestAuctionAndBureaucracy(unittest.TestCase):
    def setUp(self) -> None:
        self.market = PowerPlantMarket(
            [plant(n) for n in range(3, 11)], [plant(13), plant(11), plant(12)], NoShuffle())
        pool = ResourcePool({Resource.COAL: 5, Resource.OIL: 5,
                             Resource.GARBAGE: 5, Resource.URANIUM: 5})
        pattern = {step: {Resource.COAL: 3, Resource.OIL: 2,
                          Resource.GARBAGE: 1, Resource.URANIUM: 1} for step in (1, 2, 3)}
        self.resource_market = ResourceMarket(pool, [], pattern)
        self.red, self.blue = SimpleBoard(50), SimpleBoard(50)
        self.boards: dict[PlayerColor, InterfacePlayerBoardFacade] = {
            RED: self.red, BLUE: self.blue}
        self.auction = AuctionPowerPlants(self.boards, self.market)
        self.bureaucracy = Bureaucracy(self.boards, self.resource_market, self.market)

    def test_scenario(self) -> None:
        self.auction.start_phase([RED, BLUE], first_round=True)
        # Red opens on plant 6, Blue outbids, Red wins for 9
        self.assertEqual(self.auction.start_auction(RED, PowerPlantNumber(6), 6), CONT)
        self.assertEqual(self.auction.raise_bid(BLUE, 8), CONT)
        self.assertEqual(self.auction.raise_bid(RED, 9), CONT)
        self.assertEqual(self.auction.pass_bid(BLUE), CONT)
        self.assertEqual([p.number.number for p in self.red.plants], [6])
        self.assertEqual(self.red.money, 41)
        # 13 was drawn into the future market
        state = json.loads(self.market.state())
        self.assertEqual(state["current"], [3, 4, 5, 7])
        self.assertEqual(state["future"], [8, 9, 10, 13])

        # Blue cannot pass in the first round, plant 7 (future 8 moves up)
        self.assertIsInstance(self.auction.pass_phase(BLUE), RequestError)
        self.assertIsInstance(self.auction.start_auction(BLUE, PowerPlantNumber(8), 8),
                              RequestError)
        self.assertEqual(self.auction.start_auction(BLUE, PowerPlantNumber(7), 7), END)
        self.assertEqual(self.blue.money, 43)
        self.assertEqual(json.loads(self.market.state())["current"], [3, 4, 5, 8])

        # Bureaucracy: both players power cities, then markets are prepared
        self.bureaucracy.start_phase([RED, BLUE])
        self.assertEqual(self.bureaucracy.use_power_plants(RED, [PowerPlantNumber(6)], []),
                         CONT)
        self.assertEqual(self.bureaucracy.use_power_plants(BLUE, [PowerPlantNumber(7)], []),
                         END)
        state = json.loads(self.market.state())
        self.assertEqual(state["future"], [9, 10, 11, 12])   # 13 went under the stack
        resources = json.loads(self.resource_market.to_string())
        self.assertEqual(resources["coal"], 3)
        self.assertEqual(resources["pool"]["coal"], 2)


if __name__ == "__main__":
    unittest.main()
