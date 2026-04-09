"""
드론 수명 주기
=============
구매→운용→정비→퇴역 + TCO 분석.

사용법:
    lc = DroneLifecycle()
    lc.register("d1", purchase_cost=5000)
    lc.record_operation("d1", hours=10, maintenance_cost=100)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class LifecycleRecord:
    drone_id: str
    purchase_cost: float
    total_hours: float = 0
    total_maintenance: float = 0
    total_energy_cost: float = 0
    status: str = "ACTIVE"  # ACTIVE, MAINTENANCE, RETIRED
    max_hours: float = 2000


class DroneLifecycle:
    def __init__(self) -> None:
        self._drones: dict[str, LifecycleRecord] = {}

    def register(self, drone_id: str, purchase_cost: float = 5000, max_hours: float = 2000) -> None:
        self._drones[drone_id] = LifecycleRecord(drone_id=drone_id, purchase_cost=purchase_cost, max_hours=max_hours)

    def record_operation(self, drone_id: str, hours: float = 0, maintenance_cost: float = 0, energy_cost: float = 0) -> None:
        d = self._drones.get(drone_id)
        if not d:
            return
        d.total_hours += hours
        d.total_maintenance += maintenance_cost
        d.total_energy_cost += energy_cost
        if d.total_hours >= d.max_hours:
            d.status = "RETIRED"

    def tco(self, drone_id: str) -> float:
        d = self._drones.get(drone_id)
        if not d:
            return 0
        return round(d.purchase_cost + d.total_maintenance + d.total_energy_cost, 1)

    def cost_per_hour(self, drone_id: str) -> float:
        d = self._drones.get(drone_id)
        if not d or d.total_hours <= 0:
            return 0
        return round(self.tco(drone_id) / d.total_hours, 1)

    def retire(self, drone_id: str) -> None:
        d = self._drones.get(drone_id)
        if d:
            d.status = "RETIRED"

    def active_count(self) -> int:
        return sum(1 for d in self._drones.values() if d.status == "ACTIVE")

    def summary(self) -> dict[str, Any]:
        return {
            "total": len(self._drones),
            "active": self.active_count(),
            "retired": sum(1 for d in self._drones.values() if d.status == "RETIRED"),
            "avg_tco": round(float(np.mean([self.tco(did) for did in self._drones])), 1) if self._drones else 0,
        }
