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
    reservation_id: str | None = None


class DeliverySimulation:
    def __init__(self) -> None:
        self._orders: list[DeliveryOrder] = []
        self._drones: dict[str, DroneUnit] = {}
        self._dispatches: list[DispatchRecord] = []
        self._delivered_orders: set[str] = set()
        self._order_reservations: dict[str, str] = {}
        self._airspace: Any | None = None
        self._default_altitude_band: tuple[float, float] = (30.0, 90.0)
        self._slot_policy = {
            "congestion_alt_step": 12.0,
            "bad_weather_alt_step": 18.0,
            "weather_threshold": 0.75,
            "congestion_threshold": 0.7,
        }

    def set_airspace_reservation(
        self,
        airspace: Any,
        altitude_band: tuple[float, float] = (30.0, 90.0),
    ) -> None:
        self._airspace = airspace
        self._default_altitude_band = (
            float(altitude_band[0]),
            max(float(altitude_band[0]) + 1.0, float(altitude_band[1])),
        )

    def set_slot_policy(
        self,
        congestion_alt_step: float = 12.0,
        bad_weather_alt_step: float = 18.0,
        weather_threshold: float = 0.75,
        congestion_threshold: float = 0.7,
    ) -> None:
        self._slot_policy = {
            "congestion_alt_step": max(0.0, float(congestion_alt_step)),
            "bad_weather_alt_step": max(0.0, float(bad_weather_alt_step)),
            "weather_threshold": max(0.1, min(1.2, float(weather_threshold))),
            "congestion_threshold": max(0.0, min(1.0, float(congestion_threshold))),
        }

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

    def _sector_from_position(self, position: tuple[float, float]) -> tuple[int, int]:
        if self._airspace is None:
            return (0, 0)
        grid = float(getattr(self._airspace, "_grid_size", 100.0))
        x = int(position[0] // max(1.0, grid))
        y = int(position[1] // max(1.0, grid))
        return (x, y)

    def _reserve_slot(
        self,
        order: DeliveryOrder,
        selected: DroneUnit,
        eta_min: float,
        congestion: float,
        weather_factor: float,
    ) -> str | None:
        if self._airspace is None:
            return "NO_AIRSPACE"
        start_min = float(order.created_min)
        end_min = start_min + max(1.0, float(eta_min))
        altitude_band = self._compute_altitude_band(congestion=congestion, weather_factor=weather_factor)
        reserve_priority = self._compute_reservation_priority(
            order=order,
            congestion=congestion,
            weather_factor=weather_factor,
        )
        return self._airspace.reserve(
            drone_id=selected.drone_id,
            sector=self._sector_from_position(order.destination),
            t_start=start_min,
            t_end=end_min,
            altitude_band=altitude_band,
            priority=reserve_priority,
        )

    def _compute_altitude_band(
        self,
        congestion: float,
        weather_factor: float,
    ) -> tuple[float, float]:
        low, high = self._default_altitude_band
        congestion_norm = max(0.0, min(1.0, float(congestion)))
        shift = congestion_norm * float(self._slot_policy["congestion_alt_step"])
        if float(weather_factor) < float(self._slot_policy["weather_threshold"]):
            shift += float(self._slot_policy["bad_weather_alt_step"])
        next_low = low + shift
        next_high = high + shift
        return (round(next_low, 2), round(max(next_low + 1.0, next_high), 2))

    def _compute_reservation_priority(
        self,
        order: DeliveryOrder,
        congestion: float,
        weather_factor: float,
    ) -> int:
        p = max(1, 11 - int(order.priority))
        if float(congestion) >= float(self._slot_policy["congestion_threshold"]):
            p -= 1
        if float(weather_factor) < float(self._slot_policy["weather_threshold"]):
            p -= 1
        return max(1, p)

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
        reservation_id = self._reserve_slot(
            order=order,
            selected=selected,
            eta_min=eta_min,
            congestion=congestion,
            weather_factor=weather_factor,
        )
        if reservation_id is None:
            return None

        selected.busy = True
        record = DispatchRecord(
            order_id=order.order_id,
            drone_id=selected.drone_id,
            eta_min=eta_min,
            distance_m=distance_m,
            reservation_id=None if reservation_id == "NO_AIRSPACE" else reservation_id,
        )
        if record.reservation_id is not None:
            self._order_reservations[order.order_id] = record.reservation_id
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
                reservation_id = self._order_reservations.pop(order_id, None)
                if reservation_id and self._airspace is not None:
                    self._airspace.cancel(reservation_id)
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
            "reserved_slots": len(self._order_reservations),
            "slot_policy": dict(self._slot_policy),
        }
