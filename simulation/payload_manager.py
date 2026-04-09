"""
페이로드 관리
============
화물 무게/부피 + 비행 성능 영향 + 배달 최적화.

사용법:
    pm = PayloadManager()
    pm.register_drone("d1", max_payload_kg=5.0, base_weight_kg=2.0)
    pm.load_cargo("d1", cargo_id="c1", weight_kg=3.0)
    effect = pm.performance_impact("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Cargo:
    """화물"""
    cargo_id: str
    weight_kg: float
    volume_l: float = 0.0
    priority: int = 5
    destination: tuple[float, float] | None = None


@dataclass
class DronePayload:
    """드론 페이로드 상태"""
    drone_id: str
    max_payload_kg: float
    base_weight_kg: float
    cargo: list[Cargo] = field(default_factory=list)


@dataclass
class PerformanceImpact:
    """성능 영향"""
    speed_reduction_pct: float
    endurance_reduction_pct: float
    energy_increase_pct: float
    payload_ratio: float


class PayloadManager:
    """페이로드 관리."""

    def __init__(self) -> None:
        self._drones: dict[str, DronePayload] = {}
        self._delivered: list[Cargo] = []

    def register_drone(self, drone_id: str, max_payload_kg: float = 5.0, base_weight_kg: float = 2.0) -> None:
        self._drones[drone_id] = DronePayload(
            drone_id=drone_id, max_payload_kg=max_payload_kg,
            base_weight_kg=base_weight_kg,
        )

    def load_cargo(self, drone_id: str, cargo_id: str, weight_kg: float, volume_l: float = 0, priority: int = 5, destination: tuple[float, float] | None = None) -> bool:
        d = self._drones.get(drone_id)
        if not d:
            return False
        current = sum(c.weight_kg for c in d.cargo)
        if current + weight_kg > d.max_payload_kg:
            return False
        d.cargo.append(Cargo(cargo_id=cargo_id, weight_kg=weight_kg, volume_l=volume_l, priority=priority, destination=destination))
        return True

    def unload_cargo(self, drone_id: str, cargo_id: str) -> bool:
        d = self._drones.get(drone_id)
        if not d:
            return False
        for i, c in enumerate(d.cargo):
            if c.cargo_id == cargo_id:
                self._delivered.append(d.cargo.pop(i))
                return True
        return False

    def current_weight(self, drone_id: str) -> float:
        d = self._drones.get(drone_id)
        if not d:
            return 0
        return round(d.base_weight_kg + sum(c.weight_kg for c in d.cargo), 2)

    def performance_impact(self, drone_id: str) -> PerformanceImpact:
        d = self._drones.get(drone_id)
        if not d:
            return PerformanceImpact(0, 0, 0, 0)

        cargo_weight = sum(c.weight_kg for c in d.cargo)
        ratio = cargo_weight / max(d.max_payload_kg, 0.1)

        return PerformanceImpact(
            speed_reduction_pct=round(ratio * 15, 1),
            endurance_reduction_pct=round(ratio * 25, 1),
            energy_increase_pct=round(ratio * 30, 1),
            payload_ratio=round(ratio, 3),
        )

    def available_capacity(self, drone_id: str) -> float:
        d = self._drones.get(drone_id)
        if not d:
            return 0
        return round(d.max_payload_kg - sum(c.weight_kg for c in d.cargo), 2)

    def delivery_count(self) -> int:
        return len(self._delivered)

    def summary(self) -> dict[str, Any]:
        return {
            "drones": len(self._drones),
            "total_cargo": sum(len(d.cargo) for d in self._drones.values()),
            "total_delivered": len(self._delivered),
            "avg_utilization": round(
                float(np.mean([
                    sum(c.weight_kg for c in d.cargo) / max(d.max_payload_kg, 0.1)
                    for d in self._drones.values()
                ])) * 100, 1
            ) if self._drones else 0,
        }
