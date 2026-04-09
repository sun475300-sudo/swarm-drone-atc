"""
Bayesian parameter tuner.
=========================
Lightweight Bayesian-style optimization using kernel-weighted surrogate scoring.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np


@dataclass
class TuningObservation:
    params: dict[str, float]
    score: float


class BayesianTuner:
    def __init__(
        self,
        bounds: dict[str, tuple[float, float]],
        exploration: float = 0.15,
        kernel_sigma: float = 0.2,
        seed: int = 42,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self._bounds = bounds
        self._keys = list(bounds.keys())
        self._exploration = exploration
        self._kernel_sigma = max(kernel_sigma, 1e-4)
        self._observations: list[TuningObservation] = []

    def _sample_random(self) -> dict[str, float]:
        return {
            k: float(self._rng.uniform(self._bounds[k][0], self._bounds[k][1]))
            for k in self._keys
        }

    def _to_vector(self, params: dict[str, float]) -> np.ndarray:
        return np.array([float(params[k]) for k in self._keys], dtype=np.float64)

    def _predict_mean_std(self, candidate: dict[str, float]) -> tuple[float, float]:
        if len(self._observations) < 2:
            return 0.0, 1.0

        x = self._to_vector(candidate)
        xs = np.array([self._to_vector(obs.params) for obs in self._observations])
        ys = np.array([obs.score for obs in self._observations], dtype=np.float64)

        d2 = np.sum((xs - x) ** 2, axis=1)
        weights = np.exp(-d2 / (2 * self._kernel_sigma**2))
        wsum = np.sum(weights)
        if wsum < 1e-12:
            return float(np.mean(ys)), float(np.std(ys) + 1e-6)

        mean = float(np.sum(weights * ys) / wsum)
        var = float(np.sum(weights * (ys - mean) ** 2) / wsum)
        return mean, float(np.sqrt(max(var, 1e-12)))

    def suggest(self, n_candidates: int = 1) -> list[dict[str, float]]:
        suggestions: list[dict[str, float]] = []
        for _ in range(max(1, n_candidates)):
            if len(self._observations) < 5 or self._rng.random() < self._exploration:
                suggestions.append(self._sample_random())
                continue

            pool = [self._sample_random() for _ in range(96)]
            acq = []
            for p in pool:
                mean, std = self._predict_mean_std(p)
                acq.append(mean + 1.5 * std)
            suggestions.append(pool[int(np.argmax(acq))])
        return suggestions

    def report(self, params: dict[str, float], score: float) -> None:
        self._observations.append(TuningObservation(params=dict(params), score=float(score)))

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        n_iter: int = 20,
    ) -> dict[str, Any]:
        for _ in range(max(1, n_iter)):
            proposal = self.suggest(1)[0]
            score = float(objective(proposal))
            self.report(proposal, score)
        return self.best()

    def best(self) -> dict[str, Any]:
        if not self._observations:
            return {"params": {}, "score": 0.0}
        best = max(self._observations, key=lambda o: o.score)
        return {"params": dict(best.params), "score": round(float(best.score), 6)}

    def summary(self) -> dict[str, Any]:
        best_score = self.best()["score"] if self._observations else 0.0
        return {
            "parameters": len(self._keys),
            "observations": len(self._observations),
            "best_score": best_score,
            "exploration": round(self._exploration, 3),
        }
