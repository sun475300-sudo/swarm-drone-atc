"""
Phase 424: Multi-Modal Fusion for Sensor Integration
"""

import time
from dataclasses import dataclass
from enum import Enum

import numpy as np


class SensorType(Enum):
    """``SensorType`` 관련 기능을 제공한다."""
    CAMERA = "camera"
    LIDAR = "lidar"
    RADAR = "radar"
    GPS = "gps"
    IMU = "imu"
    SONAR = "sonar"


@dataclass
class SensorReading:
    """``SensorReading`` 관련 기능을 제공한다."""
    sensor_type: SensorType
    data: np.ndarray
    timestamp: float
    confidence: float


@dataclass
class FusionResult:
    """``FusionResult`` 데이터를 표현한다."""
    fused_state: np.ndarray
    confidence: float
    sources_used: list[SensorType]
    timestamp: float


class MultiModalFusion:
    """``MultiModalFusion`` 관련 기능을 제공한다."""
    def __init__(self, fusion_method: str = "kalman"):
        """인스턴스를 초기화한다."""
        self.fusion_method = fusion_method
        self.sensor_readings: dict[SensorType, list[SensorReading]] = {
            st: [] for st in SensorType
        }
        self.state_estimate = np.zeros(6)
        self.covariance = np.eye(6)

    def add_reading(self, reading: SensorReading):
        """`reading` 항목을 추가한다."""
        self.sensor_readings[reading.sensor_type].append(reading)

        max_readings = 100
        if len(self.sensor_readings[reading.sensor_type]) > max_readings:
            self.sensor_readings[reading.sensor_type].pop(0)

    def fuse(self) -> FusionResult:
        """``fuse`` 동작을 수행한다."""
        sources_used = []
        weighted_sum = np.zeros(6)
        total_weight = 0.0

        for sensor_type, readings in self.sensor_readings.items():
            if not readings:
                continue

            latest = readings[-1]
            weight = latest.confidence

            weighted_sum += latest.data * weight
            total_weight += weight
            sources_used.append(sensor_type)

        fused_state = weighted_sum / total_weight if total_weight > 0 else self.state_estimate

        confidence = min(total_weight / len(SensorType), 1.0)

        if self.fusion_method == "kalman":
            self._kalman_update(fused_state, confidence)
        else:
            self.state_estimate = fused_state

        return FusionResult(
            fused_state=fused_state,
            confidence=confidence,
            sources_used=sources_used,
            timestamp=time.time(),
        )

    def _kalman_update(self, measurement: np.ndarray, confidence: float):
        noise = 1.0 - confidence

        kalman_gain = self.covariance @ np.linalg.inv(
            self.covariance + noise * np.eye(6)
        )

        self.state_estimate = self.state_estimate + kalman_gain @ (
            measurement - self.state_estimate
        )

        self.covariance = (np.eye(6) - kalman_gain) @ self.covariance

    def get_state_estimate(self) -> np.ndarray:
        """`state estimate` 정보를 조회한다."""
        return self.state_estimate.copy()

    def calibrate_sensor(self, sensor_type: SensorType, calibration_data: np.ndarray):
        """``calibrate_sensor`` 동작을 수행한다."""
        pass
