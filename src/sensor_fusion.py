"""
Multi-Sensor Fusion for Drone State Estimation
================================================
Kalman filter and sensor fusion combining RF, YOLO, and RemoteID measurements.

Classes:
    SensorMeasurement  — Single measurement from a sensor
    FusedState        — Fused state estimation result
    KalmanFilter      — 6-state Kalman filter (pos_x, pos_y, pos_z, vel_x, vel_y, vel_z)
    SensorFusion      — Multi-sensor fusion engine
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import numpy as np


class SensorType(Enum):
    """Enumeration of sensor types."""
    RF = "rf"
    YOLO = "yolo"
    REMOTE_ID = "remote_id"


@dataclass
class SensorMeasurement:
    """
    Single measurement from a sensor.

    Attributes:
        sensor_type: Type of sensor (RF, YOLO, RemoteID)
        position: Measured position (x, y, z)
        covariance: Measurement uncertainty (standard deviation in meters)
        timestamp: Measurement timestamp (seconds)
        confidence: Sensor confidence (0-1)
    """
    sensor_type: SensorType
    position: np.ndarray
    covariance: float  # Standard deviation in meters
    timestamp: float = 0.0
    confidence: float = 1.0

    def __post_init__(self):
        """Ensure position is numpy array."""
        self.position = np.asarray(self.position, dtype=np.float64)
        if len(self.position) == 2:
            self.position = np.append(self.position, 0.0)


@dataclass
class FusedState:
    """
    Fused state estimation result.

    Attributes:
        position: Fused position (x, y, z)
        velocity: Fused velocity (vx, vy, vz)
        covariance: Estimation uncertainty (6x6 matrix)
        confidence_score: Combined confidence (0-1)
        num_sensors: Number of sensors used in fusion
        timestamp: Measurement timestamp
    """
    position: np.ndarray
    velocity: np.ndarray
    covariance: np.ndarray
    confidence_score: float
    num_sensors: int
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "position": self.position.tolist(),
            "velocity": self.velocity.tolist(),
            "covariance": self.covariance.tolist(),
            "confidence_score": self.confidence_score,
            "num_sensors": self.num_sensors,
            "timestamp": self.timestamp,
        }


class KalmanFilter:
    """
    6-state Kalman filter for drone state estimation.

    State vector: [pos_x, pos_y, pos_z, vel_x, vel_y, vel_z]

    Attributes:
        state: Current state estimate (6,)
        covariance: State covariance matrix (6x6)
        process_noise: Process noise covariance (6x6)
        dt: Time step (seconds)
    """

    def __init__(
        self,
        initial_position: np.ndarray = None,
        initial_velocity: np.ndarray = None,
        process_noise_std: float = 0.1,
        dt: float = 0.1,
    ):
        """
        Initialize Kalman filter.

        Args:
            initial_position: Initial position estimate [x, y, z]
            initial_velocity: Initial velocity estimate [vx, vy, vz]
            process_noise_std: Standard deviation of process noise
            dt: Time step in seconds
        """
        if initial_position is None:
            initial_position = np.zeros(3, dtype=np.float64)
        if initial_velocity is None:
            initial_velocity = np.zeros(3, dtype=np.float64)

        self.dt = dt

        # State vector: [x, y, z, vx, vy, vz]
        self.state = np.zeros(6, dtype=np.float64)
        self.state[:3] = np.asarray(initial_position, dtype=np.float64)
        self.state[3:] = np.asarray(initial_velocity, dtype=np.float64)

        # State covariance (uncertainty in state estimate)
        self.covariance = np.eye(6, dtype=np.float64) * 10.0

        # Process noise covariance (uncertainty in motion model)
        q = process_noise_std ** 2
        self.process_noise = np.eye(6, dtype=np.float64) * q

        # State transition matrix (kinematic model)
        self.F = np.eye(6, dtype=np.float64)
        self.F[:3, 3:] = np.eye(3) * dt  # Position += velocity * dt

    def predict(self) -> None:
        """
        Prediction step: advance state and covariance.

        Updates state using kinematic model and adds process noise.
        """
        # x = F @ x
        self.state = self.F @ self.state

        # P = F @ P @ F^T + Q
        self.covariance = self.F @ self.covariance @ self.F.T + self.process_noise

    def update(self, measurement: np.ndarray, measurement_noise: float) -> None:
        """
        Update step: fuse measurement into state.

        Measurement is position only [x, y, z].

        Args:
            measurement: Position measurement [x, y, z]
            measurement_noise: Measurement standard deviation (meters)
        """
        measurement = np.asarray(measurement, dtype=np.float64)

        # Measurement model: observe position only
        # z = [x, y, z] (states 0, 1, 2)
        H = np.zeros((3, 6), dtype=np.float64)
        H[:3, :3] = np.eye(3)

        # Measurement noise covariance
        R = np.eye(3, dtype=np.float64) * (measurement_noise ** 2)

        # Innovation (measurement residual)
        innovation = measurement - (H @ self.state)

        # Innovation covariance
        S = H @ self.covariance @ H.T + R

        # Kalman gain
        K = self.covariance @ H.T @ np.linalg.inv(S)

        # Update state estimate
        self.state = self.state + K @ innovation

        # Update covariance estimate
        I = np.eye(6, dtype=np.float64)
        self.covariance = (I - K @ H) @ self.covariance

    def get_position(self) -> np.ndarray:
        """Get current position estimate."""
        return self.state[:3].copy()

    def get_velocity(self) -> np.ndarray:
        """Get current velocity estimate."""
        return self.state[3:].copy()


class SensorFusion:
    """
    Multi-sensor fusion engine combining RF, YOLO, and RemoteID.

    Each sensor has different characteristics:
    - RF (Received Signal Strength):      σ = 5m (noisy, long range)
    - YOLO (Vision-based detection):     σ = 2m (moderate, line-of-sight)
    - RemoteID (Direct broadcast):       σ = 1m (most accurate, if available)

    Attributes:
        kalman_filters: Dict of Kalman filters per drone_id
        outlier_threshold: Mahalanobis distance threshold (3σ)
    """

    def __init__(self, outlier_threshold: float = 3.0):
        """
        Initialize sensor fusion engine.

        Args:
            outlier_threshold: Mahalanobis distance threshold for outlier rejection
        """
        self.kalman_filters: dict[int, KalmanFilter] = {}
        self.outlier_threshold = outlier_threshold

    def _mahalanobis_distance(
        self,
        measurement: np.ndarray,
        predicted_position: np.ndarray,
        covariance: np.ndarray,
    ) -> float:
        """
        Compute Mahalanobis distance for outlier detection.

        Args:
            measurement: Measured position
            predicted_position: Predicted position from Kalman filter
            covariance: State covariance matrix (6x6)

        Returns:
            Mahalanobis distance (dimensionless)
        """
        # Position portion of covariance (3x3)
        pos_cov = covariance[:3, :3]

        # Residual
        residual = measurement - predicted_position

        # Mahalanobis distance
        try:
            inv_cov = np.linalg.inv(pos_cov + np.eye(3) * 1e-6)
            distance = float(
                np.sqrt(residual @ inv_cov @ residual)
            )
        except np.linalg.LinAlgError:
            distance = float('inf')

        return distance

    def fuse(
        self,
        drone_id: int,
        measurements: list[SensorMeasurement],
        dt: float = 0.1,
    ) -> FusedState:
        """
        Fuse multiple sensor measurements into a single state estimate.

        Process:
        1. Get or create Kalman filter for this drone
        2. Prediction step (motion model)
        3. Filter outliers using Mahalanobis distance
        4. Update with valid measurements
        5. Compute confidence score

        Args:
            drone_id: Unique drone identifier
            measurements: List of sensor measurements
            dt: Time step in seconds

        Returns:
            FusedState with position, velocity, covariance, confidence
        """
        # Get or create Kalman filter
        if drone_id not in self.kalman_filters:
            if measurements:
                # Initialize with first measurement
                initial_pos = measurements[0].position
                self.kalman_filters[drone_id] = KalmanFilter(
                    initial_position=initial_pos,
                    dt=dt,
                )
            else:
                self.kalman_filters[drone_id] = KalmanFilter(dt=dt)

        kf = self.kalman_filters[drone_id]
        kf.dt = dt

        # Prediction step
        kf.predict()

        # Filter outliers and collect valid measurements
        valid_measurements = []
        sensor_types_used = set()

        for measurement in measurements:
            # Mahalanobis distance-based outlier rejection
            maha_dist = self._mahalanobis_distance(
                measurement.position,
                kf.get_position(),
                kf.covariance,
            )

            if maha_dist < self.outlier_threshold:
                valid_measurements.append(measurement)
                sensor_types_used.add(measurement.sensor_type)

        # Update with valid measurements
        if valid_measurements:
            # Average position of valid measurements (weighted by confidence)
            total_confidence = sum(m.confidence for m in valid_measurements)
            if total_confidence > 0:
                weighted_pos = np.zeros(3, dtype=np.float64)
                for m in valid_measurements:
                    weight = m.confidence / total_confidence
                    weighted_pos += m.position * weight

                # Use weighted measurement noise
                avg_noise = np.mean([m.covariance for m in valid_measurements])
                kf.update(weighted_pos, avg_noise)

        # Compute confidence score
        # Based on: number of agreeing sensors, measurement quality, filter certainty
        num_sensors = len(valid_measurements)
        sensor_bonus = min(1.0, num_sensors / 3.0)  # 3 sensors = 100% bonus

        # Filter certainty (inverse of covariance trace)
        filter_uncertainty = float(np.trace(kf.covariance[:3, :3])) / 100.0
        filter_certainty = 1.0 / (1.0 + filter_uncertainty)

        confidence_score = (sensor_bonus + filter_certainty) / 2.0
        confidence_score = float(np.clip(confidence_score, 0.0, 1.0))

        # Build fused state
        timestamp = valid_measurements[0].timestamp if valid_measurements else 0.0

        return FusedState(
            position=kf.get_position(),
            velocity=kf.get_velocity(),
            covariance=kf.covariance.copy(),
            confidence_score=confidence_score,
            num_sensors=num_sensors,
            timestamp=timestamp,
        )

    def get_filter(self, drone_id: int) -> Optional[KalmanFilter]:
        """Get Kalman filter for a drone, if it exists."""
        return self.kalman_filters.get(drone_id)

    def reset(self) -> None:
        """Reset all Kalman filters."""
        self.kalman_filters.clear()
