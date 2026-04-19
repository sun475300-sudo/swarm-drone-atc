"""
비행 계획 검증
==============
비행 계획 규정 검증 + NFZ + 고도/속도 제한.

사용법:
    fpv = FlightPlanValidator()
    fpv.add_nfz("NFZ1", center=(500, 500), radius=100)
    result = fpv.validate(waypoints, max_alt=120, max_speed=15)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ValidationIssue:
    """검증 문제"""
    issue_type: str  # NFZ_VIOLATION, ALTITUDE, SPEED, DISTANCE
    severity: str  # ERROR, WARNING
    waypoint_idx: int
    description: str


@dataclass
class ValidationResult:
    """검증 결과"""
    valid: bool
    issues: list[ValidationIssue]
    score: float  # 0~100


class FlightPlanValidator:
    """비행 계획 규정 검증."""

    def __init__(self) -> None:
        self._nfz_zones: list[dict[str, Any]] = []
        self._max_altitude = 120.0
        self._min_altitude = 30.0
        self._max_speed = 20.0
        self._max_segment_length = 5000.0

    def add_nfz(self, nfz_id: str, center: tuple[float, float], radius: float) -> None:
        self._nfz_zones.append({"id": nfz_id, "center": center, "radius": radius})

    def set_limits(
        self, max_altitude: float = 120.0, min_altitude: float = 30.0,
        max_speed: float = 20.0,
    ) -> None:
        self._max_altitude = max_altitude
        self._min_altitude = min_altitude
        self._max_speed = max_speed

    def validate(
        self, waypoints: list[tuple[float, float, float]],
        speed_limit: float | None = None,
    ) -> ValidationResult:
        """비행 계획 검증"""
        issues = []
        max_spd = speed_limit or self._max_speed

        for i, wp in enumerate(waypoints):
            # 고도 검증
            if wp[2] > self._max_altitude:
                issues.append(ValidationIssue(
                    "ALTITUDE", "ERROR", i,
                    f"고도 {wp[2]}m > 최대 {self._max_altitude}m",
                ))
            if wp[2] < self._min_altitude:
                issues.append(ValidationIssue(
                    "ALTITUDE", "WARNING", i,
                    f"고도 {wp[2]}m < 최소 {self._min_altitude}m",
                ))

            # NFZ 검증
            for nfz in self._nfz_zones:
                dx = wp[0] - nfz["center"][0]
                dy = wp[1] - nfz["center"][1]
                if dx*dx + dy*dy < nfz["radius"]**2:
                    issues.append(ValidationIssue(
                        "NFZ_VIOLATION", "ERROR", i,
                        f"NFZ {nfz['id']} 침범 (반경 {nfz['radius']}m)",
                    ))

            # 구간 거리 검증
            if i > 0:
                dist = float(np.linalg.norm(
                    np.array(waypoints[i]) - np.array(waypoints[i-1])
                ))
                if dist > self._max_segment_length:
                    issues.append(ValidationIssue(
                        "DISTANCE", "WARNING", i,
                        f"구간 거리 {dist:.0f}m > {self._max_segment_length}m",
                    ))

        errors = sum(1 for i in issues if i.severity == "ERROR")
        total_checks = len(waypoints) * (2 + len(self._nfz_zones))
        score = max(0, (1 - errors / max(total_checks, 1)) * 100)

        return ValidationResult(
            valid=errors == 0,
            issues=issues,
            score=round(score, 1),
        )

    def quick_check(self, waypoints: list[tuple[float, float, float]]) -> bool:
        return self.validate(waypoints).valid

    def summary(self) -> dict[str, Any]:
        return {
            "nfz_count": len(self._nfz_zones),
            "max_altitude": self._max_altitude,
            "max_speed": self._max_speed,
        }
