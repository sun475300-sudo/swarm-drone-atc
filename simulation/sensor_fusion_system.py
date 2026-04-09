"""
Phase 463: Sensor Fusion System for Multi-Sensor Integration
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class SensorData:
    sensor_type: str
    data: np.ndarray
    timestamp: float
    accuracy: float


class SensorFusionSystem:
    def __init__(self):
        self.sensor_buffers: Dict[str, List[SensorData]] = {}
        self.fused_state = np.zeros(12)

    def add_sensor_data(self, data: SensorData):
        if data.sensor_type not in self.sensor_buffers:
            self.sensor_buffers[data.sensor_type] = []

        self.sensor_buffers[data.sensor_type].append(data)

        if len(self.sensor_buffers[data.sensor_type]) > 100:
            self.sensor_buffers[data.sensor_type].pop(0)

    def fuse(self) -> np.ndarray:
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
