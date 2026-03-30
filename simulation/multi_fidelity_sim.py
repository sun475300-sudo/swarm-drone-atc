"""
Phase 482: Multi-Fidelity Simulation
저/중/고 충실도 시뮬레이션 계층, 적응형 전환.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable


class FidelityLevel(Enum):
    LOW = "low"        # 점입자 모델, 1Hz
    MEDIUM = "medium"  # 6DOF 간략, 10Hz
    HIGH = "high"      # 풀 6DOF + 공력, 100Hz


@dataclass
class SimState:
    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(3))
    orientation: np.ndarray = field(default_factory=lambda: np.zeros(3))  # roll, pitch, yaw
    angular_vel: np.ndarray = field(default_factory=lambda: np.zeros(3))
    time: float = 0.0
    fidelity: FidelityLevel = FidelityLevel.LOW


@dataclass
class FidelityMetrics:
    level: FidelityLevel
    compute_time_ms: float
    accuracy_score: float
    step_count: int


class LowFidelitySim:
    """Point-mass kinematic model."""
    def step(self, state: SimState, force: np.ndarray, dt: float, mass: float = 2.0) -> SimState:
        acc = force / mass
        new_vel = state.velocity + acc * dt
        speed = np.linalg.norm(new_vel)
        if speed > 20:
            new_vel = new_vel / speed * 20
        new_pos = state.position + new_vel * dt
        return SimState(new_pos, new_vel, acc, state.orientation,
                       state.angular_vel, state.time + dt, FidelityLevel.LOW)


class MediumFidelitySim:
    """Simplified 6DOF with drag."""
    def step(self, state: SimState, force: np.ndarray, dt: float,
             mass: float = 2.0, drag_coeff: float = 0.1) -> SimState:
        drag = -drag_coeff * state.velocity * np.linalg.norm(state.velocity)
        gravity = np.array([0, 0, -9.81 * mass])
        total_force = force + drag + gravity
        acc = total_force / mass
        new_vel = state.velocity + acc * dt
        new_pos = state.position + new_vel * dt
        heading = np.arctan2(new_vel[1], new_vel[0]) if np.linalg.norm(new_vel[:2]) > 0.1 else state.orientation[2]
        pitch = np.arctan2(-new_vel[2], np.linalg.norm(new_vel[:2])) if np.linalg.norm(new_vel) > 0.1 else 0
        orient = np.array([0, pitch, heading])
        return SimState(new_pos, new_vel, acc, orient,
                       state.angular_vel, state.time + dt, FidelityLevel.MEDIUM)


class HighFidelitySim:
    """Full 6DOF with aerodynamics and motor model."""
    def step(self, state: SimState, force: np.ndarray, torque: np.ndarray,
             dt: float, mass: float = 2.0, inertia: np.ndarray = None) -> SimState:
        if inertia is None:
            inertia = np.array([0.01, 0.01, 0.02])
        drag = -0.15 * state.velocity * np.linalg.norm(state.velocity)
        gravity = np.array([0, 0, -9.81 * mass])
        r, p, y = state.orientation
        cr, sr = np.cos(r), np.sin(r)
        cp, sp = np.cos(p), np.sin(p)
        body_force = np.array([
            force[0] * cp * np.cos(y) + force[1] * (sr * sp * np.cos(y) - cr * np.sin(y)),
            force[0] * cp * np.sin(y) + force[1] * (sr * sp * np.sin(y) + cr * np.cos(y)),
            force[0] * (-sp) + force[1] * sr * cp + force[2]
        ])
        total_force = body_force + drag + gravity
        acc = total_force / mass
        new_vel = state.velocity + acc * dt
        new_pos = state.position + new_vel * dt
        angular_acc = torque / inertia
        new_ang_vel = state.angular_vel + angular_acc * dt
        new_orient = state.orientation + new_ang_vel * dt
        return SimState(new_pos, new_vel, acc, new_orient,
                       new_ang_vel, state.time + dt, FidelityLevel.HIGH)


class MultiFidelitySim:
    """Adaptive multi-fidelity simulation engine."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.low = LowFidelitySim()
        self.medium = MediumFidelitySim()
        self.high = HighFidelitySim()
        self.current_level = FidelityLevel.LOW
        self.states: List[SimState] = []
        self.metrics: List[FidelityMetrics] = []
        self.step_count = 0
        self.auto_switch = True
        self._proximity_threshold = 20.0
        self._threat_positions: List[np.ndarray] = []

    def set_threats(self, positions: List[np.ndarray]):
        self._threat_positions = positions

    def _should_upgrade(self, state: SimState) -> FidelityLevel:
        if not self.auto_switch:
            return self.current_level
        speed = np.linalg.norm(state.velocity)
        altitude = state.position[2]
        min_threat_dist = float('inf')
        for tp in self._threat_positions:
            d = np.linalg.norm(state.position - tp)
            min_threat_dist = min(min_threat_dist, d)

        if min_threat_dist < self._proximity_threshold or altitude < 5 or speed > 15:
            return FidelityLevel.HIGH
        elif min_threat_dist < self._proximity_threshold * 2 or speed > 8:
            return FidelityLevel.MEDIUM
        return FidelityLevel.LOW

    def step(self, state: SimState, force: np.ndarray, dt: float = 0.1) -> SimState:
        self.current_level = self._should_upgrade(state)
        self.step_count += 1

        if self.current_level == FidelityLevel.LOW:
            result = self.low.step(state, force, dt)
            compute = 0.1
        elif self.current_level == FidelityLevel.MEDIUM:
            result = self.medium.step(state, force, dt)
            compute = 0.5
        else:
            torque = self.rng.standard_normal(3) * 0.01
            result = self.high.step(state, force, torque, dt)
            compute = 2.0

        self.states.append(result)
        self.metrics.append(FidelityMetrics(
            self.current_level, compute,
            {FidelityLevel.LOW: 0.7, FidelityLevel.MEDIUM: 0.85, FidelityLevel.HIGH: 0.98}[self.current_level],
            self.step_count))
        return result

    def run(self, initial_state: SimState, force_fn: Callable,
            duration: float, dt: float = 0.1) -> List[SimState]:
        state = initial_state
        steps = int(duration / dt)
        trajectory = []
        for _ in range(steps):
            force = force_fn(state)
            state = self.step(state, force, dt)
            trajectory.append(state)
        return trajectory

    def summary(self) -> Dict:
        level_counts = {}
        for m in self.metrics:
            level_counts[m.level.value] = level_counts.get(m.level.value, 0) + 1
        return {
            "total_steps": self.step_count,
            "level_distribution": level_counts,
            "avg_compute_ms": round(float(np.mean([m.compute_time_ms for m in self.metrics])), 3) if self.metrics else 0,
            "avg_accuracy": round(float(np.mean([m.accuracy_score for m in self.metrics])), 4) if self.metrics else 0,
        }
