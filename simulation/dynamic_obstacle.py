"""
동적 장애물 관리
===============
이동 장애물 예측 + 버드 스트라이크 + 건설 크레인.

사용법:
    do = DynamicObstacle()
    do.add_obstacle("bird_flock", pos=(200,300,60), velocity=(5,-3,0), radius=20)
    threats = do.check_threats(drone_pos=(210, 290, 55), t=1.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Obstacle:
    """장애물"""
    obstacle_id: str
    obstacle_type: str  # BIRD, CRANE, AIRCRAFT, BALLOON, UNKNOWN
    position: tuple[float, float, float]
    velocity: tuple[float, float, float] = (0, 0, 0)
    radius: float = 10.0
    active: bool = True


@dataclass
class ThreatInfo:
    """위협 정보"""
    obstacle_id: str
    distance: float
    time_to_closest: float
    closest_distance: float
    severity: str  # LOW, MEDIUM, HIGH


class DynamicObstacle:
    """동적 장애물 관리."""

    def __init__(self) -> None:
        self._obstacles: dict[str, Obstacle] = {}
        self._threats: list[ThreatInfo] = []

    def add_obstacle(
        self, obstacle_id: str, pos: tuple[float, float, float],
        velocity: tuple[float, float, float] = (0, 0, 0),
        radius: float = 10, obstacle_type: str = "UNKNOWN",
    ) -> None:
        self._obstacles[obstacle_id] = Obstacle(
            obstacle_id=obstacle_id, obstacle_type=obstacle_type,
            position=pos, velocity=velocity, radius=radius,
        )

    def remove_obstacle(self, obstacle_id: str) -> None:
        self._obstacles.pop(obstacle_id, None)

    def update_positions(self, dt: float) -> None:
        for obs in self._obstacles.values():
            if not obs.active:
                continue
            obs.position = tuple(
                p + v * dt for p, v in zip(obs.position, obs.velocity)
            )

    def predicted_position(self, obstacle_id: str, t_ahead: float) -> tuple[float, float, float] | None:
        obs = self._obstacles.get(obstacle_id)
        if not obs:
            return None
        return tuple(p + v * t_ahead for p, v in zip(obs.position, obs.velocity))

    def check_threats(
        self, drone_pos: tuple[float, float, float],
        drone_vel: tuple[float, float, float] = (0, 0, 0),
        t: float = 0.0, lookahead: float = 30.0,
    ) -> list[ThreatInfo]:
        threats = []
        dp = np.array(drone_pos)
        dv = np.array(drone_vel)

        for obs in self._obstacles.values():
            if not obs.active:
                continue
            op = np.array(obs.position)
            ov = np.array(obs.velocity)

            dist = float(np.linalg.norm(dp - op))

            # CPA 계산
            rel_pos = op - dp
            rel_vel = ov - dv
            speed_sq = float(np.dot(rel_vel, rel_vel))
            if speed_sq > 0.01:
                t_cpa = -float(np.dot(rel_pos, rel_vel)) / speed_sq
                t_cpa = max(0, min(lookahead, t_cpa))
            else:
                t_cpa = 0

            cpa_pos_d = dp + dv * t_cpa
            cpa_pos_o = op + ov * t_cpa
            cpa_dist = float(np.linalg.norm(cpa_pos_d - cpa_pos_o))

            if cpa_dist < obs.radius * 5:
                if cpa_dist < obs.radius:
                    severity = "HIGH"
                elif cpa_dist < obs.radius * 2:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                threat = ThreatInfo(
                    obstacle_id=obs.obstacle_id,
                    distance=round(dist, 1),
                    time_to_closest=round(t_cpa, 1),
                    closest_distance=round(cpa_dist, 1),
                    severity=severity,
                )
                threats.append(threat)
                self._threats.append(threat)

        return threats

    def active_obstacles(self) -> int:
        return sum(1 for o in self._obstacles.values() if o.active)

    def summary(self) -> dict[str, Any]:
        types = {}
        for o in self._obstacles.values():
            types[o.obstacle_type] = types.get(o.obstacle_type, 0) + 1
        return {
            "total_obstacles": len(self._obstacles),
            "active": self.active_obstacles(),
            "type_distribution": types,
            "total_threats": len(self._threats),
        }
