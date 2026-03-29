"""Delivery simulation E2E for Phase 172.

Simulates order intake, drone assignment, ETA estimation, and delivery completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any


@dataclass
class DeliveryOrder:
    order_id: str
    destination: tuple[float, float]
    weight_kg: float
    priority: int
    created_min: int


@dataclass
class DroneUnit:
    drone_id: str
    position: tuple[float, float]
    max_payload_kg: float
    speed_mps: float
    busy: bool = False


@dataclass
class DispatchRecord:
    order_id: str
    drone_id: str
    eta_min: float
    distance_m: float


class DeliverySimulation:
    def __init__(self) -> None:
        self._orders: list[DeliveryOrder] = []
        self._drones: dict[str, DroneUnit] = {}
        self._dispatches: list[DispatchRecord] = []
        self._delivered_orders: set[str] = set()

    def register_drone(
        self,
        drone_id: str,
        position: tuple[float, float] = (0.0, 0.0),
        max_payload_kg: float = 3.0,
        speed_mps: float = 12.0,
    ) -> None:
        self._drones[drone_id] = DroneUnit(
            drone_id=drone_id,
            position=(float(position[0]), float(position[1])),
            max_payload_kg=max(0.1, float(max_payload_kg)),
            speed_mps=max(0.1, float(speed_mps)),
        )

    def add_order(
        self,
        order_id: str,
        destination: tuple[float, float],
        weight_kg: float = 1.0,
        priority: int = 5,
        created_min: int = 0,
    ) -> None:
        self._orders.append(
            DeliveryOrder(
                order_id=order_id,
                destination=(float(destination[0]), float(destination[1])),
                weight_kg=max(0.1, float(weight_kg)),
                priority=max(1, min(10, int(priority))),
                created_min=max(0, int(created_min)),
            )
        )

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return sqrt(dx * dx + dy * dy)

    def _candidate_drones(self, order: DeliveryOrder) -> list[DroneUnit]:
        return [
            d for d in self._drones.values() if (not d.busy and d.max_payload_kg >= order.weight_kg)
        ]

    def estimate_eta_min(
        self,
        drone: DroneUnit,
        order: DeliveryOrder,
        congestion: float = 0.2,
        weather_factor: float = 1.0,
    ) -> tuple[float, float]:
        distance_m = self._distance(drone.position, order.destination)
        congestion_penalty = 1.0 + max(0.0, min(1.0, float(congestion))) * 0.6
        weather_penalty = 1.0 / max(0.4, min(1.2, float(weather_factor)))
        effective_speed = drone.speed_mps / (congestion_penalty * weather_penalty)
        eta_min = (distance_m / max(0.1, effective_speed)) / 60.0
        return round(eta_min, 2), round(distance_m, 2)

    def dispatch_next(
        self,
        congestion: float = 0.2,
        weather_factor: float = 1.0,
    ) -> DispatchRecord | None:
        if not self._orders:
            return None

        # High priority first, then older orders.
        self._orders.sort(key=lambda o: (-o.priority, o.created_min))
        order = self._orders[0]
        candidates = self._candidate_drones(order)
        if not candidates:
            return None

        selected = min(candidates, key=lambda d: self._distance(d.position, order.destination))
        eta_min, distance_m = self.estimate_eta_min(
            drone=selected,
            order=order,
            congestion=congestion,
            weather_factor=weather_factor,
        )

        selected.busy = True
        record = DispatchRecord(
            order_id=order.order_id,
            drone_id=selected.drone_id,
            eta_min=eta_min,
            distance_m=distance_m,
        )
        self._dispatches.append(record)
        self._orders.pop(0)
        return record

    def complete_delivery(self, order_id: str) -> bool:
        for r in self._dispatches:
            if r.order_id == order_id:
                self._delivered_orders.add(order_id)
                drone = self._drones.get(r.drone_id)
                if drone:
                    drone.busy = False
                return True
        return False

    def pending_orders(self) -> int:
        return len(self._orders)

    def summary(self) -> dict[str, Any]:
        return {
            "drones": len(self._drones),
            "pending_orders": len(self._orders),
            "dispatches": len(self._dispatches),
            "delivered": len(self._delivered_orders),
            "busy_drones": sum(1 for d in self._drones.values() if d.busy),
        }
