"""
Phase 442: Emergency Landing System for Critical Situations
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time


@dataclass
class LandingSite:
    position: np.ndarray
    suitability: float
    distance: float


class EmergencyLandingSystem:
    def __init__(self, max_altitude_m: float = 120):
        self.max_altitude = max_altitude_m
        self.emergency_history: List[Dict] = []

    def detect_emergency(self, battery_percent: float, sensor_status: Dict) -> bool:
        if battery_percent < 5:
            return True
        if sensor_status.get("gps_lost", False):
            return True
        if sensor_status.get("motor_failure", False):
            return True
        return False

    def find_safe_landing_site(
        self, position: np.ndarray, terrain: np.ndarray
    ) -> Optional[LandingSite]:
        candidates = []

        for i in range(10):
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
        obstacles: List[np.ndarray],
    ) -> List[np.ndarray]:
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
        self.emergency_history.append(
            {
                "drone_id": drone_id,
                "reason": reason,
                "position": position.tolist(),
                "timestamp": time.time(),
            }
        )
