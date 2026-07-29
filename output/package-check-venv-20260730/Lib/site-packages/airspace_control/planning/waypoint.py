"""경로점 및 경로 데이터클래스"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class Waypoint:
    position: np.ndarray    # [north, east, down] (미터)
    speed_ms: float = 8.0   # 이 경로점 도달 시 속도
    hover_s:  float = 0.0   # 도달 후 체공 시간

    def distance_to(self, other: Waypoint) -> float:
        return float(np.linalg.norm(other.position - self.position))

    def lateral_distance_to(self, other: Waypoint) -> float:
        return float(np.linalg.norm(other.position[:2] - self.position[:2]))


@dataclass
class Route:
    route_id:   str
    drone_id:   str
    waypoints:  list[Waypoint] = field(default_factory=list)
    created_at: float = 0.0
    priority:   int = 3      # 1=긴급, 2=임무, 3=일반

    @property
    def total_distance_m(self) -> float:
        if len(self.waypoints) < 2:
            return 0.0
        return sum(
            self.waypoints[i].distance_to(self.waypoints[i + 1])
            for i in range(len(self.waypoints) - 1)
        )

    @property
    def origin(self) -> Optional[np.ndarray]:
        return self.waypoints[0].position if self.waypoints else None

    @property
    def destination(self) -> Optional[np.ndarray]:
        return self.waypoints[-1].position if self.waypoints else None

    def get_current_waypoint(self, idx: int) -> Optional[Waypoint]:
        if 0 <= idx < len(self.waypoints):
            return self.waypoints[idx]
        return None


@dataclass
class RouteCost:
    distance_m:  float
    duration_s:  float
    energy_wh:   float
    risk_score:  float = 0.0   # 0.0 ~ 1.0, 충돌 위험도
