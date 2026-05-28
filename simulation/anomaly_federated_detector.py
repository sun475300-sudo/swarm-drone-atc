"""
Phase 429: Anomaly Federated Detector for Cross-Fleet Learning
"""

import time
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class AnomalyModel:
    """``AnomalyModel`` 관련 기능을 제공한다."""
    model_id: str
    thresholds: dict[str, float]
    accuracy: float
    trained_at: float


@dataclass
class AnomalyReport:
    """``AnomalyReport`` 관련 기능을 제공한다."""
    drone_id: str
    anomaly_type: str
    severity: str
    confidence: float
    timestamp: float


class AnomalyFederatedDetector:
    """``AnomalyFederatedDetector`` 관련 기능을 제공한다."""
    def __init__(self, detector_id: str):
        """인스턴스를 초기화한다."""
        self.detector_id = detector_id

        self.local_models: dict[str, AnomalyModel] = {}
        self.global_thresholds: dict[str, float] = {}

        self.anomaly_history: list[AnomalyReport] = []

        self._initialize_baseline()

    def _initialize_baseline(self):
        self.global_thresholds = {
            "velocity": 30.0,
            "battery_drain": 5.0,
            "position_deviation": 50.0,
            "communication_gap": 10.0,
        }

    def train_local_model(self, drone_id: str, data: np.ndarray, labels: np.ndarray):
        """``train_local_model`` 동작을 수행한다."""
        model = AnomalyModel(
            model_id=f"model_{drone_id}_{int(time.time())}",
            thresholds=self.global_thresholds.copy(),
            accuracy=np.random.uniform(0.85, 0.98),
            trained_at=time.time(),
        )

        self.local_models[drone_id] = model

    def detect_anomaly(
        self, drone_id: str, metrics: dict[str, float]
    ) -> AnomalyReport | None:
        """`anomaly` 결과를 계산하거나 판정한다."""
        thresholds = self.local_models[drone_id].thresholds if drone_id in self.local_models else self.global_thresholds

        anomalies = []

        for metric_name, value in metrics.items():
            threshold = thresholds.get(metric_name, 100.0)

            if abs(value) > threshold:
                severity = "high" if abs(value) > threshold * 2 else "medium"
                confidence = min(abs(value) / threshold, 1.0)

                anomalies.append(
                    {
                        "metric": metric_name,
                        "value": value,
                        "threshold": threshold,
                        "severity": severity,
                        "confidence": confidence,
                    }
                )

        if not anomalies:
            return None

        worst = max(anomalies, key=lambda a: a["confidence"])

        report = AnomalyReport(
            drone_id=drone_id,
            anomaly_type=worst["metric"],
            severity=worst["severity"],
            confidence=worst["confidence"],
            timestamp=time.time(),
        )

        self.anomaly_history.append(report)

        return report

    def federated_update(self, updates: list[dict]) -> dict[str, float]:
        """``federated_update`` 동작을 수행한다."""
        if not updates:
            return self.global_thresholds

        aggregated = {}

        for key in self.global_thresholds:
            values = [u.get(key, self.global_thresholds[key]) for u in updates]
            aggregated[key] = np.mean(values)

        self.global_thresholds = aggregated

        return aggregated

    def get_anomaly_statistics(self) -> dict[str, Any]:
        """`anomaly statistics` 정보를 조회한다."""
        if not self.anomaly_history:
            return {"total_anomalies": 0}

        severity_counts = {}
        for report in self.anomaly_history:
            severity_counts[report.severity] = (
                severity_counts.get(report.severity, 0) + 1
            )

        return {
            "total_anomalies": len(self.anomaly_history),
            "severity_counts": severity_counts,
            "avg_confidence": np.mean([r.confidence for r in self.anomaly_history]),
        }
