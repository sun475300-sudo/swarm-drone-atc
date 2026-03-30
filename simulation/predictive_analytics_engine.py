"""
Phase 412: Predictive Analytics Engine for Swarm Operations
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import deque


class ForecastType(Enum):
    TRAFFIC = "traffic"
    BATTERY = "battery"
    WEATHER = "weather"
    DEMAND = "demand"
    ANOMALY = "anomaly"


@dataclass
class Forecast:
    forecast_type: ForecastType
    predictions: np.ndarray
    confidence: float
    time_horizon: float
    generated_at: float


@dataclass
class AnomalyAlert:
    alert_id: str
    anomaly_type: str
    severity: str
    detected_at: float
    affected_drones: List[str]
    description: str


class PredictiveAnalyticsEngine:
    def __init__(
        self,
        history_window: int = 1000,
        forecast_horizon: float = 3600.0,
        anomaly_threshold: float = 3.0,
    ):
        self.history_window = history_window
        self.forecast_horizon = forecast_horizon
        self.anomaly_threshold = anomaly_threshold

        self.data_streams: Dict[ForecastType, deque] = {
            ft: deque(maxlen=history_window) for ft in ForecastType
        }

        self.forecasts: Dict[ForecastType, Forecast] = {}
        self.anomaly_history: List[AnomalyAlert] = []

        self.model_params = self._initialize_models()

    def _initialize_models(self) -> Dict:
        return {
            "arima_order": (5, 1, 2),
            "lstm_units": 64,
            "isolation_forest contamination": 0.1,
        }

    def ingest_data(
        self, forecast_type: ForecastType, data: np.ndarray, timestamp: float
    ):
        self.data_streams[forecast_type].append(
            {
                "data": data,
                "timestamp": timestamp,
            }
        )

    def generate_forecast(self, forecast_type: ForecastType) -> Forecast:
        if len(self.data_streams[forecast_type]) < 10:
            return Forecast(
                forecast_type=forecast_type,
                predictions=np.array([]),
                confidence=0.0,
                time_horizon=self.forecast_horizon,
                generated_at=time.time(),
            )

        history = np.array(
            [item["data"] for item in list(self.data_streams[forecast_type])[-50:]]
        )

        predictions = self._arima_forecast(
            history, steps=int(self.forecast_horizon / 60)
        )

        confidence = self._calculate_confidence(history, predictions)

        forecast = Forecast(
            forecast_type=forecast_type,
            predictions=predictions,
            confidence=confidence,
            time_horizon=self.forecast_horizon,
            generated_at=time.time(),
        )

        self.forecasts[forecast_type] = forecast

        return forecast

    def _arima_forecast(self, history: np.ndarray, steps: int) -> np.ndarray:
        if len(history.shape) == 1:
            history = history.reshape(-1, 1)

        mean = np.mean(history, axis=0)
        trend = np.linspace(0, 0.1, steps)

        predictions = (
            mean
            + trend
            + np.random.randn(steps, history.shape[1]) * np.std(history, axis=0) * 0.1
        )

        return predictions

    def _calculate_confidence(
        self, history: np.ndarray, predictions: np.ndarray
    ) -> float:
        if len(history) < 2:
            return 0.0

        variance = np.var(history, axis=0)
        prediction_variance = np.var(predictions) if len(predictions) > 0 else 1.0

        stability = 1.0 / (1.0 + np.mean(variance))

        data_quality = min(len(history) / 100, 1.0)

        confidence = stability * 0.6 + data_quality * 0.4

        return min(confidence, 1.0)

    def detect_anomalies(
        self, data: np.ndarray, drone_ids: List[str]
    ) -> List[AnomalyAlert]:
        alerts = []

        mean = (
            np.mean(data, axis=0)
            if len(data) > 0
            else np.zeros(data.shape[1] if len(data.shape) > 1 else 1)
        )
        std = (
            np.std(data, axis=0)
            if len(data) > 1
            else np.ones(data.shape[1] if len(data.shape) > 1 else 1)
        )

        for i, point in enumerate(data):
            if len(point.shape) > 0:
                z_scores = np.abs((point - mean) / (std + 1e-6))
            else:
                z_scores = np.abs((point - mean) / (std + 1e-6))

            max_z = np.max(z_scores) if len(z_scores.shape) > 0 else abs(z_scores)

            if max_z > self.anomaly_threshold:
                alert = AnomalyAlert(
                    alert_id=f"alert_{int(time.time() * 1000)}_{i}",
                    anomaly_type="statistical_outlier",
                    severity="high" if max_z > self.anomaly_threshold * 2 else "medium",
                    detected_at=time.time(),
                    affected_drones=[drone_ids[i]] if i < len(drone_ids) else [],
                    description=f"Z-score: {max_z:.2f}",
                )
                alerts.append(alert)

        self.anomaly_history.extend(alerts)

        return alerts

    def predict_battery_failure(
        self, drone_id: str, battery_history: np.ndarray
    ) -> Dict[str, Any]:
        if len(battery_history) < 10:
            return {"risk_level": "unknown", "hours_remaining": None}

        recent = battery_history[-10:]

        depletion_rate = np.mean(np.diff(recent))

        if depletion_rate >= 0:
            risk_level = "critical"
            hours_remaining = 0
        else:
            hours_remaining = (
                abs(recent[-1] / depletion_rate) if depletion_rate < 0 else None
            )

            if hours_remaining and hours_remaining < 1:
                risk_level = "critical"
            elif hours_remaining and hours_remaining < 3:
                risk_level = "high"
            elif hours_remaining and hours_remaining < 6:
                risk_level = "medium"
            else:
                risk_level = "low"

        return {
            "drone_id": drone_id,
            "risk_level": risk_level,
            "hours_remaining": hours_remaining,
            "depletion_rate_per_hour": abs(depletion_rate) if depletion_rate < 0 else 0,
            "current_level": battery_history[-1] if len(battery_history) > 0 else 0,
        }

    def predict_collision_risk(
        self, positions: np.ndarray, velocities: np.ndarray
    ) -> Dict[str, Any]:
        n = len(positions)
        risks = []

        for i in range(n):
            for j in range(i + 1, n):
                pos_diff = positions[i] - positions[j]
                vel_diff = velocities[i] - velocities[j]

                distance = np.linalg.norm(pos_diff)
                closing_speed = np.linalg.norm(vel_diff)

                if closing_speed > 0:
                    time_to_collision = distance / closing_speed
                else:
                    time_to_collision = float("inf")

                risk_score = (
                    1.0 / (1.0 + distance / 10.0) * min(closing_speed / 20.0, 1.0)
                )

                risks.append(
                    {
                        "pair": (i, j),
                        "distance": distance,
                        "closing_speed": closing_speed,
                        "time_to_collision": time_to_collision,
                        "risk_score": risk_score,
                    }
                )

        max_risk = max(risks, key=lambda r: r["risk_score"]) if risks else None

        return {
            "total_pairs": len(risks),
            "high_risk_pairs": sum(1 for r in risks if r["risk_score"] > 0.5),
            "max_risk": max_risk,
            "all_risks": risks,
        }

    def get_analytics_summary(self) -> Dict[str, Any]:
        return {
            "data_points": {
                ft.value: len(self.data_streams[ft]) for ft in ForecastType
            },
            "forecasts_available": list(self.forecasts.keys()),
            "anomaly_count": len(self.anomaly_history),
            "recent_alerts": [
                {
                    "alert_id": a.alert_id,
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "detected_at": a.detected_at,
                }
                for a in self.anomaly_history[-10:]
            ],
        }
