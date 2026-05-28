"""
Phase 448: Performance Monitoring System for Swarm Operations
"""

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class PerformanceMetric:
    """``PerformanceMetric`` 관련 기능을 제공한다."""
    drone_id: str
    cpu_percent: float
    memory_percent: float
    temperature_c: float
    timestamp: float


class PerformanceMonitoringSystem:
    """``PerformanceMonitoringSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.metrics_history: dict[str, list[PerformanceMetric]] = {}
        self.alerts: list[dict] = []

    def record_metric(self, metric: PerformanceMetric):
        """`metric` 정보를 기록한다."""
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
        """`average cpu` 정보를 조회한다."""
        if drone_id not in self.metrics_history:
            return 0.0

        now = time.time()
        recent = [
            m for m in self.metrics_history[drone_id] if now - m.timestamp <= window_sec
        ]

        return np.mean([m.cpu_percent for m in recent]) if recent else 0.0

    def detect_anomaly(self, drone_id: str) -> bool:
        """`anomaly` 결과를 계산하거나 판정한다."""
        avg_cpu = self.get_average_cpu(drone_id)
        return avg_cpu > 80
