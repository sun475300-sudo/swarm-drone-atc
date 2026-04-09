"""
충전 최적화
===========
최적 충전 스케줄 + 대기 시간 최소화 + 경로 연계.

사용법:
    co = ChargeOptimizer()
    co.add_station("CS1", (0, 0), capacity=4, queue_size=2)
    plan = co.optimize_charge("d1", (500, 500, 50), battery_pct=15)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ChargePlan:
    """충전 계획"""
    drone_id: str
    station_id: str
    distance_m: float
    estimated_wait_min: float
    charge_time_min: float
    total_time_min: float
    detour_m: float  # 경로 이탈 거리


@dataclass
class StationState:
    """충전소 상태"""
    station_id: str
    position: tuple[float, float]
    capacity: int
    occupied: int = 0
    queue_size: int = 0
    charge_rate_pct_per_min: float = 2.0


class ChargeOptimizer:
    """충전 스케줄 최적화."""

    def __init__(self) -> None:
        self._stations: dict[str, StationState] = {}

    def add_station(
        self, station_id: str, position: tuple[float, float],
        capacity: int = 4, charge_rate: float = 2.0,
    ) -> StationState:
        s = StationState(
            station_id=station_id, position=position,
            capacity=capacity, charge_rate_pct_per_min=charge_rate,
        )
        self._stations[station_id] = s
        return s

    def update_station(self, station_id: str, occupied: int, queue_size: int) -> None:
        s = self._stations.get(station_id)
        if s:
            s.occupied = occupied
            s.queue_size = queue_size

    def optimize_charge(
        self, drone_id: str, position: tuple[float, float, float],
        battery_pct: float = 20.0, target_pct: float = 90.0,
        destination: tuple[float, float] | None = None,
        speed_ms: float = 10.0,
    ) -> ChargePlan | None:
        """최적 충전소 선택"""
        if not self._stations:
            return None

        best_plan: ChargePlan | None = None
        best_total = float("inf")

        for sid, station in self._stations.items():
            # 거리
            dx = position[0] - station.position[0]
            dy = position[1] - station.position[1]
            dist = np.sqrt(dx*dx + dy*dy)

            # 이동 시간
            travel_min = (dist / max(speed_ms, 1)) / 60

            # 대기 시간 추정
            if station.occupied < station.capacity:
                wait_min = 0.0
            else:
                wait_min = station.queue_size * (50 / station.charge_rate_pct_per_min)

            # 충전 시간
            charge_pct = target_pct - battery_pct
            charge_min = max(0, charge_pct / station.charge_rate_pct_per_min)

            # 우회 거리
            detour = 0.0
            if destination:
                direct = np.sqrt(
                    (position[0]-destination[0])**2 + (position[1]-destination[1])**2
                )
                via_station = dist + np.sqrt(
                    (station.position[0]-destination[0])**2 +
                    (station.position[1]-destination[1])**2
                )
                detour = max(0, via_station - direct)

            total = travel_min + wait_min + charge_min + detour / max(speed_ms, 1) / 60

            if total < best_total:
                best_total = total
                best_plan = ChargePlan(
                    drone_id=drone_id, station_id=sid,
                    distance_m=dist, estimated_wait_min=round(wait_min, 1),
                    charge_time_min=round(charge_min, 1),
                    total_time_min=round(total, 1),
                    detour_m=round(detour, 1),
                )

        return best_plan

    def batch_optimize(
        self, drones: dict[str, tuple[tuple[float, float, float], float]],
        target_pct: float = 90.0,
    ) -> dict[str, ChargePlan]:
        """다수 드론 동시 최적화"""
        plans = {}
        # 배터리 낮은 순서로 할당
        sorted_drones = sorted(drones.items(), key=lambda x: x[1][1])
        for did, (pos, batt) in sorted_drones:
            plan = self.optimize_charge(did, pos, batt, target_pct)
            if plan:
                plans[did] = plan
                # 대기열 업데이트 반영
                s = self._stations.get(plan.station_id)
                if s:
                    if s.occupied < s.capacity:
                        s.occupied += 1
                    else:
                        s.queue_size += 1
        return plans

    def summary(self) -> dict[str, Any]:
        total_cap = sum(s.capacity for s in self._stations.values())
        total_occ = sum(s.occupied for s in self._stations.values())
        return {
            "stations": len(self._stations),
            "total_capacity": total_cap,
            "total_occupied": total_occ,
            "utilization": round(total_occ / max(total_cap, 1), 3),
        }
