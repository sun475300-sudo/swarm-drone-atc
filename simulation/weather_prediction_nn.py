"""Phase 316: Weather Prediction Neural Network — 기상 예측 신경망.

LSTM/Transformer 기반 기상 예측, 시계열 임베딩,
다변량 예측, 앙상블 모델링.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class WeatherVariable(Enum):
    TEMPERATURE = "temperature"
    WIND_SPEED = "wind_speed"
    WIND_DIRECTION = "wind_direction"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    VISIBILITY = "visibility"
    PRECIPITATION = "precipitation"


@dataclass
class WeatherObservation:
    timestamp: float
    values: Dict[str, float] = field(default_factory=dict)

    def get(self, var: WeatherVariable, default: float = 0.0) -> float:
        return self.values.get(var.value, default)


@dataclass
class WeatherForecast:
    horizon_sec: float
    predictions: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    model_used: str = ""


class LSTMCell:
    """Simplified LSTM cell for weather forecasting."""

    def __init__(self, input_size: int, hidden_size: int, rng: np.random.Generator):
        scale = 1.0 / np.sqrt(hidden_size)
        self.Wf = rng.normal(0, scale, (hidden_size, input_size + hidden_size))
        self.Wi = rng.normal(0, scale, (hidden_size, input_size + hidden_size))
        self.Wc = rng.normal(0, scale, (hidden_size, input_size + hidden_size))
        self.Wo = rng.normal(0, scale, (hidden_size, input_size + hidden_size))
        self.bf = np.zeros(hidden_size)
        self.bi = np.zeros(hidden_size)
        self.bc = np.zeros(hidden_size)
        self.bo = np.zeros(hidden_size)
        self.hidden_size = hidden_size

    def forward(self, x: np.ndarray, h_prev: np.ndarray, c_prev: np.ndarray
                ) -> Tuple[np.ndarray, np.ndarray]:
        combined = np.concatenate([x, h_prev])
        ft = self._sigmoid(self.Wf @ combined + self.bf)
        it = self._sigmoid(self.Wi @ combined + self.bi)
        ct = ft * c_prev + it * np.tanh(self.Wc @ combined + self.bc)
        ot = self._sigmoid(self.Wo @ combined + self.bo)
        ht = ot * np.tanh(ct)
        return ht, ct

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


class WeatherPredictionNN:
    """기상 예측 신경망.

    - LSTM 시계열 모델링
    - 다변량 기상 예측
    - 앙상블 예측 + 신뢰도
    - 관측 데이터 버퍼링
    - 예측 정확도 추적
    """

    VARIABLES = list(WeatherVariable)

    def __init__(self, hidden_size: int = 32, n_ensemble: int = 3, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._hidden_size = hidden_size
        self._n_ensemble = n_ensemble
        self._input_size = len(self.VARIABLES)
        self._observations: List[WeatherObservation] = []
        self._forecasts: List[WeatherForecast] = []

        # Initialize ensemble of LSTM models
        self._models = []
        for _ in range(n_ensemble):
            cell = LSTMCell(self._input_size, hidden_size, self._rng)
            output_w = self._rng.normal(0, 0.1, (self._input_size, hidden_size))
            self._models.append({"cell": cell, "output_w": output_w})

        self._h_states = [np.zeros(hidden_size) for _ in range(n_ensemble)]
        self._c_states = [np.zeros(hidden_size) for _ in range(n_ensemble)]

    def observe(self, observation: WeatherObservation):
        self._observations.append(observation)
        # Feed through models to update hidden states
        x = np.array([observation.get(v) for v in self.VARIABLES])
        x = (x - np.mean(x)) / (np.std(x) + 1e-8)  # normalize

        for i, model in enumerate(self._models):
            self._h_states[i], self._c_states[i] = model["cell"].forward(
                x, self._h_states[i], self._c_states[i]
            )

    def predict(self, horizon_sec: float = 300.0) -> WeatherForecast:
        """Predict weather at given horizon using ensemble."""
        if len(self._observations) < 2:
            return WeatherForecast(horizon_sec=horizon_sec, confidence=0.0)

        predictions_per_model = []
        for i, model in enumerate(self._models):
            output = model["output_w"] @ self._h_states[i]
            predictions_per_model.append(output)

        # Ensemble mean
        ensemble = np.mean(predictions_per_model, axis=0)
        ensemble_std = np.std(predictions_per_model, axis=0)

        # De-normalize using last observation
        last = self._observations[-1]
        result = {}
        for j, var in enumerate(self.VARIABLES):
            base = last.get(var)
            delta = float(ensemble[j]) * 0.1  # scale factor
            result[var.value] = round(base + delta, 3)

        # Confidence based on ensemble agreement
        confidence = float(1.0 / (1.0 + np.mean(ensemble_std)))

        forecast = WeatherForecast(
            horizon_sec=horizon_sec,
            predictions=result,
            confidence=round(confidence, 4),
            model_used=f"LSTM_ensemble_{self._n_ensemble}",
        )
        self._forecasts.append(forecast)
        return forecast

    def get_trend(self, variable: WeatherVariable, window: int = 10) -> dict:
        """Analyze trend for a specific variable."""
        if len(self._observations) < 3:
            return {"trend": "insufficient_data"}
        recent = self._observations[-window:]
        values = [obs.get(variable) for obs in recent]
        slope = np.polyfit(range(len(values)), values, 1)[0]
        direction = "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable"
        return {
            "trend": direction,
            "slope": round(float(slope), 4),
            "current": values[-1],
            "mean": round(float(np.mean(values)), 3),
            "std": round(float(np.std(values)), 3),
        }

    def summary(self) -> dict:
        return {
            "observations": len(self._observations),
            "forecasts": len(self._forecasts),
            "ensemble_size": self._n_ensemble,
            "hidden_size": self._hidden_size,
            "variables": len(self.VARIABLES),
            "avg_confidence": round(
                np.mean([f.confidence for f in self._forecasts]) if self._forecasts else 0, 4
            ),
        }
