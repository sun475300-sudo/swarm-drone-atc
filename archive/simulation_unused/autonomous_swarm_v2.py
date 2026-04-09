"""
Phase 461: Autonomous Swarm v2 Engine
Advanced autonomous swarm intelligence with emergent behavior.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import defaultdict


class SwarmBehavior(Enum):
    """Swarm behavior modes."""

    FLOCKING = auto()
    FORAGING = auto()
    PATROLLING = auto()
    FORMATION = auto()
    EMERGENCY = auto()
    EXPLORATION = auto()


class DroneRole(Enum):
    """Drone roles in swarm."""

    LEADER = auto()
    FOLLOWER = auto()
    SCOUT = auto()
    RELAY = auto()
    WORKER = auto()


@dataclass
class SwarmDrone:
    """Drone in autonomous swarm."""

    drone_id: str
    position: np.ndarray
    velocity: np.ndarray
    role: DroneRole
    energy: float = 100.0
    sensor_range: float = 100.0
    communication_range: float = 200.0
    neighbors: List[str] = field(default_factory=list)
    local_map: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmState:
    """Swarm collective state."""

    centroid: np.ndarray
    spread: float
    cohesion: float
    alignment: float
    separation: float
    energy_total: float
    coverage_area: float


@dataclass
class EmergentPattern:
    """Emergent behavior pattern."""

    pattern_id: str
    pattern_type: str
    participants: List[str]
    confidence: float
    stability: float
    timestamp: float = field(default_factory=time.time)


class AutonomousSwarmEngine:
    """Autonomous swarm intelligence engine."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.drones: Dict[str, SwarmDrone] = {}
        self.behavior_mode = SwarmBehavior.FLOCKING
        self.emergent_patterns: List[EmergentPattern] = []
        self.global_objective: Optional[np.ndarray] = None
        self.time_step = 0
        self._init_swarm(n_drones)

    def _init_swarm(self, n: int) -> None:
        for i in range(n):
            pos = self.rng.uniform(-100, 100, size=3)
            vel = self.rng.uniform(-5, 5, size=3)
            role = DroneRole.FOLLOWER if i > 0 else DroneRole.LEADER
            drone = SwarmDrone(f"drone_{i}", pos, vel, role)
            self.drones[drone.drone_id] = drone

    def set_behavior(self, behavior: SwarmBehavior) -> None:
        self.behavior_mode = behavior

    def set_objective(self, target: np.ndarray) -> None:
        self.global_objective = target.copy()

    def _update_neighbors(self) -> None:
        drone_list = list(self.drones.values())
        for d in drone_list:
            d.neighbors = []
            for other in drone_list:
                if d.drone_id == other.drone_id:
                    continue
                dist = np.linalg.norm(d.position - other.position)
                if dist < d.communication_range:
                    d.neighbors.append(other.drone_id)

    def _separation(self, drone: SwarmDrone) -> np.ndarray:
        force = np.zeros(3)
        for nid in drone.neighbors:
            other = self.drones[nid]
            diff = drone.position - other.position
            dist = np.linalg.norm(diff)
            if dist > 0 and dist < 20:
                force += diff / (dist**2)
        return force * 1.5

    def _alignment(self, drone: SwarmDrone) -> np.ndarray:
        if not drone.neighbors:
            return np.zeros(3)
        avg_vel = np.mean(
            [self.drones[nid].velocity for nid in drone.neighbors], axis=0
        )
        return (avg_vel - drone.velocity) * 0.1

    def _cohesion(self, drone: SwarmDrone) -> np.ndarray:
        if not drone.neighbors:
            return np.zeros(3)
        centroid = np.mean(
            [self.drones[nid].position for nid in drone.neighbors], axis=0
        )
        return (centroid - drone.position) * 0.01

    def _objective_force(self, drone: SwarmDrone) -> np.ndarray:
        if self.global_objective is None:
            return np.zeros(3)
        direction = self.global_objective - drone.position
        dist = np.linalg.norm(direction)
        if dist > 0:
            return direction / dist * 0.5
        return np.zeros(3)

    def _foraging_behavior(self, drone: SwarmDrone) -> np.ndarray:
        force = self._separation(drone) + self._cohesion(drone) * 0.5
        exploration = self.rng.uniform(-1, 1, size=3)
        return force + exploration * 0.3

    def _patrolling_behavior(self, drone: SwarmDrone) -> np.ndarray:
        if self.global_objective is None:
            return np.zeros(3)
        angle = np.arctan2(
            drone.position[1] - self.global_objective[1],
            drone.position[0] - self.global_objective[0],
        )
        angle += 0.1
        radius = np.linalg.norm(drone.position[:2] - self.global_objective[:2])
        target = self.global_objective.copy()
        target[0] += radius * np.cos(angle)
        target[1] += radius * np.sin(angle)
        return (target - drone.position) * 0.05

    def step(self, dt: float = 0.1) -> SwarmState:
        self._update_neighbors()
        self.time_step += 1
        for drone in self.drones.values():
            if self.behavior_mode == SwarmBehavior.FLOCKING:
                sep = self._separation(drone)
                ali = self._alignment(drone)
                coh = self._cohesion(drone)
                obj = self._objective_force(drone)
                force = sep + ali + coh + obj
            elif self.behavior_mode == SwarmBehavior.FORAGING:
                force = self._foraging_behavior(drone)
            elif self.behavior_mode == SwarmBehavior.PATROLLING:
                force = self._patrolling_behavior(drone)
            elif self.behavior_mode == SwarmBehavior.EXPLORATION:
                force = self._separation(drone) + self.rng.uniform(-1, 1, size=3) * 0.5
            else:
                force = (
                    self._separation(drone)
                    + self._alignment(drone)
                    + self._cohesion(drone)
                )
            drone.velocity += force * dt
            speed = np.linalg.norm(drone.velocity)
            if speed > 20:
                drone.velocity = drone.velocity / speed * 20
            drone.position += drone.velocity * dt
            drone.energy -= 0.01 * speed * dt
        self._detect_emergent_patterns()
        return self._compute_swarm_state()

    def _detect_emergent_patterns(self) -> None:
        positions = np.array([d.position for d in self.drones.values()])
        centroid = positions.mean(axis=0)
        distances = np.linalg.norm(positions - centroid, axis=1)
        if distances.std() < 10:
            pattern = EmergentPattern(
                f"cluster_{self.time_step}",
                "tight_formation",
                list(self.drones.keys()),
                0.9,
                0.8,
            )
            self.emergent_patterns.append(pattern)

    def _compute_swarm_state(self) -> SwarmState:
        positions = np.array([d.position for d in self.drones.values()])
        velocities = np.array([d.velocity for d in self.drones.values()])
        centroid = positions.mean(axis=0)
        spread = np.mean(np.linalg.norm(positions - centroid, axis=1))
        if len(velocities) > 1:
            avg_vel = velocities.mean(axis=0)
            alignment = np.mean(
                [
                    np.dot(v, avg_vel)
                    / (np.linalg.norm(v) * np.linalg.norm(avg_vel) + 1e-8)
                    for v in velocities
                ]
            )
        else:
            alignment = 1.0
        return SwarmState(
            centroid=centroid,
            spread=spread,
            cohesion=1.0 / (1.0 + spread),
            alignment=alignment,
            separation=spread / len(self.drones) if self.drones else 0,
            energy_total=sum(d.energy for d in self.drones.values()),
            coverage_area=np.pi * spread**2,
        )

    def run(self, n_steps: int = 100, dt: float = 0.1) -> List[SwarmState]:
        states = []
        for _ in range(n_steps):
            state = self.step(dt)
            states.append(state)
        return states

    def get_swarm_stats(self) -> Dict[str, Any]:
        state = self._compute_swarm_state()
        return {
            "n_drones": len(self.drones),
            "behavior": self.behavior_mode.name,
            "centroid": state.centroid.tolist(),
            "spread": state.spread,
            "cohesion": state.cohesion,
            "alignment": state.alignment,
            "energy_total": state.energy_total,
            "emergent_patterns": len(self.emergent_patterns),
        }


class MultiSwarmCoordinator:
    """Coordinator for multiple autonomous swarms."""

    def __init__(self, n_swarms: int, drones_per_swarm: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.swarms: Dict[str, AutonomousSwarmEngine] = {}
        self._init_swarms(n_swarms, drones_per_swarm)

    def _init_swarms(self, n_swarms: int, drones_per: int) -> None:
        for i in range(n_swarms):
            swarm = AutonomousSwarmEngine(drones_per, self.rng.integers(10000))
            offset = np.array([i * 500, 0, 0])
            for drone in swarm.drones.values():
                drone.position += offset
            self.swarms[f"swarm_{i}"] = swarm

    def set_global_objectives(self, objectives: Dict[str, np.ndarray]) -> None:
        for swarm_id, target in objectives.items():
            if swarm_id in self.swarms:
                self.swarms[swarm_id].set_objective(target)

    def step_all(self, dt: float = 0.1) -> Dict[str, SwarmState]:
        states = {}
        for swarm_id, swarm in self.swarms.items():
            states[swarm_id] = swarm.step(dt)
        return states

    def get_coordination_stats(self) -> Dict[str, Any]:
        total_drones = sum(len(s.drones) for s in self.swarms.values())
        avg_cohesion = np.mean(
            [s._compute_swarm_state().cohesion for s in self.swarms.values()]
        )
        return {
            "n_swarms": len(self.swarms),
            "total_drones": total_drones,
            "avg_cohesion": avg_cohesion,
            "swarm_stats": {sid: s.get_swarm_stats() for sid, s in self.swarms.items()},
        }


if __name__ == "__main__":
    swarm = AutonomousSwarmEngine(n_drones=20, seed=42)
    swarm.set_behavior(SwarmBehavior.FLOCKING)
    swarm.set_objective(np.array([500, 500, 100]))
    states = swarm.run(n_steps=100, dt=0.1)
    print(f"Final stats: {swarm.get_swarm_stats()}")
    print(f"Final spread: {states[-1].spread:.2f}")
    print(f"Final cohesion: {states[-1].cohesion:.4f}")
