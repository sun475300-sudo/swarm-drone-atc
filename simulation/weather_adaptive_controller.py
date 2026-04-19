"""
Phase 441: Weather Adaptive Controller for Dynamic Conditions
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import time


@dataclass
class WeatherCondition:
    temperature_c: float
    wind_speed_ms: float
    wind_direction_deg: float
    humidity_percent: float
    pressure_hpa: float
    visibility_m: float
    precipitation_mmh: float


class WeatherAdaptiveController:
    def __init__(self):
        self.current_weather: Optional[WeatherCondition] = None
        self.adaptation_history: List[Dict] = []

    def update_weather(self, weather: WeatherCondition):
        self.current_weather = weather

    def compute_adapted_parameters(self) -> Dict[str, float]:
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

    def predict_weather_trend(self, history: List[WeatherCondition]) -> str:
        if len(history) < 3:
            return "stable"

        wind_changes = [h.wind_speed_ms for h in history[-3:]]
        if abs(wind_changes[-1] - wind_changes[0]) > 5:
            return "changing"
        return "stable"
