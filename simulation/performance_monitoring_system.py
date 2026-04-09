"""
Phase 448: Performance Monitoring System for Swarm Operations
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class PerformanceMetric:
    drone_id: str
    cpu_percent: float
    memory_percent: float
    temperature_c: float
    timestamp: float


class PerformanceMonitoringSystem:
    def __init__(self):
        self.metrics_history: Dict[str, List[PerformanceMetric]] = {}
        self.alerts: List[Dict] = []

    def record_metric(self, metric: PerformanceMetric):
        if metric.drone_id not in self.metrics_history:
            self.metrics_history[metric.drone_id] = []
        self.metrics_history[metric.drone_id].append(metric)

        if metric.cpu_percent > 90:
            self.alerts.append(
                {
                    "drone_id": metric.drone_id,
                    "type": "high_cpu",
                    "value": metric.cpu_percent,
                    "timestamp": time.time(),
                }
            )

    def get_average_cpu(self, drone_id: str, window_sec: float = 60) -> float:
        if drone_id not in self.metrics_history:
            return 0.0

        now = time.time()
        recent = [
            m for m in self.metrics_history[drone_id] if now - m.timestamp <= window_sec
        ]

        return np.mean([m.cpu_percent for m in recent]) if recent else 0.0

    def detect_anomaly(self, drone_id: str) -> bool:
        avg_cpu = self.get_average_cpu(drone_id)
        return avg_cpu > 80
