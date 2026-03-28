"""
함대 구성 최적화
===============
드론 타입 믹스 최적화 + 투자 계획.

사용법:
    fc = FleetComposer(budget=1000000)
    fc.add_type("DELIVERY", cost=5000, capacity=3, revenue_per_mission=2000)
    plan = fc.optimize()
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DroneType:
    type_name: str
    unit_cost: float
    payload_capacity_kg: float
    revenue_per_mission: float
    missions_per_day: int = 10
    maintenance_monthly: float = 500


class FleetComposer:
    def __init__(self, budget: float = 1000000) -> None:
        self.budget = budget
        self._types: dict[str, DroneType] = {}

    def add_type(self, type_name: str, cost: float = 5000, capacity: float = 3, revenue_per_mission: float = 2000, missions_per_day: int = 10, maintenance: float = 500) -> None:
        self._types[type_name] = DroneType(type_name=type_name, unit_cost=cost, payload_capacity_kg=capacity, revenue_per_mission=revenue_per_mission, missions_per_day=missions_per_day, maintenance_monthly=maintenance)

    def _roi_score(self, dt: DroneType) -> float:
        monthly_revenue = dt.revenue_per_mission * dt.missions_per_day * 30
        monthly_cost = dt.maintenance_monthly + dt.unit_cost / 24  # 24-month depreciation
        return monthly_revenue / max(monthly_cost, 1)

    def optimize(self) -> dict[str, int]:
        """ROI 기반 그리디 할당"""
        sorted_types = sorted(self._types.values(), key=lambda t: -self._roi_score(t))
        allocation: dict[str, int] = {}
        remaining = self.budget

        for dt in sorted_types:
            count = int(remaining / dt.unit_cost)
            if count > 0:
                allocation[dt.type_name] = count
                remaining -= count * dt.unit_cost

        return allocation

    def projected_revenue(self, allocation: dict[str, int]) -> float:
        total = 0
        for type_name, count in allocation.items():
            dt = self._types.get(type_name)
            if dt:
                total += dt.revenue_per_mission * dt.missions_per_day * 30 * count
        return round(total)

    def summary(self) -> dict[str, Any]:
        plan = self.optimize()
        return {
            "types": len(self._types),
            "budget": self.budget,
            "allocation": plan,
            "projected_monthly_revenue": self.projected_revenue(plan),
        }
