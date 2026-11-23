from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from power_grid.interfaces import InterfacePlayerBoardFacade, InterfacePowerPlantMarket
from power_grid.simple_types import (
    PhaseStatus,
    PlayerColor,
    PowerPlant,
    PowerPlantNumber,
    RequestError,
    Resource,
)


@dataclass
class _Auction:
    ppn: PowerPlantNumber
    price: int
    leader: PlayerColor
    bidders: list[PlayerColor]  # players still in the auction, in bidding order
    on_turn: int                # index into bidders


@dataclass(frozen=True)
class _PendingDiscard:
    player: PlayerColor
    plant: PowerPlant
    price: int


class AuctionPowerPlants:
    """Phase 2: auctioning power plants.

    In player order, the first player who has not bought a plant yet either
    starts an auction or passes (not allowed in the first round). Players who
    have not bought a plant in this phase take part in the auction; they raise
    or pass in order. The last remaining bidder buys the plant. A player with
    the maximum number of plants must discard one before receiving the new one.
    If nobody buys a plant, the lowest plant is removed from the market.
    """

    _player_boards: Mapping[PlayerColor, InterfacePlayerBoardFacade]
    _market: InterfacePowerPlantMarket
    _waiting: list[PlayerColor]
    _auction: _Auction | None
    _pending_discard: _PendingDiscard | None
    _first_round: bool
    _somebody_bought: bool

    def __init__(self, player_boards: Mapping[PlayerColor, InterfacePlayerBoardFacade],
                 power_plant_market: InterfacePowerPlantMarket) -> None:
        self._player_boards = player_boards
        self._market = power_plant_market
        self._waiting = []
        self._auction = None
        self._pending_discard = None
        self._first_round = False
        self._somebody_bought = False

    def start_phase(self, player_order: Sequence[PlayerColor], first_round: bool = False) -> None:
        self._waiting = list(player_order)
        self._auction = None
        self._pending_discard = None
        self._first_round = first_round
        self._somebody_bought = False

    # ----- actions -----

    def start_auction(self, player: PlayerColor, ppn: PowerPlantNumber,
                      price: int) -> PhaseStatus | RequestError:
        error = self._check_can_choose(player)
        if error is not None:
            return error
        error = self._market.can_take_power_plant(ppn, price)
        if error is not None:
            return error
        if not self._player_boards[player].has_enough_money(price):
            return RequestError("Player does not have enough money.")
        others = self._waiting[1:]
        self._auction = _Auction(ppn, price, player, [player] + others, 1 % (len(others) + 1))
        return self._resolve_if_decided()

    def raise_bid(self, player: PlayerColor, price: int) -> PhaseStatus | RequestError:
        auction = self._auction
        if auction is None or self._pending_discard is not None:
            return RequestError("No auction is running.")
        if auction.bidders[auction.on_turn] != player:
            return RequestError("It is not this player's turn to bid.")
        if price <= auction.price:
            return RequestError(f"Bid has to be higher than {auction.price}.")
        if not self._player_boards[player].has_enough_money(price):
            return RequestError("Player does not have enough money.")
        auction.price = price
        auction.leader = player
        auction.on_turn = (auction.on_turn + 1) % len(auction.bidders)
        return PhaseStatus.PHASE_CONTINUES

    def pass_bid(self, player: PlayerColor) -> PhaseStatus | RequestError:
        auction = self._auction
        if auction is None or self._pending_discard is not None:
            return RequestError("No auction is running.")
        if auction.bidders[auction.on_turn] != player:
            return RequestError("It is not this player's turn to bid.")
        auction.bidders.pop(auction.on_turn)
        auction.on_turn %= len(auction.bidders)
        return self._resolve_if_decided()

    def pass_phase(self, player: PlayerColor) -> PhaseStatus | RequestError:
        """The player does not want to start an auction (buys nothing this round)."""
        error = self._check_can_choose(player)
        if error is not None:
            return error
        if self._first_round:
            return RequestError("Every player has to buy a power plant in the first round.")
        self._waiting.pop(0)
        return self._phase_status()

    def discard_power_plant(self, player: PlayerColor, ppn: PowerPlantNumber,
                            removed_resources: Sequence[Resource]) -> PhaseStatus | RequestError:
        pending = self._pending_discard
        if pending is None or pending.player != player:
            return RequestError("This player does not have to discard a power plant.")
        board = self._player_boards[player]
        error = board.remove_power_plant(ppn, removed_resources)
        if error is not None:
            return error
        received = board.receive_power_plant(pending.plant, pending.price)
        assert received
        self._pending_discard = None
        return self._finish_purchase(player)

    # ----- helpers -----

    def _check_can_choose(self, player: PlayerColor) -> RequestError | None:
        if self._auction is not None or self._pending_discard is not None:
            return RequestError("An auction is running.")
        if not self._waiting:
            return RequestError("Phase is not active.")
        if self._waiting[0] != player:
            return RequestError("It is not this player's turn.")
        return None

    def _resolve_if_decided(self) -> PhaseStatus:
        auction = self._auction
        assert auction is not None
        if len(auction.bidders) > 1:
            return PhaseStatus.PHASE_CONTINUES
        winner = auction.leader
        plant = self._market.take_power_plant(auction.ppn)
        if not self._player_boards[winner].receive_power_plant(plant, auction.price):
            self._pending_discard = _PendingDiscard(winner, plant, auction.price)
            return PhaseStatus.PHASE_CONTINUES
        return self._finish_purchase(winner)

    def _finish_purchase(self, winner: PlayerColor) -> PhaseStatus:
        self._auction = None
        self._somebody_bought = True
        self._waiting.remove(winner)
        return self._phase_status()

    def _phase_status(self) -> PhaseStatus:
        if self._waiting:
            return PhaseStatus.PHASE_CONTINUES
        if not self._somebody_bought:
            self._market.remove_lowest_power_plant()
        return PhaseStatus.PHASE_ENDS

    def get_state(self) -> str:
        auction = self._auction
        return json.dumps({
            "waiting": [p.value for p in self._waiting],
            "auction": None if auction is None else {
                "power_plant": auction.ppn.number,
                "price": auction.price,
                "leader": auction.leader.value,
                "bidders": [p.value for p in auction.bidders],
                "on_turn": auction.bidders[auction.on_turn].value,
            },
            "must_discard": None if self._pending_discard is None
            else self._pending_discard.player.value,
        })
