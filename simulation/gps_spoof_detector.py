"""
GPS 스푸핑 탐지
==============
다중 센서 교차 검증 + 위치 이상 탐지 + 경고.

사용법:
    gsd = GPSSpoofDetector()
    gsd.update("d1", gps=(100,200,50), imu=(101,199,50), baro_alt=50)
    alerts = gsd.check("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class SensorReading:
    """센서 읽기"""
    gps: tuple[float, float, float]
    imu: tuple[float, float, float] | None = None
    baro_alt: float | None = None
    t: float = 0.0


@dataclass
class SpoofAlert:
    """스푸핑 경고"""
    drone_id: str
    alert_type: str  # POSITION_JUMP, ALTITUDE_MISMATCH, VELOCITY_IMPOSSIBLE, MULTI_SENSOR_CONFLICT
    severity: str  # LOW, MEDIUM, HIGH
    detail: str
    confidence: float


class GPSSpoofDetector:
    """GPS 스푸핑 탐지."""

    def __init__(
        self, position_jump_threshold: float = 100.0,
        altitude_mismatch_threshold: float = 20.0,
        max_velocity_ms: float = 50.0,
    ) -> None:
        self.position_jump_threshold = position_jump_threshold
        self.altitude_mismatch_threshold = altitude_mismatch_threshold
        self.max_velocity_ms = max_velocity_ms
        self._readings: dict[str, list[SensorReading]] = {}
        self._alerts: list[SpoofAlert] = []

    def update(
        self, drone_id: str,
        gps: tuple[float, float, float],
        imu: tuple[float, float, float] | None = None,
        baro_alt: float | None = None, t: float = 0.0,
    ) -> None:
        if drone_id not in self._readings:
            self._readings[drone_id] = []
        self._readings[drone_id].append(SensorReading(gps=gps, imu=imu, baro_alt=baro_alt, t=t))
        if len(self._readings[drone_id]) > 100:
            self._readings[drone_id] = self._readings[drone_id][-100:]

    def check(self, drone_id: str) -> list[SpoofAlert]:
        readings = self._readings.get(drone_id, [])
        if len(readings) < 2:
            return []

        alerts = []
        curr = readings[-1]
        prev = readings[-2]

        # 1. 위치 점프 검사
        dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(curr.gps, prev.gps)))
        dt = max(curr.t - prev.t, 0.1)
        velocity = dist / dt

        if dist > self.position_jump_threshold:
            alert = SpoofAlert(
                drone_id=drone_id, alert_type="POSITION_JUMP",
                severity="HIGH", detail=f"점프 {dist:.0f}m in {dt:.1f}s",
                confidence=min(1.0, dist / self.position_jump_threshold / 2),
            )
            alerts.append(alert)

        # 2. 불가능한 속도
        if velocity > self.max_velocity_ms:
            alert = SpoofAlert(
                drone_id=drone_id, alert_type="VELOCITY_IMPOSSIBLE",
                severity="HIGH", detail=f"속도 {velocity:.1f} m/s > 한계 {self.max_velocity_ms}",
                confidence=min(1.0, velocity / self.max_velocity_ms / 2),
            )
            alerts.append(alert)

        # 3. 기압고도 불일치
        if curr.baro_alt is not None:
            alt_diff = abs(curr.gps[2] - curr.baro_alt)
            if alt_diff > self.altitude_mismatch_threshold:
                alert = SpoofAlert(
                    drone_id=drone_id, alert_type="ALTITUDE_MISMATCH",
                    severity="MEDIUM",
                    detail=f"GPS alt={curr.gps[2]:.1f}, baro={curr.baro_alt:.1f}, 차이={alt_diff:.1f}m",
                    confidence=min(1.0, alt_diff / self.altitude_mismatch_threshold / 2),
                )
                alerts.append(alert)

        # 4. IMU 교차 검증
        if curr.imu:
            imu_dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(curr.gps, curr.imu)))
            if imu_dist > self.position_jump_threshold * 0.5:
                alert = SpoofAlert(
                    drone_id=drone_id, alert_type="MULTI_SENSOR_CONFLICT",
                    severity="HIGH", detail=f"GPS-IMU 차이 {imu_dist:.1f}m",
                    confidence=min(1.0, imu_dist / self.position_jump_threshold),
                )
                alerts.append(alert)

        self._alerts.extend(alerts)
        return alerts

    def is_trusted(self, drone_id: str) -> bool:
        recent = [a for a in self._alerts[-20:] if a.drone_id == drone_id and a.severity == "HIGH"]
        return len(recent) == 0

    def untrusted_drones(self) -> list[str]:
        return [did for did in self._readings if not self.is_trusted(did)]

    def summary(self) -> dict[str, Any]:
        return {
            "drones_monitored": len(self._readings),
            "total_alerts": len(self._alerts),
            "untrusted": len(self.untrusted_drones()),
            "high_severity": sum(1 for a in self._alerts if a.severity == "HIGH"),
        }
