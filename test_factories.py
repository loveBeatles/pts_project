from __future__ import annotations

import json
import unittest
from collections.abc import Mapping, Sequence

from power_grid.factories import REFILL_PATTERNS, create_game, create_resource_market
from power_grid.interfaces import (
    InterfaceAuctionPowerPlants,
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceTowns,
)
from power_grid.simple_types import GamePhase, PlayerColor, RequestError, Resource

RED, BLUE, GREEN = PlayerColor.RED, PlayerColor.BLUE, PlayerColor.GREEN


class TownsFake(InterfaceTowns):
    def get_number_of_houses(self, player: PlayerColor) -> int:
        return 0

    def get_max_number_of_houses(self) -> int:
        return 0


class PowerPlantMarketFake(InterfacePowerPlantMarket):
    pass


class AuctionSpy(InterfaceAuctionPowerPlants):
    def __init__(self, boards: Mapping[PlayerColor, InterfacePlayerBoardFacade],
                 market: InterfacePowerPlantMarket) -> None:
        self.boards = boards
        self.market = market
        self.started: list[list[PlayerColor]] = []

    def start_phase(self, player_order: Sequence[PlayerColor], first_round: bool = False) -> None:
        self.started.append(list(player_order))

    def get_state(self) -> str:
        return json.dumps({})


class TestCreateResourceMarket(unittest.TestCase):
    def test_standard_starting_market(self) -> None:
        _, market = create_resource_market(3)
        state = json.loads(market.to_string())
        self.assertEqual((state["coal"], state["oil"], state["garbage"], state["uranium"]),
                         (24, 18, 6, 2))
        self.assertEqual(state["pool"], {"coal": 0, "oil": 6, "garbage": 18, "uranium": 10})

    def test_refill_uses_pattern_for_number_of_players(self) -> None:
        _, market = create_resource_market(4)
        market.refill()
        state = json.loads(market.to_string())
        # coal market is full, oil gets 3, garbage 2, uranium 1
        self.assertEqual((state["coal"], state["oil"], state["garbage"], state["uranium"]),
                         (24, 21, 8, 3))

    def test_patterns_for_all_player_counts(self) -> None:
        for players in range(2, 7):
            self.assertEqual(set(REFILL_PATTERNS[players]), {1, 2, 3})
            create_resource_market(players)

    def test_refill_never_overfills_market(self) -> None:
        pool, market = create_resource_market(2)
        market.take_resources([Resource.COAL])
        pool.return_resources(3 * [Resource.COAL])     # burnt coal comes back
        market.refill()                                  # pattern says 3, only 1 fits
        state = json.loads(market.to_string())
        self.assertEqual(state["coal"], 24)
        self.assertEqual(state["pool"]["coal"], 2)


class TestCreateGame(unittest.TestCase):
    def setUp(self) -> None:
        self.market = PowerPlantMarketFake()
        self.auctions: list[AuctionSpy] = []

        def auction_factory(boards: Mapping[PlayerColor, InterfacePlayerBoardFacade],
                            market: InterfacePowerPlantMarket) -> AuctionSpy:
            auction = AuctionSpy(boards, market)
            self.auctions.append(auction)
            return auction

        self.game = create_game([GREEN, RED, BLUE], TownsFake(), self.market, auction_factory)

    def test_game_starts_with_auction(self) -> None:
        self.assertEqual(self.game.phase, GamePhase.AUCTION_POWER_PLANTS)
        self.assertEqual(self.game.player_order, [GREEN, RED, BLUE])
        self.assertEqual(self.auctions[0].started, [[GREEN, RED, BLUE]])

    def test_auction_gets_boards_and_market(self) -> None:
        auction = self.auctions[0]
        self.assertEqual(set(auction.boards), {GREEN, RED, BLUE})
        self.assertIs(auction.market, self.market)

    def test_players_start_with_money(self) -> None:
        state = json.loads(self.game.state().state)
        self.assertEqual(state["step"], 1)
        for color in ("Green", "Red", "Blue"):
            self.assertEqual(state["players"][color]["money"], 50)

    def test_other_phases_are_wired(self) -> None:
        self.assertIsInstance(self.game.buy_resources(RED, []), RequestError)


if __name__ == "__main__":
    unittest.main()
