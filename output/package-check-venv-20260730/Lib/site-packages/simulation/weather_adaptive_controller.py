"""
Phase 441: Weather Adaptive Controller for Dynamic Conditions
"""

import time
from dataclasses import dataclass


@dataclass
class WeatherCondition:
    """``WeatherCondition`` 관련 기능을 제공한다."""
    temperature_c: float
    wind_speed_ms: float
    wind_direction_deg: float
    humidity_percent: float
    pressure_hpa: float
    visibility_m: float
    precipitation_mmh: float


class WeatherAdaptiveController:
    """``WeatherAdaptiveController`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.current_weather: WeatherCondition | None = None
        self.adaptation_history: list[dict] = []

    def update_weather(self, weather: WeatherCondition):
        """`weather` 상태를 갱신한다."""
        self.current_weather = weather

    def compute_adapted_parameters(self) -> dict[str, float]:
        """`adapted parameters` 값을 계산한다."""
        if not self.current_weather:
            return {}

        w = self.current_weather

        if w.wind_speed_ms > 10:
            param = {
                "velocity_scale": 0.7,
                "path_margin": 1.5,
                "battery_buffer": 1.3,
                "control_gain": 1.2,
            }
        elif w.wind_speed_ms > 5:
            param = {
                "velocity_scale": 0.85,
                "path_margin": 1.2,
                "battery_buffer": 1.15,
                "control_gain": 1.1,
            }
        else:
            param = {
                "velocity_scale": 1.0,
                "path_margin": 1.0,
                "battery_buffer": 1.0,
                "control_gain": 1.0,
            }

        if w.precipitation_mmh > 0:
            param["velocity_scale"] *= 0.8
            param["battery_buffer"] *= 1.2

        self.adaptation_history.append(
            {
                "timestamp": time.time(),
                "weather": w.__dict__,
                "parameters": param,
            }
        )

        return param

    def predict_weather_trend(self, history: list[WeatherCondition]) -> str:
        """`weather trend` 결과를 계산하거나 판정한다."""
        if len(history) < 3:
            return "stable"

        wind_changes = [h.wind_speed_ms for h in history[-3:]]
        if abs(wind_changes[-1] - wind_changes[0]) > 5:
            return "changing"
        return "stable"
