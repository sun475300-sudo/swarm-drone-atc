"""
Phase 451: Mission Planning System for Complex Operations
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class Waypoint:
    """``Waypoint`` 관련 기능을 제공한다."""
    x: float
    y: float
    z: float
    action: str


@dataclass
class Mission:
    """``Mission`` 관련 기능을 제공한다."""
    mission_id: str
    waypoints: list[Waypoint]
    drones_required: int
    estimated_duration: float


class MissionPlanningSystem:
    """``MissionPlanningSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.missions: dict[str, Mission] = {}
        self.completed: list[str] = []

    def plan_mission(
        self, mission_id: str, num_waypoints: int, area_bounds: tuple
    ) -> Mission:
        """`mission` 작업을 계획한다."""
        waypoints = []
        for i in range(num_waypoints):
            wp = Waypoint(
                x=np.random.uniform(area_bounds[0], area_bounds[1]),
                y=np.random.uniform(area_bounds[2], area_bounds[3]),
                z=np.random.uniform(50, 150),
                action="survey" if i % 2 == 0 else "hover",
            )
            waypoints.append(wp)

        mission = Mission(mission_id, waypoints, 1, num_waypoints * 2.0)
        self.missions[mission_id] = mission
        return mission

    def optimize_route(self, mission: Mission) -> list[Waypoint]:
        """``optimize_route`` 동작을 수행한다."""
        return sorted(mission.waypoints, key=lambda w: w.x + w.y)
