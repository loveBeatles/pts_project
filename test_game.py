from __future__ import annotations

import json
import unittest
from collections.abc import Sequence

from power_grid.game import Game, GameComponents, GamePhases
from power_grid.interfaces import (
    InterfaceAuctionPowerPlants,
    InterfaceBuildingHouses,
    InterfaceBureaucracy,
    InterfaceBuyingResources,
    InterfaceCheckAndBumpStep,
    InterfaceDeterminePlayerOrder,
    InterfacePlayerBoardFacade,
    InterfaceTowns,
)
from power_grid.simple_types import (
    GamePhase,
    PhaseStatus,
    PlayerColor,
    PowerPlantNumber,
    RequestError,
    Resource,
)

RED, BLUE = PlayerColor.RED, PlayerColor.BLUE
CONT, END = PhaseStatus.PHASE_CONTINUES, PhaseStatus.PHASE_ENDS


class PhaseFake(InterfaceBuyingResources, InterfaceBuildingHouses, InterfaceBureaucracy):
    """Ends the phase when the scripted status says so."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.next_status: PhaseStatus | RequestError = CONT
        self.started_with: list[list[PlayerColor]] = []
        self.calls = 0

    def start_phase(self, player_order: Sequence[PlayerColor]) -> None:
        self.started_with.append(list(player_order))

    def _act(self) -> PhaseStatus | RequestError:
        self.calls += 1
        return self.next_status

    def buy_resources(self, player: PlayerColor,
                      removed_resources: Sequence[Resource]) -> PhaseStatus | RequestError:
        return self._act()

    def build_houses(self, player: PlayerColor,
                     town_names: Sequence[str]) -> PhaseStatus | RequestError:
        return self._act()

    def use_power_plants(self, player: PlayerColor, ppns: Sequence[PowerPlantNumber],
                         resources_to_burn: Sequence[Resource]) -> PhaseStatus | RequestError:
        return self._act()

    def get_state(self) -> str:
        return json.dumps({"phase": self.name})


class AuctionFake(InterfaceAuctionPowerPlants):
    def __init__(self) -> None:
        self.next_status: PhaseStatus | RequestError = CONT
        self.started_with: list[tuple[list[PlayerColor], bool]] = []

    def start_phase(self, player_order: Sequence[PlayerColor], first_round: bool = False) -> None:
        self.started_with.append((list(player_order), first_round))

    def start_auction(self, player: PlayerColor, ppn: PowerPlantNumber,
                      price: int) -> PhaseStatus | RequestError:
        return self.next_status

    def raise_bid(self, player: PlayerColor, price: int) -> PhaseStatus | RequestError:
        return self.next_status

    def pass_bid(self, player: PlayerColor) -> PhaseStatus | RequestError:
        return self.next_status

    def pass_phase(self, player: PlayerColor) -> PhaseStatus | RequestError:
        return self.next_status

    def discard_power_plant(self, player: PlayerColor, ppn: PowerPlantNumber,
                            removed_resources: Sequence[Resource]) -> PhaseStatus | RequestError:
        return self.next_status

    def get_state(self) -> str:
        return json.dumps({"phase": "auction"})


class BoardFake(InterfacePlayerBoardFacade):
    def state(self) -> str:
        return json.dumps({"money": 50})


class TownsFake(InterfaceTowns):
    def __init__(self) -> None:
        self.max_houses = 0

    def get_max_number_of_houses(self) -> int:
        return self.max_houses


class OrderFake(InterfaceDeterminePlayerOrder):
    def __init__(self) -> None:
        self.order = [BLUE, RED]

    def reorder(self) -> list[PlayerColor]:
        return list(self.order)

    def game_result(self) -> list[PlayerColor]:
        return [RED, BLUE]


class StepFake(InterfaceCheckAndBumpStep):
    def __init__(self) -> None:
        self.step3_checks = 0

    def get_step(self) -> int:
        return 1

    def check_and_bump_to_step3(self) -> None:
        self.step3_checks += 1


class TestGame(unittest.TestCase):  # pylint: disable=too-many-instance-attributes
    def setUp(self) -> None:
        self.auction = AuctionFake()
        self.buying = PhaseFake("buying")
        self.building = PhaseFake("building")
        self.bureaucracy = PhaseFake("bureaucracy")
        self.towns = TownsFake()
        self.order = OrderFake()
        self.step = StepFake()
        self.game = Game(
            [RED, BLUE],
            GamePhases(self.auction, self.buying, self.building, self.bureaucracy),
            GameComponents({RED: BoardFake(), BLUE: BoardFake()}, self.towns,
                           self.order, self.step))

    def finish_auction(self) -> None:
        self.auction.next_status = END
        self.assertEqual(self.game.pass_auction(RED), END)

    def test_starts_with_first_round_auction(self) -> None:
        self.assertEqual(self.game.phase, GamePhase.AUCTION_POWER_PLANTS)
        self.assertEqual(self.auction.started_with, [([RED, BLUE], True)])

    def test_actions_in_wrong_phase_are_rejected(self) -> None:
        self.assertIsInstance(self.game.buy_resources(RED, []), RequestError)
        self.assertIsInstance(self.game.build_houses(RED, []), RequestError)
        self.assertIsInstance(self.game.use_power_plants(RED, [], []), RequestError)
        self.assertIsInstance(self.game.game_result(), RequestError)
        self.finish_auction()
        self.assertIsInstance(self.game.raise_bid(RED, 5), RequestError)

    def test_auction_continues(self) -> None:
        self.assertEqual(self.game.start_auction(RED, PowerPlantNumber(3), 3), CONT)
        self.assertEqual(self.game.raise_bid(BLUE, 4), CONT)
        self.assertEqual(self.game.pass_bid(RED), CONT)
        self.assertEqual(self.game.discard_power_plant(BLUE, PowerPlantNumber(3), []), CONT)
        self.assertEqual(self.game.phase, GamePhase.AUCTION_POWER_PLANTS)

    def test_errors_are_passed_through(self) -> None:
        self.auction.next_status = RequestError("bad bid")
        self.assertEqual(self.game.raise_bid(RED, 1), RequestError("bad bid"))
        self.assertEqual(self.game.phase, GamePhase.AUCTION_POWER_PLANTS)

    def test_order_is_determined_again_after_first_auction(self) -> None:
        self.finish_auction()
        self.assertEqual(self.game.phase, GamePhase.BUY_RESOURCES)
        self.assertEqual(self.game.player_order, [BLUE, RED])
        self.assertEqual(self.buying.started_with, [[BLUE, RED]])

    def test_full_round(self) -> None:
        self.finish_auction()
        self.buying.next_status = END
        self.assertEqual(self.game.buy_resources(BLUE, []), END)
        self.assertEqual(self.game.phase, GamePhase.BUY_HOUSES)
        self.building.next_status = END
        self.assertEqual(self.game.build_houses(BLUE, []), END)
        self.assertEqual(self.game.phase, GamePhase.BUREAUCRACY)
        self.order.order = [RED, BLUE]
        self.bureaucracy.next_status = END
        self.assertEqual(self.game.use_power_plants(BLUE, [], []), END)
        self.assertEqual(self.game.phase, GamePhase.AUCTION_POWER_PLANTS)
        self.assertEqual(self.auction.started_with[-1], ([RED, BLUE], False))
        self.assertEqual(self.step.step3_checks, 4)
        self.assertEqual(json.loads(self.game.state().state)["round"], 2)

    def test_second_auction_keeps_order(self) -> None:
        self.finish_auction()
        self.buying.next_status = END
        self.game.buy_resources(BLUE, [])
        self.building.next_status = END
        self.game.build_houses(BLUE, [])
        self.bureaucracy.next_status = END
        self.game.use_power_plants(BLUE, [], [])
        self.order.order = [RED, BLUE]
        self.auction.next_status = END
        self.game.pass_auction(BLUE)
        self.assertEqual(self.game.player_order, [BLUE, RED])

    def test_game_ends_after_building(self) -> None:
        self.finish_auction()
        self.buying.next_status = END
        self.game.buy_resources(BLUE, [])
        self.towns.max_houses = 21
        self.building.next_status = END
        self.assertEqual(self.game.build_houses(BLUE, []), PhaseStatus.GAME_ENDS)
        self.assertEqual(self.game.phase, GamePhase.GAME_END)
        self.assertEqual(self.game.game_result(), [RED, BLUE])
        self.assertIsInstance(self.game.use_power_plants(BLUE, [], []), RequestError)

    def test_state(self) -> None:
        state = json.loads(self.game.state().state)
        self.assertEqual(state["phase"], "AuctionPowerPlants")
        self.assertEqual(state["player_order"], ["Red", "Blue"])
        self.assertEqual(state["phase_state"], {"phase": "auction"})
        self.assertEqual(state["players"]["Red"], {"money": 50})


if __name__ == "__main__":
    unittest.main()
