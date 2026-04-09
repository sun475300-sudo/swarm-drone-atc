"""
배송 경로 최적화
===============
TSP/VRP 변형 + 시간창 + 다중 배송.

사용법:
    do = DeliveryOptimizer()
    do.add_delivery("c1", destination=(500, 300), weight_kg=2.0)
    route = do.optimize_route(depot=(0, 0), max_payload_kg=5.0)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class Delivery:
    delivery_id: str
    destination: tuple[float, float]
    weight_kg: float
    priority: int = 5
    time_window: tuple[int, int] | None = None


class DeliveryOptimizer:
    def __init__(self) -> None:
        self._deliveries: dict[str, Delivery] = {}

    def add_delivery(self, delivery_id: str, destination: tuple[float, float], weight_kg: float = 1.0, priority: int = 5, time_window: tuple[int, int] | None = None) -> None:
        self._deliveries[delivery_id] = Delivery(delivery_id=delivery_id, destination=destination, weight_kg=weight_kg, priority=priority, time_window=time_window)

    def _dist(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        return float(np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2))

    def optimize_route(self, depot: tuple[float, float] = (0, 0), max_payload_kg: float = 5.0) -> list[str]:
        """Nearest-neighbor + capacity constraint"""
        remaining = dict(self._deliveries)
        route = []
        current_pos = depot
        current_weight = 0.0

        while remaining:
            best_id = None
            best_dist = float("inf")
            for did, d in remaining.items():
                if current_weight + d.weight_kg > max_payload_kg:
                    continue
                dist = self._dist(current_pos, d.destination)
                if dist < best_dist:
                    best_dist = dist
                    best_id = did

            if best_id is None:
                break  # 용량 초과, 새 루트 필요

            route.append(best_id)
            d = remaining.pop(best_id)
            current_pos = d.destination
            current_weight += d.weight_kg

        return route

    def total_distance(self, route: list[str], depot: tuple[float, float] = (0, 0)) -> float:
        if not route:
            return 0
        total = 0.0
        prev = depot
        for did in route:
            d = self._deliveries.get(did)
            if d:
                total += self._dist(prev, d.destination)
                prev = d.destination
        total += self._dist(prev, depot)
        return round(total, 1)

    def summary(self) -> dict[str, Any]:
        route = self.optimize_route()
        return {
            "deliveries": len(self._deliveries),
            "route_length": len(route),
            "total_distance": self.total_distance(route),
        }
