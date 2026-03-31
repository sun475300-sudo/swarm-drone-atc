# Phase 643: Health Predictor — Predictive Maintenance via Exponential Smoothing
"""
드론 건강 상태 예측: 배터리 열화, 모터 진동, 센서 드리프트를
지수 평활법으로 추세 분석하여 잔여 수명(RUL) 추정.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class HealthMetric:
    name: str
    values: list[float] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)
    threshold: float = 0.0  # 임계값 (이하이면 경고)


@dataclass
class RULEstimate:
    drone_id: str
    metric: str
    remaining_hours: float
    confidence: float  # 0-1
    trend: str  # "degrading", "stable", "improving"


class HealthPredictor:
    def __init__(self, seed: int = 42, alpha: float = 0.3, beta: float = 0.1):
        self.rng = np.random.default_rng(seed)
        self.alpha = alpha  # level smoothing
        self.beta = beta    # trend smoothing
        self._metrics: dict[str, dict[str, HealthMetric]] = {}

    def register_drone(self, drone_id: str) -> None:
        self._metrics[drone_id] = {
            "battery_health": HealthMetric("battery_health", threshold=20.0),
            "motor_vibration": HealthMetric("motor_vibration", threshold=80.0),
            "sensor_drift": HealthMetric("sensor_drift", threshold=5.0),
            "comm_quality": HealthMetric("comm_quality", threshold=30.0),
        }

    def record(self, drone_id: str, metric_name: str, value: float, t: float) -> None:
        if drone_id not in self._metrics:
            self.register_drone(drone_id)
        m = self._metrics[drone_id].get(metric_name)
        if m is None:
            m = HealthMetric(metric_name)
            self._metrics[drone_id][metric_name] = m
        m.values.append(value)
        m.timestamps.append(t)

    def _holt_forecast(self, values: list[float], steps: int) -> list[float]:
        if len(values) < 2:
            return [values[-1]] * steps if values else [0.0] * steps

        level = values[0]
        trend = values[1] - values[0]

        for v in values[1:]:
            new_level = self.alpha * v + (1 - self.alpha) * (level + trend)
            new_trend = self.beta * (new_level - level) + (1 - self.beta) * trend
            level = new_level
            trend = new_trend

        forecasts = []
        for i in range(1, steps + 1):
            forecasts.append(level + i * trend)
        return forecasts

    def predict_rul(self, drone_id: str, metric_name: str) -> RULEstimate:
        if drone_id not in self._metrics:
            return RULEstimate(drone_id, metric_name, float("inf"), 0.0, "stable")

        m = self._metrics[drone_id].get(metric_name)
        if m is None or len(m.values) < 3:
            return RULEstimate(drone_id, metric_name, float("inf"), 0.0, "stable")

        # Forecast 100 steps ahead
        forecasts = self._holt_forecast(m.values, 100)

        # Find when threshold is crossed
        rul_steps = 100
        for i, f in enumerate(forecasts):
            if metric_name == "motor_vibration":
                # vibration increases → fail when above threshold
                if f > m.threshold:
                    rul_steps = i
                    break
            else:
                # battery/comm degrades → fail when below threshold
                if f < m.threshold:
                    rul_steps = i
                    break

        # Convert steps to hours (assuming 1 step = 1 minute)
        rul_hours = rul_steps / 60.0

        # Trend detection
        recent = m.values[-min(10, len(m.values)):]
        slope = np.polyfit(range(len(recent)), recent, 1)[0]
        if metric_name == "motor_vibration":
            trend = "degrading" if slope > 0.1 else ("improving" if slope < -0.1 else "stable")
        else:
            trend = "degrading" if slope < -0.1 else ("improving" if slope > 0.1 else "stable")

        # Confidence based on data points
        confidence = min(1.0, len(m.values) / 50.0)

        return RULEstimate(drone_id, metric_name, rul_hours, confidence, trend)

    def fleet_health_summary(self) -> dict:
        summary = {"total_drones": len(self._metrics), "alerts": []}
        for drone_id in self._metrics:
            for metric_name in self._metrics[drone_id]:
                rul = self.predict_rul(drone_id, metric_name)
                if rul.remaining_hours < 1.0 and rul.trend == "degrading":
                    summary["alerts"].append({
                        "drone_id": drone_id,
                        "metric": metric_name,
                        "rul_hours": round(rul.remaining_hours, 2),
                        "confidence": round(rul.confidence, 2),
                    })
        return summary

    def simulate_degradation(self, n_drones: int = 5, n_steps: int = 100) -> dict:
        results = {}
        for i in range(n_drones):
            did = f"D-{i:04d}"
            self.register_drone(did)
            bat = 100.0
            vib = 10.0
            for t in range(n_steps):
                bat -= self.rng.uniform(0.05, 0.15)
                vib += self.rng.uniform(-0.2, 0.5)
                self.record(did, "battery_health", max(0, bat), float(t))
                self.record(did, "motor_vibration", max(0, vib), float(t))

            results[did] = {
                "battery_rul": self.predict_rul(did, "battery_health"),
                "motor_rul": self.predict_rul(did, "motor_vibration"),
            }
        return results


if __name__ == "__main__":
    hp = HealthPredictor(42)
    results = hp.simulate_degradation(5, 100)
    for did, ruls in results.items():
        print(f"{did}: battery RUL={ruls['battery_rul'].remaining_hours:.1f}h "
              f"({ruls['battery_rul'].trend}), "
              f"motor RUL={ruls['motor_rul'].remaining_hours:.1f}h "
              f"({ruls['motor_rul'].trend})")
