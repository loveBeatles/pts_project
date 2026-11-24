"""Builds a ready-to-play game from its components (standard Power Grid setup)."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from power_grid.check_and_bump_step import CheckAndBumpStep
from power_grid.game import Game, GameComponents, GamePhases
from power_grid.interfaces import (
    InterfaceAuctionPowerPlants,
    InterfacePlayerBoardFacade,
    InterfacePowerPlantMarket,
    InterfaceTowns,
)
from power_grid.phases.building_houses import BuildingHouses
from power_grid.phases.bureaucracy import Bureaucracy
from power_grid.phases.buying_resources import BuyingResources
from power_grid.phases.determine_player_order import DeterminePlayerOrder
from power_grid.player_facade import PlayerFacade
from power_grid.player_money import PlayerMoney
from power_grid.player_power_plants import PlayerPowerPlants
from power_grid.player_resources import PlayerResources
from power_grid.resource_market import ResourceMarket
from power_grid.resource_pool import ResourcePool
from power_grid.simple_types import PlayerColor, Resource

COAL, OIL, GARBAGE, URANIUM = Resource.COAL, Resource.OIL, Resource.GARBAGE, Resource.URANIUM

TOTAL_RESOURCES: dict[Resource, int] = {COAL: 24, OIL: 24, GARBAGE: 24, URANIUM: 12}
STARTING_MARKET: dict[Resource, int] = {COAL: 24, OIL: 18, GARBAGE: 6, URANIUM: 2}


def _pattern(coal: int, oil: int, garbage: int, uranium: int) -> dict[Resource, int]:
    return {COAL: coal, OIL: oil, GARBAGE: garbage, URANIUM: uranium}


# number of players -> step -> resources added to the market in Bureaucracy
REFILL_PATTERNS: dict[int, dict[int, dict[Resource, int]]] = {
    2: {1: _pattern(3, 2, 1, 1), 2: _pattern(4, 2, 2, 1), 3: _pattern(3, 4, 3, 1)},
    3: {1: _pattern(4, 2, 1, 1), 2: _pattern(5, 3, 2, 1), 3: _pattern(3, 4, 3, 1)},
    4: {1: _pattern(5, 3, 2, 1), 2: _pattern(6, 4, 3, 2), 3: _pattern(4, 5, 4, 2)},
    5: {1: _pattern(5, 4, 3, 2), 2: _pattern(7, 5, 3, 3), 3: _pattern(5, 6, 5, 2)},
    6: {1: _pattern(7, 5, 3, 2), 2: _pattern(9, 6, 5, 3), 3: _pattern(6, 7, 6, 3)},
}

AuctionFactory = Callable[
    [Mapping[PlayerColor, InterfacePlayerBoardFacade], InterfacePowerPlantMarket],
    InterfaceAuctionPowerPlants,
]


def create_resource_market(number_of_players: int) -> tuple[ResourcePool, ResourceMarket]:
    """Standard starting market; resources not on the market are in the pool."""
    pool = ResourcePool({x: TOTAL_RESOURCES[x] - STARTING_MARKET[x] for x in Resource})
    starting = [x for x in Resource for _ in range(STARTING_MARKET[x])]
    return pool, ResourceMarket(pool, starting, REFILL_PATTERNS[number_of_players])


def create_game(initial_order: Sequence[PlayerColor], towns: InterfaceTowns,
                power_plant_market: InterfacePowerPlantMarket,
                auction_factory: AuctionFactory, starting_money: int = 50) -> Game:
    """Creates a game in the auction phase of the first round.

    Towns, the power plant market and the auction are passed in, so that each
    team member can plug in own implementations. initial_order should be random.
    """
    players = list(initial_order)
    pool, resource_market = create_resource_market(len(players))
    boards: dict[PlayerColor, InterfacePlayerBoardFacade] = {}
    for color in players:
        plants = PlayerPowerPlants()
        boards[color] = PlayerFacade(
            PlayerMoney(color, starting_money),
            plants,
            PlayerResources(plants, resource_market, resource_pool=pool),
            power_plant_market,
            resource_market,
        )
    step = CheckAndBumpStep(len(players), towns, power_plant_market, resource_market)
    phases = GamePhases(
        auction=auction_factory(boards, power_plant_market),
        buying_resources=BuyingResources(boards),
        building_houses=BuildingHouses(boards, towns, power_plant_market, step),
        bureaucracy=Bureaucracy(boards, resource_market, power_plant_market, towns),
    )
    components = GameComponents(
        player_boards=boards,
        towns=towns,
        player_order=DeterminePlayerOrder(players, towns, boards),
        step=step,
    )
    return Game(players, phases, components)
