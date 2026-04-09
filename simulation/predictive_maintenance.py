"""
예측 유지보수 스케줄러
====================
비행시간/진동/사이클 기반 잔여수명 + 정비 일정.

사용법:
    pm = PredictiveMaintenance()
    pm.register_drone("d1", max_hours=500)
    pm.update_usage("d1", hours=10, cycles=5, vibration=2.5)
    schedule = pm.get_schedule("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class DroneUsage:
    """드론 사용 이력"""
    drone_id: str
    max_hours: float = 500.0
    max_cycles: int = 2000
    total_hours: float = 0.0
    total_cycles: int = 0
    vibration_history: list[float] = field(default_factory=list)
    last_maintenance_hours: float = 0.0
    maintenance_interval: float = 100.0


@dataclass
class MaintenanceSchedule:
    """정비 일정"""
    drone_id: str
    remaining_hours: float
    remaining_cycles: int
    health_score: float  # 0~100
    urgency: str  # NORMAL, SOON, URGENT, OVERDUE
    next_maintenance_in: float  # hours until next


class PredictiveMaintenance:
    """예측 유지보수."""

    def __init__(self) -> None:
        self._drones: dict[str, DroneUsage] = {}

    def register_drone(
        self, drone_id: str, max_hours: float = 500.0,
        max_cycles: int = 2000, maintenance_interval: float = 100.0,
    ) -> None:
        self._drones[drone_id] = DroneUsage(
            drone_id=drone_id, max_hours=max_hours,
            max_cycles=max_cycles, maintenance_interval=maintenance_interval,
        )

    def update_usage(
        self, drone_id: str, hours: float = 0.0,
        cycles: int = 0, vibration: float = 0.0,
    ) -> None:
        d = self._drones.get(drone_id)
        if not d:
            return
        d.total_hours += hours
        d.total_cycles += cycles
        d.vibration_history.append(vibration)
        if len(d.vibration_history) > 200:
            d.vibration_history = d.vibration_history[-200:]

    def record_maintenance(self, drone_id: str) -> None:
        d = self._drones.get(drone_id)
        if d:
            d.last_maintenance_hours = d.total_hours

    def _health_score(self, d: DroneUsage) -> float:
        hour_ratio = d.total_hours / max(d.max_hours, 1)
        cycle_ratio = d.total_cycles / max(d.max_cycles, 1)

        vib_score = 1.0
        if d.vibration_history:
            avg_vib = np.mean(d.vibration_history[-20:])
            vib_score = max(0, 1 - avg_vib / 10.0)

        usage_score = 1 - max(hour_ratio, cycle_ratio)
        return max(0, min(100, (usage_score * 0.6 + vib_score * 0.4) * 100))

    def get_schedule(self, drone_id: str) -> MaintenanceSchedule | None:
        d = self._drones.get(drone_id)
        if not d:
            return None

        remaining_hours = max(0, d.max_hours - d.total_hours)
        remaining_cycles = max(0, d.max_cycles - d.total_cycles)
        health = self._health_score(d)

        hours_since = d.total_hours - d.last_maintenance_hours
        next_in = max(0, d.maintenance_interval - hours_since)

        if next_in <= 0 or health < 20:
            urgency = "OVERDUE"
        elif next_in <= 10 or health < 40:
            urgency = "URGENT"
        elif next_in <= 30 or health < 60:
            urgency = "SOON"
        else:
            urgency = "NORMAL"

        return MaintenanceSchedule(
            drone_id=drone_id,
            remaining_hours=round(remaining_hours, 1),
            remaining_cycles=remaining_cycles,
            health_score=round(health, 1),
            urgency=urgency,
            next_maintenance_in=round(next_in, 1),
        )

    def overdue_drones(self) -> list[str]:
        result = []
        for did in self._drones:
            sched = self.get_schedule(did)
            if sched and sched.urgency in ("OVERDUE", "URGENT"):
                result.append(did)
        return result

    def fleet_health(self) -> float:
        if not self._drones:
            return 100.0
        scores = [self._health_score(d) for d in self._drones.values()]
        return round(float(np.mean(scores)), 1)

    def summary(self) -> dict[str, Any]:
        return {
            "total_drones": len(self._drones),
            "fleet_health": self.fleet_health(),
            "overdue_count": len(self.overdue_drones()),
        }
