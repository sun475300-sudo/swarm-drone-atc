"""
Phase 445: Traffic Coordinator for UAV Airspace Management
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class UAVTraffic:
    """``UAVTraffic`` 관련 기능을 제공한다."""
    uav_id: str
    position: np.ndarray
    velocity: np.ndarray
    destination: np.ndarray


class TrafficCoordinator:
    """``TrafficCoordinator`` 관련 기능을 제공한다."""
    def __init__(
        self, airspace_bounds: tuple[float, float, float, float, float, float]
    ):
        """인스턴스를 초기화한다."""
        self.bounds = airspace_bounds
        self.uavs: dict[str, UAVTraffic] = {}
        self.conflicts: list[tuple[str, str]] = []

    def register_uav(self, uav: UAVTraffic):
        """`uav` 항목을 추가한다."""
        self.uavs[uav.uav_id] = uav

    def detect_conflicts(
        self, separation_distance: float = 50.0
    ) -> list[tuple[str, str]]:
        """`conflicts` 결과를 계산하거나 판정한다."""
        conflicts = []

        uav_list = list(self.uavs.values())

        for i in range(len(uav_list)):
            for j in range(i + 1, len(uav_list)):
                dist = np.linalg.norm(uav_list[i].position - uav_list[j].position)

                if dist < separation_distance:
                    conflicts.append((uav_list[i].uav_id, uav_list[j].uav_id))

        self.conflicts = conflicts
        return conflicts

    def resolve_conflicts(self) -> dict[str, np.ndarray]:
        """``resolve_conflicts`` 동작을 수행한다."""
        maneuvers = {}

        for uav1_id, uav2_id in self.conflicts:
            uav1 = self.uavs[uav1_id]
            uav2 = self.uavs[uav2_id]

            direction = uav1.position - uav2.position
            direction /= np.linalg.norm(direction) + 1e-6

            maneuvers[uav1_id] = direction * 5
            maneuvers[uav2_id] = -direction * 5

        return maneuvers

    def get_traffic_density(self, region: tuple[float, float, float, float]) -> int:
        """`traffic density` 정보를 조회한다."""
        count = 0
        for uav in self.uavs.values():
            if (
                region[0] <= uav.position[0] <= region[1]
                and region[2] <= uav.position[1] <= region[3]
            ):
                count += 1
        return count
