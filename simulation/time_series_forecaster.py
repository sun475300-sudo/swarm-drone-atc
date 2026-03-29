"""
Time-series forecaster.
=======================
Hybrid AR(1) + exponential smoothing forecaster for drone traffic metrics.
"""
from __future__ import annotations

from typing import Any

import numpy as np


class TimeSeriesForecaster:
    def __init__(self, alpha: float = 0.3) -> None:
        self.alpha = float(np.clip(alpha, 0.01, 0.99))
        self._series: list[float] = []
        self._smooth: float | None = None
        self._phi: float = 0.0
        self._mean: float = 0.0
        self._forecasts = 0

    def fit(self, series: list[float]) -> dict[str, Any]:
        if len(series) < 2:
            raise ValueError("series must contain at least 2 points")

        self._series = [float(v) for v in series]
        self._mean = float(np.mean(self._series))

        smooth = self._series[0]
        for value in self._series[1:]:
            smooth = self.alpha * value + (1 - self.alpha) * smooth
        self._smooth = float(smooth)

        x_prev = np.array(self._series[:-1], dtype=np.float64)
        x_curr = np.array(self._series[1:], dtype=np.float64)
        denom = float(np.sum((x_prev - x_prev.mean()) ** 2))
        if denom < 1e-12:
            self._phi = 0.0
        else:
            numer = float(np.sum((x_prev - x_prev.mean()) * (x_curr - x_curr.mean())))
            self._phi = float(np.clip(numer / denom, -0.99, 0.99))

        return {
            "n_points": len(self._series),
            "phi": round(self._phi, 6),
            "smoothed": round(float(self._smooth), 6),
        }

    def update(self, value: float) -> None:
        v = float(value)
        self._series.append(v)
        if self._smooth is None:
            self._smooth = v
        else:
            self._smooth = self.alpha * v + (1 - self.alpha) * self._smooth
        self._mean = float(np.mean(self._series))

    def forecast(self, steps: int = 5) -> list[float]:
        if not self._series:
            return [0.0] * max(1, steps)

        steps = max(1, steps)
        last = self._series[-1]
        smoothed = self._smooth if self._smooth is not None else last
        out: list[float] = []

        for _ in range(steps):
            ar_part = self._mean + self._phi * (last - self._mean)
            next_val = 0.6 * ar_part + 0.4 * smoothed
            out.append(round(float(next_val), 6))
            last = next_val
            smoothed = self.alpha * next_val + (1 - self.alpha) * smoothed

        self._forecasts += 1
        return out

    def summary(self) -> dict[str, Any]:
        return {
            "points": len(self._series),
            "alpha": round(self.alpha, 3),
            "phi": round(self._phi, 6),
            "forecasts": self._forecasts,
        }
