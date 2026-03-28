"""
배터리 수명 예측기
==================
과거 소모 패턴 기반 잔여 비행시간을 정밀 예측.
풍향, 속도, 고도를 반영한 다변수 소모 모델.

사용법:
    predictor = BatteryPredictor()
    predictor.record(t=10, battery_pct=85, altitude=60, speed=12, wind_speed=5)
    eta = predictor.predict_remaining_time()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class BatterySnapshot:
    """배터리 상태 스냅샷"""
    t: float
    battery_pct: float
    altitude: float = 60.0
    speed: float = 10.0
    wind_speed: float = 0.0
    is_climbing: bool = False


class BatteryPredictor:
    """
    다변수 배터리 수명 예측기.

    소모 이력 기반 선형 회귀 + 환경 보정 계수.
    """

    def __init__(
        self,
        critical_pct: float = 10.0,
        rtl_pct: float = 20.0,
        max_history: int = 300,
    ) -> None:
        self.critical_pct = critical_pct
        self.rtl_pct = rtl_pct
        self.max_history = max_history

        self._snapshots: dict[str, list[BatterySnapshot]] = {}  # drone_id -> snapshots

    def record(
        self,
        drone_id: str,
        t: float,
        battery_pct: float,
        altitude: float = 60.0,
        speed: float = 10.0,
        wind_speed: float = 0.0,
        is_climbing: bool = False,
    ) -> None:
        """배터리 상태 기록"""
        if drone_id not in self._snapshots:
            self._snapshots[drone_id] = []

        self._snapshots[drone_id].append(BatterySnapshot(
            t=t, battery_pct=battery_pct,
            altitude=altitude, speed=speed,
            wind_speed=wind_speed, is_climbing=is_climbing,
        ))

        if len(self._snapshots[drone_id]) > self.max_history:
            self._snapshots[drone_id] = self._snapshots[drone_id][-self.max_history:]

    def predict_remaining_time(self, drone_id: str) -> float:
        """
        잔여 비행시간 예측 (초).

        배터리가 critical_pct까지 떨어지는 데 걸리는 시간.
        데이터 부족 시 -1 반환.
        """
        snaps = self._snapshots.get(drone_id, [])
        if len(snaps) < 2:
            return -1.0

        times = np.array([s.t for s in snaps])
        bats = np.array([s.battery_pct for s in snaps])

        # 선형 회귀로 소모율 계산
        dt = times[-1] - times[0]
        if dt < 0.1:
            return -1.0

        # 최근 데이터에 가중치
        weights = np.linspace(0.5, 1.0, len(times))
        coeffs = np.polyfit(times - times[0], bats, 1, w=weights)
        drain_rate = coeffs[0]  # %/s (음수)

        if drain_rate >= 0:
            return float("inf")  # 배터리 충전 중

        current_pct = snaps[-1].battery_pct
        remaining_pct = current_pct - self.critical_pct
        if remaining_pct <= 0:
            return 0.0

        # 환경 보정 계수
        correction = self._environment_correction(snaps[-1])
        adjusted_rate = drain_rate * correction

        return remaining_pct / abs(adjusted_rate)

    def predict_range_km(self, drone_id: str) -> float:
        """잔여 비행거리 예측 (km)"""
        remaining_s = self.predict_remaining_time(drone_id)
        if remaining_s < 0:
            return -1.0

        snaps = self._snapshots.get(drone_id, [])
        if not snaps:
            return -1.0

        avg_speed = float(np.mean([s.speed for s in snaps[-10:]]))
        return remaining_s * avg_speed / 1000.0

    def can_reach(
        self, drone_id: str, distance_m: float, speed: float = 10.0
    ) -> bool:
        """목표 지점 도달 가능 여부"""
        remaining_s = self.predict_remaining_time(drone_id)
        if remaining_s < 0:
            return False

        required_time = distance_m / max(speed, 0.1)
        return bool(remaining_s > required_time * 1.2)  # 20% 여유

    def should_rtl(self, drone_id: str) -> bool:
        """RTL 필요 여부"""
        snaps = self._snapshots.get(drone_id, [])
        if not snaps:
            return False

        current = snaps[-1].battery_pct
        if current <= self.rtl_pct:
            return True

        # 예측 기반: 60초 후 critical 이하로 떨어지면 RTL
        remaining = self.predict_remaining_time(drone_id)
        if 0 < remaining < 60:
            return True

        return False

    def drain_rate(self, drone_id: str) -> float:
        """현재 소모율 (%/s, 양수=소모)"""
        snaps = self._snapshots.get(drone_id, [])
        if len(snaps) < 2:
            return 0.0

        recent = snaps[-min(10, len(snaps)):]
        dt = recent[-1].t - recent[0].t
        if dt < 0.1:
            return 0.0

        dpct = recent[0].battery_pct - recent[-1].battery_pct
        return dpct / dt

    def _environment_correction(self, snap: BatterySnapshot) -> float:
        """환경 보정 계수 (1.0 = 기본, >1.0 = 소모 가속)"""
        correction = 1.0

        # 풍속 보정 (강풍일수록 소모 증가)
        if snap.wind_speed > 10:
            correction *= 1.0 + (snap.wind_speed - 10) * 0.03

        # 고도 보정 (고도 높을수록 소모 미세 증가)
        if snap.altitude > 80:
            correction *= 1.0 + (snap.altitude - 80) * 0.002

        # 속도 보정 (고속일수록 소모 증가)
        if snap.speed > 15:
            correction *= 1.0 + (snap.speed - 15) * 0.02

        # 상승 중 보정
        if snap.is_climbing:
            correction *= 1.3

        return correction

    def summary(self, drone_id: str) -> dict[str, Any]:
        """드론 배터리 예측 요약"""
        snaps = self._snapshots.get(drone_id, [])
        if not snaps:
            return {"drone_id": drone_id, "data_points": 0}

        return {
            "drone_id": drone_id,
            "data_points": len(snaps),
            "current_pct": snaps[-1].battery_pct,
            "drain_rate_pct_s": self.drain_rate(drone_id),
            "remaining_time_s": self.predict_remaining_time(drone_id),
            "remaining_range_km": self.predict_range_km(drone_id),
            "should_rtl": self.should_rtl(drone_id),
        }

    def all_drones_summary(self) -> list[dict[str, Any]]:
        """전체 드론 배터리 요약"""
        return [self.summary(did) for did in self._snapshots]

    def clear(self) -> None:
        self._snapshots.clear()
