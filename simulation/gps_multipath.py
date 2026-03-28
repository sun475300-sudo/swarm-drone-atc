"""
GPS 다중경로 모델
================
도심 반사 + 정확도 변동 + HDOP 시뮬레이션.

사용법:
    gm = GPSMultipath(seed=42)
    gm.add_reflector((100, 100), height=80)
    measured = gm.measure((150, 120, 50), true_pos=(150, 120, 50))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Reflector:
    """반사체 (건물)"""
    position: tuple[float, float]
    height: float
    reflection_coeff: float = 0.5


@dataclass
class GPSMeasurement:
    """GPS 측정 결과"""
    measured_pos: tuple[float, float, float]
    true_pos: tuple[float, float, float]
    error_m: float
    hdop: float
    multipath_affected: bool


class GPSMultipath:
    """GPS 다중경로 모델."""

    def __init__(self, base_accuracy: float = 2.0, seed: int = 42) -> None:
        self.base_accuracy = base_accuracy
        self._rng = np.random.default_rng(seed)
        self._reflectors: list[Reflector] = []
        self._measurements: list[GPSMeasurement] = []

    def add_reflector(self, position: tuple[float, float], height: float = 80, coeff: float = 0.5) -> None:
        self._reflectors.append(Reflector(position=position, height=height, reflection_coeff=coeff))

    def _multipath_error(self, pos: tuple[float, float, float]) -> tuple[float, float, bool]:
        """다중경로 오차 + HDOP"""
        extra_error = 0.0
        hdop = 1.0
        affected = False

        for ref in self._reflectors:
            dx = pos[0] - ref.position[0]
            dy = pos[1] - ref.position[1]
            dist = np.sqrt(dx**2 + dy**2)
            half_h = ref.height / 2

            if dist < ref.height * 2 and pos[2] < ref.height:
                # 다중경로 영향
                proximity = max(0, 1 - dist / (ref.height * 2))
                extra_error += proximity * ref.reflection_coeff * 10
                hdop += proximity * 2
                affected = True

        return extra_error, round(hdop, 2), affected

    def measure(self, true_pos: tuple[float, float, float]) -> GPSMeasurement:
        extra_err, hdop, affected = self._multipath_error(true_pos)
        total_accuracy = self.base_accuracy + extra_err

        noise = self._rng.normal(0, total_accuracy, size=3)
        noise[2] *= 1.5  # 고도 정확도 낮음

        measured = (
            round(true_pos[0] + noise[0], 2),
            round(true_pos[1] + noise[1], 2),
            round(true_pos[2] + noise[2], 2),
        )
        error = float(np.sqrt(sum((m - t)**2 for m, t in zip(measured, true_pos))))

        m = GPSMeasurement(
            measured_pos=measured, true_pos=true_pos,
            error_m=round(error, 2), hdop=hdop,
            multipath_affected=affected,
        )
        self._measurements.append(m)
        return m

    def average_error(self) -> float:
        if not self._measurements:
            return 0.0
        return round(float(np.mean([m.error_m for m in self._measurements])), 2)

    def multipath_rate(self) -> float:
        if not self._measurements:
            return 0.0
        return round(sum(1 for m in self._measurements if m.multipath_affected) / len(self._measurements) * 100, 1)

    def summary(self) -> dict[str, Any]:
        return {
            "reflectors": len(self._reflectors),
            "measurements": len(self._measurements),
            "avg_error_m": self.average_error(),
            "multipath_rate_pct": self.multipath_rate(),
        }
