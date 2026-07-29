"""
Phase 463: Sensor Fusion System for Multi-Sensor Integration
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class SensorData:
    """``SensorData`` 관련 기능을 제공한다."""
    sensor_type: str
    data: np.ndarray
    timestamp: float
    accuracy: float


class SensorFusionSystem:
    """``SensorFusionSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.sensor_buffers: dict[str, list[SensorData]] = {}
        self.fused_state = np.zeros(12)

    def add_sensor_data(self, data: SensorData):
        """`sensor data` 항목을 추가한다."""
        if data.sensor_type not in self.sensor_buffers:
            self.sensor_buffers[data.sensor_type] = []

        self.sensor_buffers[data.sensor_type].append(data)

        if len(self.sensor_buffers[data.sensor_type]) > 100:
            self.sensor_buffers[data.sensor_type].pop(0)

    def fuse(self) -> np.ndarray:
        """``fuse`` 동작을 수행한다."""
        total_weight = 0
        weighted_sum = np.zeros(12)

        for sensor_type, buffer in self.sensor_buffers.items():
            if not buffer:
                continue

            latest = buffer[-1]
            weight = latest.accuracy

            if sensor_type == "gps":
                weighted_sum[:3] += latest.data[:3] * weight
                total_weight += weight
            elif sensor_type == "imu":
                weighted_sum[3:9] += latest.data * weight
                total_weight += weight
            elif sensor_type == "barometer":
                weighted_sum[9:] += latest.data * weight
                total_weight += weight

        if total_weight > 0:
            self.fused_state = weighted_sum / total_weight

        return self.fused_state
