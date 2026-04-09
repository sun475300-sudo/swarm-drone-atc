"""
Phase 445: Traffic Coordinator for UAV Airspace Management
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import time


@dataclass
class UAVTraffic:
    uav_id: str
    position: np.ndarray
    velocity: np.ndarray
    destination: np.ndarray


class TrafficCoordinator:
    def __init__(
        self, airspace_bounds: Tuple[float, float, float, float, float, float]
    ):
        self.bounds = airspace_bounds
        self.uavs: Dict[str, UAVTraffic] = {}
        self.conflicts: List[Tuple[str, str]] = []

    def register_uav(self, uav: UAVTraffic):
        self.uavs[uav.uav_id] = uav

    def detect_conflicts(
        self, separation_distance: float = 50.0
    ) -> List[Tuple[str, str]]:
        conflicts = []

        uav_list = list(self.uavs.values())

        for i in range(len(uav_list)):
            for j in range(i + 1, len(uav_list)):
                dist = np.linalg.norm(uav_list[i].position - uav_list[j].position)

                if dist < separation_distance:
                    conflicts.append((uav_list[i].uav_id, uav_list[j].uav_id))

        self.conflicts = conflicts
        return conflicts

    def resolve_conflicts(self) -> Dict[str, np.ndarray]:
        maneuvers = {}

        for uav1_id, uav2_id in self.conflicts:
            uav1 = self.uavs[uav1_id]
            uav2 = self.uavs[uav2_id]

            direction = uav1.position - uav2.position
            direction /= np.linalg.norm(direction) + 1e-6

            maneuvers[uav1_id] = direction * 5
            maneuvers[uav2_id] = -direction * 5

        return maneuvers

    def get_traffic_density(self, region: Tuple[float, float, float, float]) -> int:
        count = 0
        for uav in self.uavs.values():
            if (
                region[0] <= uav.position[0] <= region[1]
                and region[2] <= uav.position[1] <= region[3]
            ):
                count += 1
        return count
