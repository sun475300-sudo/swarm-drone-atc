"""
센서 퓨전
=========
다중 센서 데이터 융합 + 칼만 필터 + 신뢰도.

사용법:
    sf = SensorFusion()
    sf.add_measurement("d1", "GPS", position=(500, 500, 50), accuracy=2.0)
    sf.add_measurement("d1", "RADAR", position=(501, 499, 50), accuracy=5.0)
    fused = sf.fuse("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class SensorMeasurement:
    """센서 측정"""
    sensor_type: str
    position: tuple[float, float, float]
    accuracy_m: float  # 표준편차 (m)
    t: float = 0.0
    confidence: float = 1.0


@dataclass
class FusedState:
    """융합된 상태"""
    drone_id: str
    position: tuple[float, float, float]
    uncertainty_m: float
    sources: int
    confidence: float
    t: float = 0.0


class SensorFusion:
    """다중 센서 데이터 융합."""

    def __init__(self, max_age_s: float = 5.0) -> None:
        self._measurements: dict[str, dict[str, SensorMeasurement]] = {}
        self._max_age = max_age_s
        self._fused: dict[str, FusedState] = {}

    def add_measurement(
        self,
        drone_id: str,
        sensor_type: str,
        position: tuple[float, float, float],
        accuracy: float = 2.0,
        t: float = 0.0,
        confidence: float = 1.0,
    ) -> None:
        if drone_id not in self._measurements:
            self._measurements[drone_id] = {}
        self._measurements[drone_id][sensor_type] = SensorMeasurement(
            sensor_type=sensor_type,
            position=position,
            accuracy_m=accuracy,
            t=t,
            confidence=confidence,
        )

    def fuse(self, drone_id: str, t: float = 0.0) -> FusedState | None:
        """가중 평균 융합 (역분산 가중)"""
        measurements = self._measurements.get(drone_id, {})
        if not measurements:
            return None

        # 오래된 측정 필터링
        valid = {
            k: m for k, m in measurements.items()
            if t == 0 or abs(t - m.t) <= self._max_age
        }
        if not valid:
            return None

        # 역분산 가중 평균
        total_weight = 0.0
        weighted_pos = np.zeros(3)

        for m in valid.values():
            weight = m.confidence / max(m.accuracy_m * m.accuracy_m, 0.01)
            weighted_pos += weight * np.array(m.position)
            total_weight += weight

        if total_weight < 1e-9:
            return None

        fused_pos = tuple(weighted_pos / total_weight)
        # 융합 불확실성 (역분산 합의 역수의 제곱근)
        uncertainty = 1.0 / np.sqrt(total_weight)
        # 전체 신뢰도
        confidence = min(1.0, sum(m.confidence for m in valid.values()) / len(valid))

        state = FusedState(
            drone_id=drone_id,
            position=fused_pos,
            uncertainty_m=float(uncertainty),
            sources=len(valid),
            confidence=confidence,
            t=t,
        )
        self._fused[drone_id] = state
        return state

    def fuse_all(self, t: float = 0.0) -> dict[str, FusedState]:
        """모든 드론 융합"""
        result = {}
        for drone_id in self._measurements:
            state = self.fuse(drone_id, t)
            if state:
                result[drone_id] = state
        return result

    def get_fused(self, drone_id: str) -> FusedState | None:
        return self._fused.get(drone_id)

    def sensor_health(self, drone_id: str) -> dict[str, float]:
        """센서별 신뢰도"""
        measurements = self._measurements.get(drone_id, {})
        return {k: m.confidence for k, m in measurements.items()}

    def degraded_sensors(self, threshold: float = 0.5) -> list[tuple[str, str]]:
        """신뢰도 낮은 센서 목록"""
        result = []
        for drone_id, sensors in self._measurements.items():
            for sensor_type, m in sensors.items():
                if m.confidence < threshold:
                    result.append((drone_id, sensor_type))
        return result

    def summary(self) -> dict[str, Any]:
        total_sensors = sum(len(s) for s in self._measurements.values())
        return {
            "tracked_drones": len(self._measurements),
            "total_sensors": total_sensors,
            "fused_states": len(self._fused),
            "degraded_sensors": len(self.degraded_sensors()),
        }
