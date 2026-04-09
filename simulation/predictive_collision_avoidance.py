"""Phase 286: Predictive Collision Avoidance — 예측적 충돌 회피 시스템.

확장 칼만 필터 기반 궤적 예측, 시간-공간 충돌 확률 계산,
다중 에이전트 ORCA(Optimal Reciprocal Collision Avoidance) 구현.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class TrajectoryPrediction:
    drone_id: str
    positions: List[np.ndarray]  # future positions
    velocities: List[np.ndarray]
    timestamps: List[float]
    confidence: List[float]


@dataclass
class CollisionRisk:
    drone_a: str
    drone_b: str
    min_distance: float
    time_to_closest: float
    probability: float
    risk_level: str  # "none", "low", "medium", "high", "critical"


@dataclass
class AvoidanceManeuver:
    drone_id: str
    velocity_adjustment: np.ndarray
    start_time: float
    duration: float
    priority: int = 0


class ExtendedKalmanPredictor:
    """확장 칼만 필터 기반 궤적 예측기."""

    def __init__(self, dt: float = 0.1, process_noise: float = 0.5):
        self.dt = dt
        self.process_noise = process_noise

    def predict_trajectory(
        self, position: np.ndarray, velocity: np.ndarray,
        acceleration: Optional[np.ndarray] = None, horizon_sec: float = 5.0,
    ) -> Tuple[List[np.ndarray], List[np.ndarray], List[float]]:
        if acceleration is None:
            acceleration = np.zeros(3)
        n_steps = int(horizon_sec / self.dt)
        positions, velocities, confidences = [], [], []
        pos = position.copy()
        vel = velocity.copy()
        confidence = 1.0
        for i in range(n_steps):
            vel = vel + acceleration * self.dt
            pos = pos + vel * self.dt
            confidence *= (1.0 - self.process_noise * self.dt * 0.1)
            positions.append(pos.copy())
            velocities.append(vel.copy())
            confidences.append(max(0.1, confidence))
        return positions, velocities, confidences


class ORCAVelocityPlanner:
    """ORCA 기반 속도 계획기."""

    def __init__(self, tau: float = 3.0, safety_radius: float = 5.0):
        self.tau = tau
        self.safety_radius = safety_radius

    def compute_orca_velocity(
        self, agent_pos: np.ndarray, agent_vel: np.ndarray, agent_radius: float,
        neighbors: List[Tuple[np.ndarray, np.ndarray, float]], preferred_vel: np.ndarray,
        max_speed: float = 15.0,
    ) -> np.ndarray:
        orca_planes = []
        for nb_pos, nb_vel, nb_radius in neighbors:
            rel_pos = nb_pos - agent_pos
            rel_vel = agent_vel - nb_vel
            dist = np.linalg.norm(rel_pos)
            combined_radius = agent_radius + nb_radius + self.safety_radius
            if dist < 0.01:
                continue
            if dist < combined_radius:
                # Already too close — push away
                direction = rel_pos / dist
                orca_planes.append((-direction, np.dot(-direction, rel_vel)))
            else:
                # Project to velocity obstacle
                leg = np.sqrt(max(0, dist * dist - combined_radius * combined_radius))
                direction = rel_pos / dist
                # Normal to half-plane
                n = np.array([-direction[1], direction[0], 0]) if len(direction) >= 3 else np.array([-direction[1], direction[0]])
                if len(n) < 3:
                    n = np.append(n, 0)
                u = rel_vel - direction * combined_radius / self.tau
                orca_planes.append((n / max(np.linalg.norm(n), 1e-6), np.dot(n, u) * 0.5))

        # Solve: find velocity closest to preferred that satisfies all half-planes
        new_vel = preferred_vel.copy()
        for normal, offset in orca_planes:
            proj = np.dot(new_vel, normal[:3]) - offset
            if proj < 0:
                new_vel = new_vel - proj * normal[:3]
        speed = np.linalg.norm(new_vel)
        if speed > max_speed:
            new_vel = new_vel / speed * max_speed
        return new_vel


class PredictiveCollisionAvoidance:
    """예측적 충돌 회피 시스템.

    - EKF 궤적 예측
    - 시공간 충돌 확률 계산
    - ORCA 기반 회피 속도 계산
    - 다중 에이전트 동시 회피
    """

    def __init__(self, safety_distance: float = 10.0, prediction_horizon: float = 5.0, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.safety_distance = safety_distance
        self.prediction_horizon = prediction_horizon
        self._predictor = ExtendedKalmanPredictor()
        self._orca = ORCAVelocityPlanner(safety_radius=safety_distance * 0.3)
        self._drone_states: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}  # pos, vel
        self._predictions: Dict[str, TrajectoryPrediction] = {}
        self._risks: List[CollisionRisk] = []
        self._maneuvers: Dict[str, AvoidanceManeuver] = {}
        self._history: List[dict] = []

    def update_state(self, drone_id: str, position: np.ndarray, velocity: np.ndarray):
        self._drone_states[drone_id] = (position.copy(), velocity.copy())

    def predict_all(self) -> Dict[str, TrajectoryPrediction]:
        self._predictions.clear()
        for did, (pos, vel) in self._drone_states.items():
            positions, velocities, confidences = self._predictor.predict_trajectory(
                pos, vel, horizon_sec=self.prediction_horizon
            )
            timestamps = [i * self._predictor.dt for i in range(len(positions))]
            pred = TrajectoryPrediction(
                drone_id=did, positions=positions, velocities=velocities,
                timestamps=timestamps, confidence=confidences,
            )
            self._predictions[did] = pred
        return self._predictions

    def assess_risks(self) -> List[CollisionRisk]:
        self._risks.clear()
        drone_ids = list(self._predictions.keys())
        for i in range(len(drone_ids)):
            for j in range(i + 1, len(drone_ids)):
                a_id, b_id = drone_ids[i], drone_ids[j]
                pred_a = self._predictions[a_id]
                pred_b = self._predictions[b_id]
                min_dist = float("inf")
                min_time = 0.0
                n = min(len(pred_a.positions), len(pred_b.positions))
                for k in range(n):
                    d = np.linalg.norm(pred_a.positions[k] - pred_b.positions[k])
                    if d < min_dist:
                        min_dist = d
                        min_time = pred_a.timestamps[k]
                prob = max(0.0, 1.0 - min_dist / (self.safety_distance * 3))
                if min_dist < self.safety_distance:
                    level = "critical"
                elif min_dist < self.safety_distance * 1.5:
                    level = "high"
                elif min_dist < self.safety_distance * 2.5:
                    level = "medium"
                elif prob > 0.1:
                    level = "low"
                else:
                    level = "none"
                if level != "none":
                    risk = CollisionRisk(
                        drone_a=a_id, drone_b=b_id, min_distance=min_dist,
                        time_to_closest=min_time, probability=prob, risk_level=level,
                    )
                    self._risks.append(risk)
        return self._risks

    def compute_avoidance(self, drone_id: str, preferred_vel: Optional[np.ndarray] = None) -> Optional[AvoidanceManeuver]:
        state = self._drone_states.get(drone_id)
        if not state:
            return None
        pos, vel = state
        if preferred_vel is None:
            preferred_vel = vel.copy()
        neighbors = []
        for did, (p, v) in self._drone_states.items():
            if did != drone_id:
                neighbors.append((p, v, 2.0))  # drone radius ~2m
        if not neighbors:
            return None
        new_vel = self._orca.compute_orca_velocity(pos, vel, 2.0, neighbors, preferred_vel)
        adjustment = new_vel - vel
        if np.linalg.norm(adjustment) < 0.1:
            return None
        maneuver = AvoidanceManeuver(
            drone_id=drone_id, velocity_adjustment=adjustment,
            start_time=0.0, duration=2.0,
        )
        self._maneuvers[drone_id] = maneuver
        self._history.append({"event": "avoidance", "drone": drone_id, "adjustment_mag": float(np.linalg.norm(adjustment))})
        return maneuver

    def step(self) -> dict:
        """한 단계 실행: 예측 → 위험 평가 → 회피."""
        self.predict_all()
        risks = self.assess_risks()
        maneuvers = {}
        critical_drones = set()
        for risk in risks:
            if risk.risk_level in ("high", "critical"):
                critical_drones.add(risk.drone_a)
                critical_drones.add(risk.drone_b)
        for did in critical_drones:
            m = self.compute_avoidance(did)
            if m:
                maneuvers[did] = m
        return {"risks": len(risks), "critical_drones": len(critical_drones), "maneuvers": len(maneuvers)}

    def summary(self) -> dict:
        risk_levels = {}
        for r in self._risks:
            risk_levels[r.risk_level] = risk_levels.get(r.risk_level, 0) + 1
        return {
            "tracked_drones": len(self._drone_states),
            "predictions": len(self._predictions),
            "active_risks": len(self._risks),
            "risk_levels": risk_levels,
            "active_maneuvers": len(self._maneuvers),
            "history_events": len(self._history),
        }
