"""
함대 최적화
==========
드론 타입별 배치 최적화 + 교대 스케줄 + ROI 분석.
임무 수요에 맞는 최적 함대 구성 추천.

사용법:
    opt = FleetOptimizer()
    opt.add_drone_type("delivery", cost=500, range_km=10, payload_kg=5)
    opt.set_demand(deliveries_per_hour=20)
    result = opt.optimize()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class DroneType:
    """드론 타입 정의"""
    name: str
    cost_usd: float = 1000.0
    range_km: float = 10.0
    payload_kg: float = 5.0
    endurance_min: float = 30.0
    charge_time_min: float = 45.0
    speed_ms: float = 10.0
    maintenance_interval_hours: float = 50.0


@dataclass
class FleetComposition:
    """함대 구성"""
    types: dict[str, int]  # type_name -> count
    total_count: int = 0
    total_cost: float = 0.0
    utilization: float = 0.0
    missions_per_hour: float = 0.0
    roi_months: float = 0.0


@dataclass
class ShiftSchedule:
    """교대 스케줄"""
    shift_name: str
    start_hour: float
    end_hour: float
    active_drones: int
    missions_capacity: float


class FleetOptimizer:
    """
    함대 최적화기.

    드론 타입별 배치 + 교대 + ROI.
    """

    def __init__(
        self,
        revenue_per_mission: float = 5.0,
        operating_cost_per_hour: float = 2.0,
    ) -> None:
        self._types: dict[str, DroneType] = {}
        self._demand_per_hour: float = 10.0
        self._revenue = revenue_per_mission
        self._op_cost = operating_cost_per_hour

    def add_drone_type(self, name: str, **kwargs: Any) -> DroneType:
        dt = DroneType(name=name, **kwargs)
        self._types[name] = dt
        return dt

    def set_demand(self, missions_per_hour: float) -> None:
        self._demand_per_hour = missions_per_hour

    def optimize(self) -> FleetComposition:
        """그리디 최적화: 수요 충족 최소 비용 함대"""
        if not self._types:
            return FleetComposition(types={})

        composition: dict[str, int] = {}
        total_capacity = 0.0

        # 효율 순 정렬 (missions/hour per cost)
        sorted_types = sorted(
            self._types.values(),
            key=lambda t: self._missions_per_hour(t) / max(t.cost_usd, 1),
            reverse=True,
        )

        for dt in sorted_types:
            if total_capacity >= self._demand_per_hour:
                break
            mph = self._missions_per_hour(dt)
            needed = int(np.ceil(
                (self._demand_per_hour - total_capacity) / max(mph, 0.01)
            ))
            needed = max(1, needed)
            composition[dt.name] = needed
            total_capacity += needed * mph

        total_count = sum(composition.values())
        total_cost = sum(
            composition.get(name, 0) * self._types[name].cost_usd
            for name in composition
        )

        utilization = min(1.0, self._demand_per_hour / max(total_capacity, 0.01))

        # ROI: 투자 회수 기간 (월)
        monthly_revenue = self._demand_per_hour * self._revenue * 720  # 30일*24시간
        monthly_cost = total_count * self._op_cost * 720
        monthly_profit = monthly_revenue - monthly_cost
        roi = total_cost / max(monthly_profit, 1.0) if monthly_profit > 0 else float("inf")

        return FleetComposition(
            types=composition,
            total_count=total_count,
            total_cost=total_cost,
            utilization=utilization,
            missions_per_hour=total_capacity,
            roi_months=roi,
        )

    def generate_shifts(
        self, total_drones: int, shifts: int = 3
    ) -> list[ShiftSchedule]:
        """교대 스케줄 생성"""
        hours_per_shift = 24.0 / shifts
        schedules = []
        for i in range(shifts):
            start = i * hours_per_shift
            end = start + hours_per_shift
            # 야간은 드론 수 감소
            is_night = start >= 22 or end <= 6
            active = max(1, int(total_drones * (0.5 if is_night else 1.0)))
            cap = active * 2.0  # 평균 드론당 2 missions/hour

            schedules.append(ShiftSchedule(
                shift_name=f"Shift_{i+1}",
                start_hour=start,
                end_hour=end,
                active_drones=active,
                missions_capacity=cap,
            ))

        return schedules

    def _missions_per_hour(self, dt: DroneType) -> float:
        """드론 1대의 시간당 임무 수"""
        # 비행 시간 + 충전 시간 = 사이클
        cycle_min = dt.endurance_min + dt.charge_time_min
        cycles_per_hour = 60.0 / cycle_min
        # 1 사이클 = 1 임무 (편도)
        return cycles_per_hour

    def cost_breakdown(self, composition: FleetComposition) -> dict[str, Any]:
        """비용 분석"""
        acquisition = composition.total_cost
        monthly_op = composition.total_count * self._op_cost * 720
        monthly_rev = composition.missions_per_hour * self._revenue * 720
        return {
            "acquisition_cost": acquisition,
            "monthly_operating_cost": round(monthly_op, 2),
            "monthly_revenue": round(monthly_rev, 2),
            "monthly_profit": round(monthly_rev - monthly_op, 2),
            "roi_months": round(composition.roi_months, 1),
        }

    def summary(self) -> dict[str, Any]:
        comp = self.optimize()
        return {
            "drone_types": len(self._types),
            "demand_per_hour": self._demand_per_hour,
            "optimal_fleet": comp.types,
            "total_drones": comp.total_count,
            "total_cost": comp.total_cost,
            "utilization": round(comp.utilization, 3),
        }
