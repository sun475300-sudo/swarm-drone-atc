"""
스케줄 최적화
============
일별/주별 임무 스케줄 + 자원 최적 배분.

사용법:
    so = ScheduleOptimizer()
    so.add_mission("m1", duration_min=30, earliest=8, latest=18, drones_needed=2)
    schedule = so.optimize()
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class MissionSlot:
    mission_id: str
    duration_min: float
    earliest_hour: int = 6
    latest_hour: int = 22
    drones_needed: int = 1
    assigned_hour: int | None = None


class ScheduleOptimizer:
    def __init__(self, available_drones: int = 50) -> None:
        self.available_drones = available_drones
        self._missions: dict[str, MissionSlot] = {}

    def add_mission(self, mission_id: str, duration_min: float = 30, earliest: int = 6, latest: int = 22, drones_needed: int = 1) -> None:
        self._missions[mission_id] = MissionSlot(mission_id=mission_id, duration_min=duration_min, earliest_hour=earliest, latest_hour=latest, drones_needed=drones_needed)

    def optimize(self) -> list[dict[str, Any]]:
        """그리디 스케줄링"""
        hourly_load = [0] * 24
        schedule = []
        sorted_missions = sorted(self._missions.values(), key=lambda m: m.latest_hour - m.earliest_hour)

        for m in sorted_missions:
            best_hour = None
            best_load = float("inf")
            for h in range(m.earliest_hour, m.latest_hour + 1):
                if hourly_load[h] + m.drones_needed <= self.available_drones:
                    if hourly_load[h] < best_load:
                        best_load = hourly_load[h]
                        best_hour = h

            if best_hour is not None:
                m.assigned_hour = best_hour
                blocks = max(1, int(np.ceil(m.duration_min / 60)))
                for b in range(blocks):
                    if best_hour + b < 24:
                        hourly_load[best_hour + b] += m.drones_needed
                schedule.append({"mission": m.mission_id, "hour": best_hour, "drones": m.drones_needed})

        return schedule

    def utilization_by_hour(self) -> list[float]:
        self.optimize()
        hourly = [0] * 24
        for m in self._missions.values():
            if m.assigned_hour is not None:
                blocks = max(1, int(np.ceil(m.duration_min / 60)))
                for b in range(blocks):
                    h = m.assigned_hour + b
                    if h < 24:
                        hourly[h] += m.drones_needed
        return [round(h / max(self.available_drones, 1) * 100, 1) for h in hourly]

    def summary(self) -> dict[str, Any]:
        schedule = self.optimize()
        return {
            "missions": len(self._missions),
            "scheduled": len(schedule),
            "peak_utilization": max(self.utilization_by_hour()) if self._missions else 0,
        }
