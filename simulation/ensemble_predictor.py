"""
Multi-model ensemble predictor.
===============================
Combines model outputs through adaptive weighted averaging.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class EnsembleModel:
    name: str
    predict_fn: Callable[[list[float]], float]
    weight: float = 1.0
    mae: float = 1.0


class EnsemblePredictor:
    def __init__(self) -> None:
        self._models: dict[str, EnsembleModel] = {}
        self._predictions = 0

    def register_model(
        self,
        name: str,
        predict_fn: Callable[[list[float]], float],
        weight: float = 1.0,
    ) -> None:
        self._models[name] = EnsembleModel(
            name=name,
            predict_fn=predict_fn,
            weight=max(float(weight), 1e-6),
        )

    def _normalized_weights(self) -> dict[str, float]:
        if not self._models:
            return {}
        total = sum(m.weight for m in self._models.values())
        if total <= 0:
            return {n: 1.0 / len(self._models) for n in self._models}
        return {n: m.weight / total for n, m in self._models.items()}

    def predict(self, features: list[float]) -> dict[str, Any]:
        if not self._models:
            return {"prediction": 0.0, "components": {}}

        weights = self._normalized_weights()
        components: dict[str, float] = {}
        total = 0.0
        for name, model in self._models.items():
            pred = float(model.predict_fn(features))
            components[name] = round(pred, 6)
            total += pred * weights[name]

        self._predictions += 1
        return {
            "prediction": round(total, 6),
            "components": components,
            "weights": {k: round(v, 6) for k, v in weights.items()},
        }

    def calibrate(self, validation_data: list[tuple[list[float], float]]) -> dict[str, float]:
        if not self._models or not validation_data:
            return {}

        errors: dict[str, list[float]] = {name: [] for name in self._models}
        for features, target in validation_data:
            for name, model in self._models.items():
                pred = float(model.predict_fn(features))
                errors[name].append(abs(pred - float(target)))

        for name, vals in errors.items():
            mae = sum(vals) / max(len(vals), 1)
            self._models[name].mae = mae
            self._models[name].weight = 1.0 / max(mae, 1e-3)

        return {name: round(model.weight, 6) for name, model in self._models.items()}

    def top_model(self) -> str | None:
        if not self._models:
            return None
        return max(self._models.values(), key=lambda m: m.weight).name

    def summary(self) -> dict[str, Any]:
        return {
            "models": len(self._models),
            "predictions": self._predictions,
            "top_model": self.top_model(),
        }
