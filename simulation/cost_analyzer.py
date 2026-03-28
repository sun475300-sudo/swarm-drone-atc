"""
비용 분석 엔진
=============
임무별 운영 비용(에너지+정비+인프라) + ROI 분석.

사용법:
    ca = CostAnalyzer(energy_cost_per_wh=0.15)
    ca.record_mission("m1", energy_wh=50, distance_m=5000, revenue=10000)
    roi = ca.mission_roi("m1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class MissionCost:
    """임무 비용"""
    mission_id: str
    energy_wh: float
    distance_m: float
    flight_time_s: float = 0.0
    revenue: float = 0.0
    maintenance_cost: float = 0.0


class CostAnalyzer:
    """비용 분석."""

    def __init__(
        self, energy_cost_per_wh: float = 0.15,
        maintenance_per_hour: float = 500.0,
        infrastructure_per_flight: float = 100.0,
    ) -> None:
        self.energy_cost_per_wh = energy_cost_per_wh
        self.maintenance_per_hour = maintenance_per_hour
        self.infrastructure_per_flight = infrastructure_per_flight
        self._missions: dict[str, MissionCost] = {}

    def record_mission(
        self, mission_id: str, energy_wh: float = 0,
        distance_m: float = 0, flight_time_s: float = 0,
        revenue: float = 0, maintenance_cost: float = 0,
    ) -> None:
        self._missions[mission_id] = MissionCost(
            mission_id=mission_id, energy_wh=energy_wh,
            distance_m=distance_m, flight_time_s=flight_time_s,
            revenue=revenue, maintenance_cost=maintenance_cost,
        )

    def total_cost(self, mission_id: str) -> float:
        m = self._missions.get(mission_id)
        if not m:
            return 0.0
        energy = m.energy_wh * self.energy_cost_per_wh
        maintenance = m.maintenance_cost or (m.flight_time_s / 3600 * self.maintenance_per_hour)
        infra = self.infrastructure_per_flight
        return round(energy + maintenance + infra, 1)

    def cost_per_km(self, mission_id: str) -> float:
        m = self._missions.get(mission_id)
        if not m or m.distance_m <= 0:
            return 0.0
        return round(self.total_cost(mission_id) / (m.distance_m / 1000), 1)

    def mission_roi(self, mission_id: str) -> float:
        """투자수익률 (%)"""
        m = self._missions.get(mission_id)
        if not m:
            return 0.0
        cost = self.total_cost(mission_id)
        if cost <= 0:
            return 0.0
        return round((m.revenue - cost) / cost * 100, 1)

    def profitable_missions(self) -> list[str]:
        return [mid for mid in self._missions if self.mission_roi(mid) > 0]

    def fleet_roi(self) -> float:
        total_revenue = sum(m.revenue for m in self._missions.values())
        total_cost = sum(self.total_cost(mid) for mid in self._missions)
        if total_cost <= 0:
            return 0.0
        return round((total_revenue - total_cost) / total_cost * 100, 1)

    def cost_breakdown(self) -> dict[str, float]:
        energy = sum(m.energy_wh * self.energy_cost_per_wh for m in self._missions.values())
        maintenance = sum(
            m.maintenance_cost or (m.flight_time_s / 3600 * self.maintenance_per_hour)
            for m in self._missions.values()
        )
        infra = len(self._missions) * self.infrastructure_per_flight
        return {
            "energy": round(energy, 1),
            "maintenance": round(maintenance, 1),
            "infrastructure": round(infra, 1),
            "total": round(energy + maintenance + infra, 1),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "missions": len(self._missions),
            "fleet_roi": self.fleet_roi(),
            "profitable_count": len(self.profitable_missions()),
            "cost_breakdown": self.cost_breakdown(),
        }
