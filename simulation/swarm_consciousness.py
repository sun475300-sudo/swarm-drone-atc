"""
Phase 478: Swarm Consciousness Simulator
집합지능, 창발 행동, 자기조직화 시뮬레이션.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class EmergentBehavior(Enum):
    FLOCKING = "flocking"
    FORAGING = "foraging"
    CLUSTERING = "clustering"
    MIGRATION = "migration"
    DEFENSE = "defense"


@dataclass
class ConsciousDrone:
    drone_id: int
    position: np.ndarray
    velocity: np.ndarray
    awareness: float = 1.0  # 0-1
    energy: float = 100.0
    state: str = "active"
    neighbors: List[int] = field(default_factory=list)
    memory: List[np.ndarray] = field(default_factory=list)


@dataclass
class SwarmMetric:
    cohesion: float
    alignment: float
    entropy: float
    emergent_behavior: EmergentBehavior
    collective_intelligence: float


class SwarmConsciousness:
    """Models emergent collective intelligence in drone swarms."""

    def __init__(self, n_drones: int = 50, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.drones: List[ConsciousDrone] = []
        self.step_count = 0
        self.metrics_history: List[SwarmMetric] = []

        for i in range(n_drones):
            pos = self.rng.uniform(-100, 100, 3)
            vel = self.rng.standard_normal(3) * 2
            self.drones.append(ConsciousDrone(i, pos, vel))

    def _update_neighbors(self, radius: float = 30.0) -> None:
        for d in self.drones:
            d.neighbors = []
            for other in self.drones:
                if d.drone_id == other.drone_id:
                    continue
                dist = np.linalg.norm(d.position - other.position)
                if dist < radius:
                    d.neighbors.append(other.drone_id)

    def _separation(self, drone: ConsciousDrone) -> np.ndarray:
        steer = np.zeros(3)
        for nid in drone.neighbors:
            diff = drone.position - self.drones[nid].position
            dist = np.linalg.norm(diff)
            if dist > 0:
                steer += diff / (dist ** 2)
        return steer

    def _alignment(self, drone: ConsciousDrone) -> np.ndarray:
        if not drone.neighbors:
            return np.zeros(3)
        avg_vel = np.mean([self.drones[n].velocity for n in drone.neighbors], axis=0)
        return avg_vel - drone.velocity

    def _cohesion(self, drone: ConsciousDrone) -> np.ndarray:
        if not drone.neighbors:
            return np.zeros(3)
        center = np.mean([self.drones[n].position for n in drone.neighbors], axis=0)
        return (center - drone.position) * 0.01

    def _awareness_update(self, drone: ConsciousDrone) -> float:
        if not drone.neighbors:
            return max(0, drone.awareness - 0.01)
        neighbor_awareness = np.mean([self.drones[n].awareness for n in drone.neighbors])
        return 0.9 * drone.awareness + 0.1 * neighbor_awareness

    def step(self, dt: float = 0.1) -> SwarmMetric:
        self.step_count += 1
        self._update_neighbors()

        for drone in self.drones:
            if drone.state != "active":
                continue
            sep = self._separation(drone) * 1.5
            ali = self._alignment(drone) * 1.0
            coh = self._cohesion(drone) * 1.0
            noise = self.rng.standard_normal(3) * 0.1

            acceleration = sep + ali + coh + noise
            drone.velocity += acceleration * dt
            speed = np.linalg.norm(drone.velocity)
            if speed > 10:
                drone.velocity = drone.velocity / speed * 10
            drone.position += drone.velocity * dt

            drone.awareness = self._awareness_update(drone)
            drone.energy -= 0.01
            if drone.energy <= 0:
                drone.state = "depleted"

            drone.memory.append(drone.position.copy())
            if len(drone.memory) > 50:
                drone.memory.pop(0)

        metric = self._compute_metrics()
        self.metrics_history.append(metric)
        return metric

    def _compute_metrics(self) -> SwarmMetric:
        active = [d for d in self.drones if d.state == "active"]
        if not active:
            return SwarmMetric(0, 0, 0, EmergentBehavior.CLUSTERING, 0)

        positions = np.array([d.position for d in active])
        velocities = np.array([d.velocity for d in active])

        center = np.mean(positions, axis=0)
        cohesion = 1.0 / (1 + np.mean(np.linalg.norm(positions - center, axis=1)))

        avg_vel = np.mean(velocities, axis=0)
        avg_speed = np.linalg.norm(avg_vel)
        speeds = np.linalg.norm(velocities, axis=1)
        alignment = avg_speed / (np.mean(speeds) + 1e-10)

        spread = np.std(positions)
        entropy = float(np.log(spread + 1))

        if alignment > 0.8:
            behavior = EmergentBehavior.MIGRATION
        elif cohesion > 0.5:
            behavior = EmergentBehavior.FLOCKING
        elif entropy < 1:
            behavior = EmergentBehavior.CLUSTERING
        else:
            behavior = EmergentBehavior.FORAGING

        ci = (cohesion + alignment) / 2 * np.mean([d.awareness for d in active])

        return SwarmMetric(
            cohesion=round(float(cohesion), 4),
            alignment=round(float(alignment), 4),
            entropy=round(float(entropy), 4),
            emergent_behavior=behavior,
            collective_intelligence=round(float(ci), 4)
        )

    def run_for(self, steps: int, dt: float = 0.1) -> List[SwarmMetric]:
        return [self.step(dt) for _ in range(steps)]

    def summary(self) -> Dict:
        active = sum(1 for d in self.drones if d.state == "active")
        last = self.metrics_history[-1] if self.metrics_history else None
        return {
            "total_drones": self.n_drones,
            "active": active,
            "steps": self.step_count,
            "behavior": last.emergent_behavior.value if last else "none",
            "collective_intelligence": last.collective_intelligence if last else 0,
            "cohesion": last.cohesion if last else 0,
            "alignment": last.alignment if last else 0,
        }
