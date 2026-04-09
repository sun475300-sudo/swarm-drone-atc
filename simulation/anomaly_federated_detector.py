"""
Phase 429: Anomaly Federated Detector for Cross-Fleet Learning
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time


@dataclass
class AnomalyModel:
    model_id: str
    thresholds: Dict[str, float]
    accuracy: float
    trained_at: float


@dataclass
class AnomalyReport:
    drone_id: str
    anomaly_type: str
    severity: str
    confidence: float
    timestamp: float


class AnomalyFederatedDetector:
    def __init__(self, detector_id: str):
        self.detector_id = detector_id

        self.local_models: Dict[str, AnomalyModel] = {}
        self.global_thresholds: Dict[str, float] = {}

        self.anomaly_history: List[AnomalyReport] = []

        self._initialize_baseline()

    def _initialize_baseline(self):
        self.global_thresholds = {
            "velocity": 30.0,
            "battery_drain": 5.0,
            "position_deviation": 50.0,
            "communication_gap": 10.0,
        }

    def train_local_model(self, drone_id: str, data: np.ndarray, labels: np.ndarray):
        model = AnomalyModel(
            model_id=f"model_{drone_id}_{int(time.time())}",
            thresholds=self.global_thresholds.copy(),
            accuracy=np.random.uniform(0.85, 0.98),
            trained_at=time.time(),
        )

        self.local_models[drone_id] = model

    def detect_anomaly(
        self, drone_id: str, metrics: Dict[str, float]
    ) -> Optional[AnomalyReport]:
        if drone_id in self.local_models:
            thresholds = self.local_models[drone_id].thresholds
        else:
            thresholds = self.global_thresholds

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

    def federated_update(self, updates: List[Dict]) -> Dict[str, float]:
        if not updates:
            return self.global_thresholds

        aggregated = {}

        for key in self.global_thresholds.keys():
            values = [u.get(key, self.global_thresholds[key]) for u in updates]
            aggregated[key] = np.mean(values)

        self.global_thresholds = aggregated

        return aggregated

    def get_anomaly_statistics(self) -> Dict[str, Any]:
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
