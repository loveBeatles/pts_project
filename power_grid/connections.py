from __future__ import annotations
import heapq
from typing import Sequence


class Connections:
    _distances: list[tuple[str, str, int]]
    _graph: dict[str, list[tuple[str, int]]]

    def __init__(self, distances: Sequence[tuple[str, str, int]]) -> None:
        self._distances = list(distances)
        self._graph = {}
        for town_a, town_b, cost in self._distances:
            assert cost >= 0
            self._graph.setdefault(town_a, []).append((town_b, cost))
            self._graph.setdefault(town_b, []).append((town_a, cost))

    def _shortest_cost(self, network: set[str], target: str) -> int:
        if target in network:
            return 0
        best: dict[str, int] = {town: 0 for town in network}
        queue: list[tuple[int, str]] = [(0, town) for town in network]
        heapq.heapify(queue)
        while queue:
            cost, town = heapq.heappop(queue)
            if town == target:
                return cost
            if cost > best[town]:
                continue
            for neighbour, edge_cost in self._graph.get(town, []):
                new_cost = cost + edge_cost
                if neighbour not in best or new_cost < best[neighbour]:
                    best[neighbour] = new_cost
                    heapq.heappush(queue, (new_cost, neighbour))
        raise ValueError(f"Town {target} is unreachable")

    def calculate_connecting_cost(self, from_towns: Sequence[str],
                                  to_towns: Sequence[str]) -> int:
        network: set[str] = set(from_towns)
        total_cost = 0
        for target in to_towns:
            if not network:
                network.add(target)
                continue
            total_cost += self._shortest_cost(network, target)
            network.add(target)
        return total_cost
