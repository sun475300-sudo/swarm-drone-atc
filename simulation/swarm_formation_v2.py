"""Phase 315: Autonomous Swarm Formation v2 — 자율 군집 대형 v2.

포텐셜 필드 + Voronoi 기반 대형 유지,
장애물 회피, 리더-팔로워 전환, 대형 모핑.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class FormationType(Enum):
    V_FORMATION = "v_formation"
    LINE = "line"
    GRID = "grid"
    CIRCLE = "circle"
    DIAMOND = "diamond"
    WEDGE = "wedge"
    COLUMN = "column"
    CUSTOM = "custom"


class DroneRole(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    SCOUT = "scout"
    RELAY = "relay"


@dataclass
class FormationDrone:
    drone_id: str
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    target_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    role: DroneRole = DroneRole.FOLLOWER
    formation_offset: np.ndarray = field(default_factory=lambda: np.zeros(3))


@dataclass
class FormationConfig:
    formation_type: FormationType
    spacing: float = 20.0
    altitude: float = 50.0
    heading_deg: float = 0.0
    speed: float = 10.0


class SwarmFormationV2:
    """자율 군집 대형 v2.

    - 포텐셜 필드 기반 대형 유지
    - 7가지 기본 대형 + 커스텀
    - 리더-팔로워 전환
    - 장애물 회피 통합
    - 대형 모핑 (부드러운 전환)
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._drones: Dict[str, FormationDrone] = {}
        self._config = FormationConfig(FormationType.V_FORMATION)
        self._leader_id: Optional[str] = None
        self._obstacles: List[Tuple[np.ndarray, float]] = []  # (center, radius)
        self._step_count = 0
        self._morph_progress = 1.0  # 1.0 = complete

    def add_drone(self, drone_id: str, position: np.ndarray, role: DroneRole = DroneRole.FOLLOWER):
        drone = FormationDrone(drone_id=drone_id, position=position.copy(), role=role)
        self._drones[drone_id] = drone
        if role == DroneRole.LEADER:
            self._leader_id = drone_id

    def add_obstacle(self, center: np.ndarray, radius: float):
        self._obstacles.append((center.copy(), radius))

    def set_formation(self, config: FormationConfig):
        self._config = config
        self._morph_progress = 0.0
        self._compute_offsets()

    def _compute_offsets(self):
        """Compute formation offsets for each drone."""
        drones = list(self._drones.values())
        n = len(drones)
        spacing = self._config.spacing
        heading = np.radians(self._config.heading_deg)

        for i, drone in enumerate(drones):
            if drone.role == DroneRole.LEADER:
                drone.formation_offset = np.zeros(3)
                continue

            idx = i - (1 if self._leader_id else 0)
            if self._config.formation_type == FormationType.V_FORMATION:
                side = 1 if idx % 2 == 0 else -1
                row = (idx + 1) // 2
                offset = np.array([
                    -row * spacing * np.cos(np.radians(30)),
                    side * row * spacing * np.sin(np.radians(30)),
                    0.0,
                ])
            elif self._config.formation_type == FormationType.LINE:
                offset = np.array([-idx * spacing, 0.0, 0.0])
            elif self._config.formation_type == FormationType.GRID:
                cols = max(1, int(np.ceil(np.sqrt(n))))
                row, col = divmod(idx, cols)
                offset = np.array([
                    -row * spacing,
                    (col - cols / 2) * spacing,
                    0.0,
                ])
            elif self._config.formation_type == FormationType.CIRCLE:
                angle = 2 * np.pi * idx / max(n - 1, 1)
                r = spacing * n / (2 * np.pi)
                offset = np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
            elif self._config.formation_type == FormationType.DIAMOND:
                if idx < n // 2:
                    offset = np.array([-idx * spacing * 0.7, idx * spacing * 0.7, 0.0])
                else:
                    j = idx - n // 2
                    offset = np.array([-j * spacing * 0.7, -j * spacing * 0.7, 0.0])
            elif self._config.formation_type == FormationType.WEDGE:
                row = idx
                offset = np.array([-row * spacing, row * spacing * 0.5 * (1 if idx % 2 == 0 else -1), 0.0])
            elif self._config.formation_type == FormationType.COLUMN:
                offset = np.array([-idx * spacing, 0.0, 0.0])
            else:
                offset = np.zeros(3)

            # Rotate by heading
            cos_h, sin_h = np.cos(heading), np.sin(heading)
            rotated = np.array([
                offset[0] * cos_h - offset[1] * sin_h,
                offset[0] * sin_h + offset[1] * cos_h,
                offset[2],
            ])
            drone.formation_offset = rotated

    def step(self, dt: float = 0.1):
        """Advance formation by one step using potential field control."""
        if not self._leader_id or self._leader_id not in self._drones:
            return

        leader = self._drones[self._leader_id]
        self._morph_progress = min(1.0, self._morph_progress + dt * 0.5)

        for drone in self._drones.values():
            if drone.role == DroneRole.LEADER:
                # Leader moves forward
                heading = np.radians(self._config.heading_deg)
                drone.velocity = np.array([
                    self._config.speed * np.cos(heading),
                    self._config.speed * np.sin(heading),
                    0.0,
                ])
                drone.position += drone.velocity * dt
                continue

            # Target = leader position + offset
            target = leader.position + drone.formation_offset * self._morph_progress
            target[2] = self._config.altitude
            drone.target_position = target

            # Attraction to target
            to_target = target - drone.position
            dist = np.linalg.norm(to_target)
            if dist > 0.1:
                attract = to_target / dist * min(dist, self._config.speed)
            else:
                attract = np.zeros(3)

            # Obstacle repulsion
            repel = np.zeros(3)
            for obs_center, obs_radius in self._obstacles:
                to_drone = drone.position - obs_center
                obs_dist = np.linalg.norm(to_drone)
                if obs_dist < obs_radius * 2 and obs_dist > 0:
                    repel += to_drone / obs_dist * (obs_radius * 2 - obs_dist) * 2

            # Inter-drone repulsion (separation)
            for other in self._drones.values():
                if other.drone_id == drone.drone_id:
                    continue
                diff = drone.position - other.position
                d = np.linalg.norm(diff)
                if d < self._config.spacing * 0.5 and d > 0:
                    repel += diff / d * (self._config.spacing * 0.5 - d) * 1.5

            drone.velocity = attract + repel
            speed = np.linalg.norm(drone.velocity)
            if speed > self._config.speed:
                drone.velocity = drone.velocity / speed * self._config.speed
            drone.position += drone.velocity * dt

        self._step_count += 1

    def get_cohesion(self) -> float:
        """Measure formation cohesion (0-1, 1=perfect)."""
        if len(self._drones) < 2 or not self._leader_id:
            return 1.0
        leader = self._drones[self._leader_id]
        errors = []
        for drone in self._drones.values():
            if drone.role == DroneRole.LEADER:
                continue
            target = leader.position + drone.formation_offset
            error = np.linalg.norm(drone.position - target)
            errors.append(error)
        if not errors:
            return 1.0
        avg_error = np.mean(errors)
        return float(max(0, 1 - avg_error / (self._config.spacing * 2)))

    def get_formation_center(self) -> np.ndarray:
        if not self._drones:
            return np.zeros(3)
        return np.mean([d.position for d in self._drones.values()], axis=0)

    def summary(self) -> dict:
        return {
            "total_drones": len(self._drones),
            "formation": self._config.formation_type.value,
            "leader": self._leader_id,
            "cohesion": round(self.get_cohesion(), 4),
            "morph_progress": round(self._morph_progress, 2),
            "step_count": self._step_count,
            "obstacles": len(self._obstacles),
        }
