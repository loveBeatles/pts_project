from __future__ import annotations
import json
import unittest
from typing import Sequence
from power_grid.interfaces import InterfacePlayerBoardFacade, InterfacePowerPlantMarket
from power_grid.phases.auction_power_plants import AuctionPowerPlants
from power_grid.simple_types import (
    PhaseStatus, PlayerColor, PowerPlant, PowerPlantNumber, RequestError, Resource,
)

RED, BLUE, GREEN = PlayerColor.RED, PlayerColor.BLUE, PlayerColor.GREEN
CONT, END = PhaseStatus.PHASE_CONTINUES, PhaseStatus.PHASE_ENDS


def num(n: int) -> PowerPlantNumber:
    return PowerPlantNumber(n)


class MarketFake(InterfacePowerPlantMarket):
    def __init__(self, numbers: Sequence[int]) -> None:
        self.available = list(numbers)
        self.taken: list[int] = []
        self.lowest_removed = 0

    def can_take_power_plant(self, ppn: PowerPlantNumber, price: int) -> RequestError | None:
        if ppn.number not in self.available or price < ppn.number:
            return RequestError("cannot take")
        return None

    def take_power_plant(self, ppn: PowerPlantNumber) -> PowerPlant:
        self.available.remove(ppn.number)
        self.taken.append(ppn.number)
        return PowerPlant(ppn, [Resource.COAL], 2, 1)

    def remove_lowest_power_plant(self) -> None:
        self.lowest_removed += 1


class BoardFake(InterfacePlayerBoardFacade):
    def __init__(self, money: int, plants: Sequence[int] = ()) -> None:
        self.money = money
        self.plants = list(plants)
        self.removed: list[tuple[int, list[Resource]]] = []

    def has_enough_money(self, amount: int) -> bool:
        return amount <= self.money

    def receive_power_plant(self, power_plant: PowerPlant, price: int) -> bool:
        if len(self.plants) >= 3:
            return False
        self.plants.append(power_plant.number.number)
        self.money -= price
        return True

    def remove_power_plant(self, ppn: PowerPlantNumber,
                           removed_resources: Sequence[Resource]) -> RequestError | None:
        if ppn.number not in self.plants:
            return RequestError("not owned")
        self.plants.remove(ppn.number)
        self.removed.append((ppn.number, list(removed_resources)))
        return None


class TestAuctionPowerPlants(unittest.TestCase):
    def setUp(self) -> None:
        self.market = MarketFake([3, 4, 5, 6])
        self.boards = {RED: BoardFake(50), BLUE: BoardFake(50), GREEN: BoardFake(10)}
        self.auction = AuctionPowerPlants(self.boards, self.market)
        self.auction.start_phase([RED, BLUE, GREEN])

    def test_only_first_waiting_player_can_start(self) -> None:
        self.assertIsInstance(self.auction.start_auction(BLUE, num(3), 3), RequestError)
        self.assertIsInstance(self.auction.pass_phase(GREEN), RequestError)

    def test_invalid_opening_bid(self) -> None:
        self.assertIsInstance(self.auction.start_auction(RED, num(5), 4), RequestError)
        self.assertIsInstance(self.auction.start_auction(RED, num(9), 9), RequestError)
        self.assertIsInstance(self.auction.start_auction(RED, num(5), 60), RequestError)

    def test_everybody_passes_bidding(self) -> None:
        self.assertEqual(self.auction.start_auction(RED, num(5), 5), CONT)
        self.assertEqual(self.auction.pass_bid(BLUE), CONT)
        self.assertEqual(self.auction.pass_bid(GREEN), CONT)
        self.assertEqual(self.boards[RED].plants, [5])
        self.assertEqual(self.boards[RED].money, 45)
        self.assertEqual(json.loads(self.auction.get_state())["waiting"], ["Blue", "Green"])

    def test_bidding_war_and_initiator_chooses_again(self) -> None:
        self.auction.start_auction(RED, num(5), 5)
        self.assertEqual(self.auction.raise_bid(BLUE, 6), CONT)
        self.assertIsInstance(self.auction.raise_bid(GREEN, 6), RequestError)  # not higher
        self.assertIsInstance(self.auction.raise_bid(GREEN, 11), RequestError)  # no money
        self.auction.pass_bid(GREEN)
        self.assertEqual(self.auction.raise_bid(RED, 8), CONT)
        self.assertIsInstance(self.auction.pass_bid(RED), RequestError)  # Blue is on turn
        self.auction.pass_bid(BLUE)
        self.assertEqual(self.boards[RED].plants, [5])
        self.assertEqual(self.boards[RED].money, 42)
        # Blue and Green did not buy, Blue is first now
        self.assertIsNone(json.loads(self.auction.get_state())["auction"])
        self.assertIsInstance(self.auction.start_auction(GREEN, num(3), 3), RequestError)
        self.assertEqual(self.auction.start_auction(BLUE, num(3), 3), CONT)

    def test_winner_who_did_not_start_leaves_and_initiator_goes_again(self) -> None:
        self.auction.start_auction(RED, num(4), 4)
        self.auction.raise_bid(BLUE, 7)
        self.auction.pass_bid(GREEN)
        self.auction.pass_bid(RED)
        self.assertEqual(self.boards[BLUE].plants, [4])
        self.assertEqual(json.loads(self.auction.get_state())["waiting"], ["Red", "Green"])

    def test_last_player_buys_without_bidding_and_phase_ends(self) -> None:
        self.auction.pass_phase(RED)
        self.auction.pass_phase(BLUE)
        self.assertEqual(self.auction.start_auction(GREEN, num(3), 3), END)
        self.assertEqual(self.market.lowest_removed, 0)

    def test_nobody_buys_removes_lowest_plant(self) -> None:
        self.auction.pass_phase(RED)
        self.auction.pass_phase(BLUE)
        self.assertEqual(self.auction.pass_phase(GREEN), END)
        self.assertEqual(self.market.lowest_removed, 1)

    def test_cannot_pass_in_first_round(self) -> None:
        self.auction.start_phase([RED, BLUE], first_round=True)
        self.assertIsInstance(self.auction.pass_phase(RED), RequestError)

    def test_player_with_three_plants_must_discard(self) -> None:
        self.boards[RED] = BoardFake(50, [10, 11, 12])
        self.auction = AuctionPowerPlants(self.boards, self.market)
        self.auction.start_phase([RED, BLUE])
        self.assertEqual(self.auction.start_auction(RED, num(6), 6), CONT)
        self.assertEqual(self.auction.pass_bid(BLUE), CONT)
        self.assertEqual(json.loads(self.auction.get_state())["must_discard"], "Red")
        self.assertIsInstance(self.auction.start_auction(BLUE, num(3), 3), RequestError)
        self.assertIsInstance(
            self.auction.discard_power_plant(BLUE, num(10), []), RequestError)
        self.assertIsInstance(
            self.auction.discard_power_plant(RED, num(99), []), RequestError)
        self.assertEqual(self.auction.discard_power_plant(
            RED, num(10), [Resource.COAL]), CONT)
        self.assertEqual(self.boards[RED].plants, [11, 12, 6])
        self.assertEqual(self.boards[RED].removed, [(10, [Resource.COAL])])

    def test_no_bidding_without_auction(self) -> None:
        self.assertIsInstance(self.auction.raise_bid(BLUE, 5), RequestError)
        self.assertIsInstance(self.auction.pass_bid(BLUE), RequestError)


if __name__ == "__main__":
    unittest.main()
