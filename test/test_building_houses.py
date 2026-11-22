from __future__ import annotations

from collections.abc import Sequence
import unittest

from power_grid.interfaces import (
    InterfaceCheckAndBumpStep,
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceTowns,
)
from power_grid.phases.building_houses import BuildingHouses
from power_grid.simple_types import PhaseStatus, PlayerColor, RequestError


class StubBuildingBoard(InterfacePlayerBoardFacade):
    def __init__(self, money: int) -> None:
        self._money = money

    def outstanding_money(self) -> int:
        return self._money

    def spend_money(self, amount: int) -> None:
        self._money -= amount


class StubBuildingTowns(InterfaceTowns):
    def __init__(self, players: Sequence[PlayerColor]) -> None:
        self._houses: dict[PlayerColor, int] = {player: 0 for player in players}
        self.purchases: list[tuple[PlayerColor, list[str]]] = []

    def buy_houses(
        self, player: PlayerColor, town_names: Sequence[str], max_money: int
    ) -> int | RequestError:
        if "INVALID" in town_names:
            return RequestError("City is not reachable")
        cost = len(town_names) * 15
        if cost > max_money:
            return RequestError("Insufficient Elektro")
        self._houses[player] += len(town_names)
        self.purchases.append((player, list(town_names)))
        return cost

    def get_max_number_of_houses(self) -> int:
        return max(self._houses.values(), default=0)


class SpyBuildingPlantMarket(InterfacePowerPlantMarket):
    def __init__(self) -> None:
        self.thresholds_checked: list[int] = []

    def remove_power_plants_cheaper_than(self, value: int) -> None:
        self.thresholds_checked.append(value)


class SpyStepChecker(InterfaceCheckAndBumpStep):
    def __init__(self) -> None:
        self.step_2_checks = 0

    def check_and_bump_to_step_2(self) -> None:
        self.step_2_checks += 1


class TestBuildingHouses(unittest.TestCase):
    def test_reverse_order_payment_market_trim_and_step2_check(self) -> None:
        players = [PlayerColor.RED, PlayerColor.BLUE, PlayerColor.GREEN]
        boards = {
            PlayerColor.RED: StubBuildingBoard(50),
            PlayerColor.BLUE: StubBuildingBoard(50),
            PlayerColor.GREEN: StubBuildingBoard(50),
        }
        towns = StubBuildingTowns(players)
        market = SpyBuildingPlantMarket()
        step_checker = SpyStepChecker()

        phase = BuildingHouses(boards, towns, market, step_checker)
        phase.start_phase(players)

        # Out of turn player rejected
        self.assertIsInstance(
            phase.build_houses(PlayerColor.RED, ["Berlin"]), RequestError
        )

        # Green goes first (reverse order), builds 2 houses for 30 Elektro
        self.assertEqual(
            phase.build_houses(PlayerColor.GREEN, ["Berlin", "Hamburg"]),
            PhaseStatus.PHASE_CONTINUES,
        )
        self.assertEqual(boards[PlayerColor.GREEN].outstanding_money(), 20)
        self.assertEqual(market.thresholds_checked, [2])
        self.assertEqual(step_checker.step_2_checks, 0)

        # Blue passes (0 houses, 0 Elektro spent)
        self.assertEqual(
            phase.build_houses(PlayerColor.BLUE, []), PhaseStatus.PHASE_CONTINUES
        )
        self.assertEqual(boards[PlayerColor.BLUE].outstanding_money(), 50)
        self.assertEqual(market.thresholds_checked, [2, 2])
        self.assertEqual(step_checker.step_2_checks, 0)

        # Red goes last, builds 1 house for 15 Elektro -> phase ends and checks Step 2
        self.assertEqual(
            phase.build_houses(PlayerColor.RED, ["Munich"]), PhaseStatus.PHASE_ENDS
        )
        self.assertEqual(boards[PlayerColor.RED].outstanding_money(), 35)
        self.assertEqual(market.thresholds_checked, [2, 2, 2])
        self.assertEqual(step_checker.step_2_checks, 1)

    def test_failed_build_does_not_deduct_money_or_skip_turn(self) -> None:
        players = [PlayerColor.RED, PlayerColor.BLUE]
        boards = {
            PlayerColor.RED: StubBuildingBoard(20),
            PlayerColor.BLUE: StubBuildingBoard(50),
        }
        towns = StubBuildingTowns(players)
        market = SpyBuildingPlantMarket()
        step_checker = SpyStepChecker()

        phase = BuildingHouses(boards, towns, market, step_checker)
        phase.start_phase(players)

        # Blue attempts invalid city -> rejected, turn stays active
        self.assertIsInstance(
            phase.build_houses(PlayerColor.BLUE, ["INVALID"]), RequestError
        )
        self.assertEqual(boards[PlayerColor.BLUE].outstanding_money(), 50)
        self.assertEqual(market.thresholds_checked, [])

        # Blue retries with 1 valid house (15 Elektro) -> succeeds
        self.assertEqual(
            phase.build_houses(PlayerColor.BLUE, ["Frankfurt"]),
            PhaseStatus.PHASE_CONTINUES,
        )
        self.assertEqual(boards[PlayerColor.BLUE].outstanding_money(), 35)

        # Red attempts 2 houses (30 Elektro > 20 available) -> rejected, then passes
        self.assertIsInstance(
            phase.build_houses(PlayerColor.RED, ["Cologne", "Essen"]), RequestError
        )
        self.assertEqual(
            phase.build_houses(PlayerColor.RED, []), PhaseStatus.PHASE_ENDS
        )
        self.assertEqual(step_checker.step_2_checks, 1)
