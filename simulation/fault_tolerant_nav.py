"""
Phase 512: Fault-Tolerant Navigation
센서 퓨전 기반 내결함성 항법, IMU/GPS/비전 삼중 중복.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class NavSensor(Enum):
    GPS = "gps"
    IMU = "imu"
    VISION = "vision"
    BAROMETER = "barometer"
    MAGNETOMETER = "magnetometer"
    LIDAR = "lidar"


class NavHealth(Enum):
    NOMINAL = "nominal"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class SensorState:
    sensor: NavSensor
    health: NavHealth
    position_est: np.ndarray
    velocity_est: np.ndarray
    covariance: np.ndarray
    confidence: float
    timestamp: float


@dataclass
class NavSolution:
    position: np.ndarray
    velocity: np.ndarray
    heading_deg: float
    confidence: float
    sensors_used: List[NavSensor]
    integrity: float


class ExtendedKalmanFilter:
    """EKF for sensor fusion navigation."""

    def __init__(self, dim: int = 6, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.dim = dim
        self.x = np.zeros(dim)  # [px, py, pz, vx, vy, vz]
        self.P = np.eye(dim) * 10.0
        self.Q = np.eye(dim) * 0.01  # process noise
        self.F = np.eye(dim)  # state transition
        self.F[:3, 3:6] = np.eye(3) * 0.1  # dt

    def predict(self, dt: float = 0.1):
        self.F[:3, 3:6] = np.eye(3) * dt
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q * dt

    def update(self, z: np.ndarray, H: np.ndarray, R: np.ndarray):
        y = z - H @ self.x
        S = H @ self.P @ H.T + R
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            return
        self.x = self.x + K @ y
        self.P = (np.eye(self.dim) - K @ H) @ self.P

    def state(self) -> Tuple[np.ndarray, np.ndarray]:
        return self.x[:3].copy(), self.x[3:6].copy()


class SensorVoter:
    """Triple-redundancy sensor voting."""

    def __init__(self):
        self.vote_log: List[Dict] = []

    def vote(self, states: List[SensorState]) -> Tuple[np.ndarray, float]:
        if not states:
            return np.zeros(3), 0.0
        healthy = [s for s in states if s.health != NavHealth.FAILED]
        if not healthy:
            healthy = states  # use all as fallback

        weights = np.array([s.confidence for s in healthy])
        weights /= weights.sum() + 1e-10
        pos = sum(w * s.position_est for w, s in zip(weights, healthy))

        spread = np.std([s.position_est for s in healthy], axis=0)
        integrity = max(0, 1 - np.linalg.norm(spread) / 10)

        self.vote_log.append({"n_sensors": len(healthy), "integrity": round(integrity, 4)})
        return pos, integrity


class FaultTolerantNav:
    """Fault-tolerant navigation system with sensor fusion."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.ekf = ExtendedKalmanFilter(seed=seed)
        self.voter = SensorVoter()
        self.sensor_health: Dict[NavSensor, NavHealth] = {
            s: NavHealth.NOMINAL for s in NavSensor}
        self.solutions: List[NavSolution] = []
        self.true_pos = np.array([0.0, 0.0, 50.0])
        self.true_vel = np.array([2.0, 1.0, 0.0])

    def _simulate_sensor(self, sensor: NavSensor, dt: float) -> SensorState:
        health = self.sensor_health[sensor]
        noise_map = {
            NavSensor.GPS: 2.0, NavSensor.IMU: 0.5, NavSensor.VISION: 1.0,
            NavSensor.BAROMETER: 3.0, NavSensor.MAGNETOMETER: 5.0, NavSensor.LIDAR: 0.3,
        }
        noise = noise_map.get(sensor, 1.0)
        if health == NavHealth.DEGRADED:
            noise *= 5
        elif health == NavHealth.FAILED:
            noise *= 50

        pos_est = self.true_pos + self.rng.standard_normal(3) * noise
        vel_est = self.true_vel + self.rng.standard_normal(3) * noise * 0.3
        cov = np.eye(3) * noise ** 2
        conf = max(0.1, 1.0 - noise / 20)
        if health == NavHealth.FAILED:
            conf = 0.05
        return SensorState(sensor, health, pos_est, vel_est, cov, conf, dt)

    def inject_fault(self, sensor: NavSensor, health: NavHealth):
        self.sensor_health[sensor] = health

    def step(self, dt: float = 0.1) -> NavSolution:
        self.true_pos += self.true_vel * dt + self.rng.standard_normal(3) * 0.01
        self.true_vel += self.rng.standard_normal(3) * 0.05

        self.ekf.predict(dt)
        states = []
        for sensor in [NavSensor.GPS, NavSensor.IMU, NavSensor.VISION]:
            s = self._simulate_sensor(sensor, dt)
            states.append(s)
            if s.health != NavHealth.FAILED:
                H = np.zeros((3, 6))
                H[:3, :3] = np.eye(3)
                R = s.covariance
                self.ekf.update(s.position_est, H, R)

        pos, vel = self.ekf.state()
        voted_pos, integrity = self.voter.vote(states)
        used = [s.sensor for s in states if s.health != NavHealth.FAILED]
        heading = float(np.degrees(np.arctan2(vel[1], vel[0]))) % 360
        confidence = integrity * len(used) / 3

        sol = NavSolution(pos, vel, round(heading, 1), round(confidence, 4),
                         used, round(integrity, 4))
        self.solutions.append(sol)
        return sol

    def run(self, duration: float = 10, dt: float = 0.1) -> List[NavSolution]:
        sols = []
        for _ in np.arange(0, duration, dt):
            sols.append(self.step(dt))
        return sols

    def summary(self) -> Dict:
        return {
            "solutions": len(self.solutions),
            "avg_confidence": round(np.mean([s.confidence for s in self.solutions]), 4) if self.solutions else 0,
            "avg_integrity": round(np.mean([s.integrity for s in self.solutions]), 4) if self.solutions else 0,
            "failed_sensors": sum(1 for h in self.sensor_health.values() if h == NavHealth.FAILED),
        }
