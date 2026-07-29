"""
Phase 442: Emergency Landing System for Critical Situations
"""

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class LandingSite:
    """``LandingSite`` 관련 기능을 제공한다."""
    position: np.ndarray
    suitability: float
    distance: float


class EmergencyLandingSystem:
    """``EmergencyLandingSystem`` 역할을 담당한다."""
    def __init__(self, max_altitude_m: float = 120):
        """인스턴스를 초기화한다."""
        self.max_altitude = max_altitude_m
        self.emergency_history: list[dict] = []

    def detect_emergency(self, battery_percent: float, sensor_status: dict) -> bool:
        """`emergency` 결과를 계산하거나 판정한다."""
        if battery_percent < 5:
            return True
        if sensor_status.get("gps_lost", False):
            return True
        return bool(sensor_status.get("motor_failure", False))

    def find_safe_landing_site(
        self, position: np.ndarray, terrain: np.ndarray
    ) -> LandingSite | None:
        """``find_safe_landing_site`` 동작을 수행한다."""
        candidates = []

        for _i in range(10):
            offset = np.random.randn(3) * 50
            candidate_pos = position + offset
            candidate_pos[2] = 0

            dist = np.linalg.norm(offset)
            suitability = np.random.uniform(0.5, 1.0)

            candidates.append(LandingSite(candidate_pos, suitability, dist))

        candidates.sort(key=lambda s: s.suitability * 1000 - s.distance)

        return candidates[0] if candidates else None

    def compute_descent_trajectory(
        self,
        start: np.ndarray,
        goal: np.ndarray,
        obstacles: list[np.ndarray],
    ) -> list[np.ndarray]:
        """`descent trajectory` 값을 계산한다."""
        points = []

        for t in np.linspace(0, 1, 20):
            point = start + (goal - start) * t
            point[2] = start[2] + (goal[2] - start[2]) * t

            for obs in obstacles:
                if np.linalg.norm(point - obs) < 10:
                    point += (point - obs) / np.linalg.norm(point - obs) * 5

            points.append(point)

        return points

    def execute_emergency(self, drone_id: str, reason: str, position: np.ndarray):
        """``execute_emergency`` 동작을 수행한다."""
        self.emergency_history.append(
            {
                "drone_id": drone_id,
                "reason": reason,
                "position": position.tolist(),
                "timestamp": time.time(),
            }
        )
