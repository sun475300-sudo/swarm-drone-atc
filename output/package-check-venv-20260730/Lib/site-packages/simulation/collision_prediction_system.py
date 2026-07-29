"""
Phase 438: Collision Prediction System with Trajectory Forecasting
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class DroneState:
    """``DroneState`` 데이터를 표현한다."""
    drone_id: str
    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray
    timestamp: float


@dataclass
class CollisionWarning:
    """``CollisionWarning`` 관련 기능을 제공한다."""
    drone1_id: str
    drone2_id: str
    time_to_collision: float
    distance: float
    severity: str


class CollisionPredictionSystem:
    """``CollisionPredictionSystem`` 역할을 담당한다."""
    def __init__(self, prediction_horizon: float = 5.0):
        """인스턴스를 초기화한다."""
        self.prediction_horizon = prediction_horizon

    def predict_trajectory(
        self,
        state: DroneState,
        steps: int = 50,
    ) -> np.ndarray:
        """`trajectory` 결과를 계산하거나 판정한다."""
        dt = self.prediction_horizon / steps

        positions = [state.position.copy()]

        pos = state.position.copy()
        vel = state.velocity.copy()
        acc = state.acceleration.copy()

        for _ in range(steps):
            vel += acc * dt
            pos += vel * dt
            positions.append(pos.copy())

        return np.array(positions)

    def detect_collision(
        self,
        states: list[DroneState],
    ) -> list[CollisionWarning]:
        """`collision` 결과를 계산하거나 판정한다."""
        warnings = []

        for i in range(len(states)):
            for j in range(i + 1, len(states)):
                traj1 = self.predict_trajectory(states[i])
                traj2 = self.predict_trajectory(states[j])

                distances = np.linalg.norm(traj1 - traj2, axis=1)
                min_dist = np.min(distances)

                if min_dist < 5.0:
                    ttc = np.argmin(distances) * (self.prediction_horizon / 50)

                    severity = (
                        "critical"
                        if min_dist < 2
                        else "high"
                        if min_dist < 5
                        else "medium"
                    )

                    warnings.append(
                        CollisionWarning(
                            states[i].drone_id,
                            states[j].drone_id,
                            ttc,
                            float(min_dist),
                            severity,
                        )
                    )

        return warnings

    def recommend_maneuver(
        self,
        warning: CollisionWarning,
        current_state: DroneState,
    ) -> np.ndarray:
        """``recommend_maneuver`` 동작을 수행한다."""
        escape_direction = np.random.randn(3)
        escape_direction /= np.linalg.norm(escape_direction)

        return escape_direction * 10.0
