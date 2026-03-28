"""
드론 성능 프로필
================
드론 유형별 성능 DB + 열화 추적 + 비교.

사용법:
    pp = PerformanceProfile()
    pp.add_profile("d1", drone_type="COMMERCIAL", max_speed=15)
    pp.record_performance("d1", speed=14.2, energy_rate=0.5)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class DroneProfile:
    """드론 성능 프로필"""
    drone_id: str
    drone_type: str
    max_speed_ms: float
    max_altitude_m: float = 120.0
    battery_capacity_wh: float = 80.0
    weight_kg: float = 2.0
    age_hours: float = 0.0


@dataclass
class PerformanceRecord:
    """성능 기록"""
    speed_ms: float
    energy_rate_wh_km: float
    vibration: float = 0.0
    t: float = 0.0


class PerformanceProfile:
    """드론 성능 프로필 관리."""

    def __init__(self) -> None:
        self._profiles: dict[str, DroneProfile] = {}
        self._records: dict[str, list[PerformanceRecord]] = {}

    def add_profile(
        self, drone_id: str, drone_type: str = "COMMERCIAL",
        max_speed: float = 15.0, max_altitude: float = 120.0,
        battery: float = 80.0, weight: float = 2.0,
    ) -> DroneProfile:
        p = DroneProfile(
            drone_id=drone_id, drone_type=drone_type,
            max_speed_ms=max_speed, max_altitude_m=max_altitude,
            battery_capacity_wh=battery, weight_kg=weight,
        )
        self._profiles[drone_id] = p
        self._records[drone_id] = []
        return p

    def record_performance(
        self, drone_id: str, speed: float = 0.0,
        energy_rate: float = 0.0, vibration: float = 0.0, t: float = 0.0,
    ) -> None:
        if drone_id not in self._records:
            self._records[drone_id] = []
        self._records[drone_id].append(PerformanceRecord(
            speed_ms=speed, energy_rate_wh_km=energy_rate,
            vibration=vibration, t=t,
        ))
        if len(self._records[drone_id]) > 500:
            self._records[drone_id] = self._records[drone_id][-500:]

    def degradation(self, drone_id: str) -> float:
        """성능 열화율 (0=완전, 1=완전 열화)"""
        records = self._records.get(drone_id, [])
        profile = self._profiles.get(drone_id)
        if not records or not profile or len(records) < 5:
            return 0.0

        # 최근 속도 대비 최대 속도
        recent_speeds = [r.speed_ms for r in records[-10:] if r.speed_ms > 0]
        if not recent_speeds:
            return 0.0

        avg_speed = np.mean(recent_speeds)
        speed_deg = max(0, 1 - avg_speed / max(profile.max_speed_ms, 1))

        # 진동 트렌드
        recent_vib = [r.vibration for r in records[-10:]]
        vib_deg = min(1.0, np.mean(recent_vib) / 10.0) if recent_vib else 0

        return min(1.0, (speed_deg + vib_deg) / 2)

    def compare(self, drone_a: str, drone_b: str) -> dict[str, Any]:
        """두 드론 비교"""
        pa = self._profiles.get(drone_a)
        pb = self._profiles.get(drone_b)
        if not pa or not pb:
            return {}
        return {
            "speed_ratio": pa.max_speed_ms / max(pb.max_speed_ms, 1),
            "battery_ratio": pa.battery_capacity_wh / max(pb.battery_capacity_wh, 1),
            "weight_ratio": pa.weight_kg / max(pb.weight_kg, 0.1),
            "degradation_a": round(self.degradation(drone_a), 3),
            "degradation_b": round(self.degradation(drone_b), 3),
        }

    def needs_maintenance(self, threshold: float = 0.5) -> list[str]:
        return [did for did in self._profiles if self.degradation(did) >= threshold]

    def by_type(self, drone_type: str) -> list[DroneProfile]:
        return [p for p in self._profiles.values() if p.drone_type == drone_type]

    def summary(self) -> dict[str, Any]:
        return {
            "total_profiles": len(self._profiles),
            "total_records": sum(len(v) for v in self._records.values()),
            "needs_maintenance": len(self.needs_maintenance()),
        }
