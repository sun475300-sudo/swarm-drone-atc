"""
충전 인프라 관리
================
충전소 배치 + 대기열 + 에너지 수급 + 최적 충전소 추천.

사용법:
    pg = PowerGrid()
    pg.add_station("CS1", position=(0, 0), capacity=4)
    station = pg.recommend_station("d1", (500, 500, 50), battery_pct=20)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ChargingStation:
    """충전소"""
    station_id: str
    position: tuple[float, float]
    capacity: int = 4  # 동시 충전 대수
    charge_rate_pct_min: float = 2.0  # %/분
    occupied: list[str] = field(default_factory=list)
    queue: list[str] = field(default_factory=list)
    total_charged: int = 0


class PowerGrid:
    """충전 인프라 관리."""

    def __init__(self) -> None:
        self._stations: dict[str, ChargingStation] = {}

    def add_station(
        self,
        station_id: str,
        position: tuple[float, float],
        capacity: int = 4,
        charge_rate: float = 2.0,
    ) -> ChargingStation:
        cs = ChargingStation(
            station_id=station_id, position=position,
            capacity=capacity, charge_rate_pct_min=charge_rate,
        )
        self._stations[station_id] = cs
        return cs

    def recommend_station(
        self,
        drone_id: str,
        position: tuple[float, float, float],
        battery_pct: float = 20.0,
    ) -> str | None:
        """최적 충전소 추천 (거리 + 대기열)"""
        if not self._stations:
            return None

        pos = np.array(position[:2])
        best = None
        best_score = float("inf")

        for sid, cs in self._stations.items():
            dist = float(np.linalg.norm(pos - np.array(cs.position)))
            queue_penalty = len(cs.queue) * 100
            occupied_penalty = len(cs.occupied) * 50
            score = dist + queue_penalty + occupied_penalty

            if score < best_score:
                best_score = score
                best = sid

        return best

    def request_charge(self, drone_id: str, station_id: str) -> bool:
        """충전 요청"""
        cs = self._stations.get(station_id)
        if not cs:
            return False

        if len(cs.occupied) < cs.capacity:
            cs.occupied.append(drone_id)
            return True
        else:
            cs.queue.append(drone_id)
            return True  # 대기열에 추가

    def complete_charge(self, drone_id: str, station_id: str) -> bool:
        """충전 완료"""
        cs = self._stations.get(station_id)
        if not cs:
            return False

        if drone_id in cs.occupied:
            cs.occupied.remove(drone_id)
            cs.total_charged += 1
            # 대기열에서 다음 드론 투입
            if cs.queue:
                next_drone = cs.queue.pop(0)
                cs.occupied.append(next_drone)
            return True
        if drone_id in cs.queue:
            cs.queue.remove(drone_id)
            return True
        return False

    def station_utilization(self, station_id: str) -> float:
        cs = self._stations.get(station_id)
        if not cs:
            return 0.0
        return len(cs.occupied) / max(cs.capacity, 1)

    def total_capacity(self) -> int:
        return sum(cs.capacity for cs in self._stations.values())

    def total_occupied(self) -> int:
        return sum(len(cs.occupied) for cs in self._stations.values())

    def charge_time_estimate(
        self, station_id: str, current_pct: float, target_pct: float = 90.0
    ) -> float:
        """충전 소요 시간 추정 (분)"""
        cs = self._stations.get(station_id)
        if not cs:
            return -1.0
        needed = target_pct - current_pct
        if needed <= 0:
            return 0.0
        wait = len(cs.queue) * (50 / cs.charge_rate_pct_min)  # 대기 시간
        charge = needed / cs.charge_rate_pct_min
        return wait + charge

    def summary(self) -> dict[str, Any]:
        return {
            "total_stations": len(self._stations),
            "total_capacity": self.total_capacity(),
            "total_occupied": self.total_occupied(),
            "total_queued": sum(len(cs.queue) for cs in self._stations.values()),
            "total_charged": sum(cs.total_charged for cs in self._stations.values()),
        }
