"""
Phase 480: Predictive Swarm Behavior
AI-driven prediction of swarm behavior patterns and emergent phenomena.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any


class BehaviorPattern(Enum):
    """Swarm behavior patterns."""

    FLOCKING = auto()
    CLUSTERING = auto()
    DISPERSING = auto()
    MIGRATING = auto()
    FORAGING = auto()
    SWARMING = auto()


@dataclass
class BehaviorPrediction:
    """Behavior prediction result."""

    predicted_pattern: BehaviorPattern
    confidence: float
    time_horizon_s: float
    affected_drones: List[str]
    trigger_conditions: Dict[str, Any]


@dataclass
class SwarmTrajectory:
    """Predicted swarm trajectory."""

    centroid_trajectory: np.ndarray
    spread_trajectory: np.ndarray
    confidence: float
    time_steps: int


class PredictiveSwarmBehavior:
    """Predictive swarm behavior engine."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.positions: Dict[str, np.ndarray] = {}
        self.velocities: Dict[str, np.ndarray] = {}
        self.history: List[Dict[str, np.ndarray]] = []
        self.predictions: List[BehaviorPrediction] = []
        self._init_swarm()

    def _init_swarm(self) -> None:
        for i in range(self.n_drones):
            did = f"drone_{i}"
            self.positions[did] = self.rng.uniform(-100, 100, size=3)
            self.velocities[did] = self.rng.uniform(-5, 5, size=3)

    def update_state(
        self, positions: Dict[str, np.ndarray], velocities: Dict[str, np.ndarray]
    ) -> None:
        self.positions.update(positions)
        self.velocities.update(velocities)
        self.history.append(
            {"positions": positions.copy(), "velocities": velocities.copy()}
        )

    def _compute_centroid(self) -> np.ndarray:
        pos = np.array(list(self.positions.values()))
        return pos.mean(axis=0)

    def _compute_spread(self) -> float:
        centroid = self._compute_centroid()
        pos = np.array(list(self.positions.values()))
        return float(np.mean(np.linalg.norm(pos - centroid, axis=1)))

    def _compute_alignment(self) -> float:
        vels = np.array(list(self.velocities.values()))
        norms = np.linalg.norm(vels, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = vels / norms
        return float(np.mean(np.abs(normalized @ normalized.T)))

    def predict_behavior(self, horizon_s: float = 10.0) -> BehaviorPrediction:
        spread = self._compute_spread()
        alignment = self._compute_alignment()
        if spread < 20 and alignment > 0.8:
            pattern = BehaviorPattern.FLOCKING
            confidence = 0.9
        elif spread < 30:
            pattern = BehaviorPattern.CLUSTERING
            confidence = 0.8
        elif spread > 80:
            pattern = BehaviorPattern.DISPERSING
            confidence = 0.7
        else:
            pattern = BehaviorPattern.MIGRATING
            confidence = 0.6
        prediction = BehaviorPrediction(
            pattern,
            confidence,
            horizon_s,
            list(self.positions.keys()),
            {"spread": spread, "alignment": alignment},
        )
        self.predictions.append(prediction)
        return prediction

    def predict_trajectory(self, steps: int = 100, dt: float = 0.1) -> SwarmTrajectory:
        centroid = self._compute_centroid()
        vel_mean = np.mean(list(self.velocities.values()), axis=0)
        centroids = np.zeros((steps, 3))
        spreads = np.zeros(steps)
        for i in range(steps):
            centroid += vel_mean * dt
            centroids[i] = centroid
            spreads[i] = self._compute_spread() + self.rng.uniform(-1, 1)
        return SwarmTrajectory(centroids, spreads, 0.8, steps)

    def detect_anomaly(self) -> Dict[str, Any]:
        if len(self.history) < 5:
            return {"anomaly": False}
        recent_spreads = [
            self._compute_spread() for _ in range(min(5, len(self.history)))
        ]
        spread_change = (
            abs(np.diff(recent_spreads).mean()) if len(recent_spreads) > 1 else 0
        )
        anomaly = spread_change > 10
        return {"anomaly": anomaly, "spread_change": spread_change}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "n_drones": self.n_drones,
            "centroid": self._compute_centroid().tolist(),
            "spread": self._compute_spread(),
            "alignment": self._compute_alignment(),
            "predictions": len(self.predictions),
            "history_length": len(self.history),
        }


if __name__ == "__main__":
    predictor = PredictiveSwarmBehavior(n_drones=10, seed=42)
    prediction = predictor.predict_behavior()
    trajectory = predictor.predict_trajectory(steps=50)
    print(
        f"Prediction: {prediction.predicted_pattern.name} ({prediction.confidence:.2f})"
    )
    print(f"Trajectory steps: {trajectory.time_steps}")
    print(f"Stats: {predictor.get_stats()}")
