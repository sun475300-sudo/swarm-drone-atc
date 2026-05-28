"""
Phase 484: Explainable AI (XAI) for Drone Decisions
SHAP-like 특성 중요도, LIME 로컬 설명, 의사결정 투명성.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np


class ExplanationType(Enum):
    """``ExplanationType`` 관련 기능을 제공한다."""
    FEATURE_IMPORTANCE = "feature_importance"
    LOCAL_SURROGATE = "local_surrogate"
    COUNTERFACTUAL = "counterfactual"
    DECISION_TREE = "decision_tree"


@dataclass
class FeatureAttribution:
    """``FeatureAttribution`` 관련 기능을 제공한다."""
    feature_name: str
    value: float
    attribution: float
    direction: str  # "positive" or "negative"


@dataclass
class Explanation:
    """``Explanation`` 관련 기능을 제공한다."""
    explanation_type: ExplanationType
    decision: str
    confidence: float
    attributions: list[FeatureAttribution]
    counterfactual: dict | None = None
    human_readable: str = ""


@dataclass
class DecisionRecord:
    """``DecisionRecord`` 데이터를 표현한다."""
    drone_id: str
    timestamp: float
    decision: str
    inputs: dict[str, float]
    output: float
    explanation: Explanation | None = None


class SHAPExplainer:
    """Simplified SHAP-like feature attribution."""

    def __init__(self, model_fn: Callable, feature_names: list[str], seed: int = 42):
        """인스턴스를 초기화한다."""
        self.model_fn = model_fn
        self.feature_names = feature_names
        self.rng = np.random.default_rng(seed)
        self.n_samples = 100

    def explain(self, instance: np.ndarray) -> list[FeatureAttribution]:
        """``explain`` 동작을 수행한다."""
        baseline = np.zeros_like(instance)
        base_pred = self.model_fn(baseline)
        attributions = []
        for i, name in enumerate(self.feature_names):
            perturbed_with = baseline.copy()
            perturbed_with[i] = instance[i]
            self.model_fn(perturbed_with) - base_pred

            samples = []
            for _ in range(self.n_samples):
                mask = self.rng.random(len(instance)) > 0.5
                with_feature = instance.copy()
                without_feature = instance.copy()
                for j in range(len(instance)):
                    if mask[j]:
                        with_feature[j] = instance[j]
                        without_feature[j] = baseline[j]
                    else:
                        with_feature[j] = baseline[j]
                        without_feature[j] = instance[j]
                with_feature[i] = instance[i]
                without_feature[i] = baseline[i]
                marginal = self.model_fn(with_feature) - self.model_fn(without_feature)
                samples.append(marginal)

            shap_value = float(np.mean(samples))
            attributions.append(FeatureAttribution(
                name, float(instance[i]), round(shap_value, 4),
                "positive" if shap_value > 0 else "negative"))
        return sorted(attributions, key=lambda a: abs(a.attribution), reverse=True)


class LIMEExplainer:
    """Local Interpretable Model-agnostic Explanations."""

    def __init__(self, model_fn: Callable, feature_names: list[str], seed: int = 42):
        """인스턴스를 초기화한다."""
        self.model_fn = model_fn
        self.feature_names = feature_names
        self.rng = np.random.default_rng(seed)
        self.n_neighbors = 200

    def explain(self, instance: np.ndarray, sigma: float = 0.5) -> list[FeatureAttribution]:
        """``explain`` 동작을 수행한다."""
        neighbors = instance + self.rng.standard_normal((self.n_neighbors, len(instance))) * sigma
        predictions = np.array([self.model_fn(n) for n in neighbors])
        distances = np.linalg.norm(neighbors - instance, axis=1)
        weights = np.exp(-distances ** 2 / (2 * sigma ** 2))

        X = neighbors - instance
        W = np.diag(weights)
        try:
            coeffs = np.linalg.lstsq(W @ X, W @ (predictions - self.model_fn(instance)), rcond=None)[0]
        except np.linalg.LinAlgError:
            coeffs = np.zeros(len(instance))

        return [FeatureAttribution(
            self.feature_names[i], float(instance[i]), round(float(coeffs[i]), 4),
            "positive" if coeffs[i] > 0 else "negative"
        ) for i in range(len(self.feature_names))]


class CounterfactualExplainer:
    """Find minimal changes to flip a decision."""

    def __init__(self, model_fn: Callable, feature_names: list[str], seed: int = 42):
        """인스턴스를 초기화한다."""
        self.model_fn = model_fn
        self.feature_names = feature_names
        self.rng = np.random.default_rng(seed)

    def explain(self, instance: np.ndarray, target_class: float,
                threshold: float = 0.5, max_iter: int = 500) -> dict | None:
        """``explain`` 동작을 수행한다."""
        self.model_fn(instance)
        best = None
        best_dist = float('inf')
        for _ in range(max_iter):
            delta = self.rng.standard_normal(len(instance)) * 0.2
            candidate = instance + delta
            pred = self.model_fn(candidate)
            if (target_class > 0.5 and pred > threshold) or (target_class <= 0.5 and pred < threshold):
                dist = np.linalg.norm(delta)
                if dist < best_dist:
                    best_dist = dist
                    best = {
                        "original": {self.feature_names[i]: float(instance[i]) for i in range(len(instance))},
                        "counterfactual": {self.feature_names[i]: float(candidate[i]) for i in range(len(instance))},
                        "changes": {self.feature_names[i]: round(float(delta[i]), 4)
                                   for i in range(len(instance)) if abs(delta[i]) > 0.05},
                        "distance": round(best_dist, 4),
                    }
        return best


class ExplainableAI:
    """Unified XAI system for drone decision transparency."""

    def __init__(self, seed: int = 42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.decision_log: list[DecisionRecord] = []
        self.explanations: list[Explanation] = []

    def explain_decision(self, model_fn: Callable, feature_names: list[str],
                         instance: np.ndarray, drone_id: str = "drone_0",
                         decision_name: str = "action") -> Explanation:
        """``explain_decision`` 동작을 수행한다."""
        shap = SHAPExplainer(model_fn, feature_names, self.rng.integers(0, 10000))
        attributions = shap.explain(instance)
        prediction = model_fn(instance)
        top3 = attributions[:3]
        readable_parts = [f"{a.feature_name}={a.value:.2f} ({a.direction}, {a.attribution:+.3f})" for a in top3]
        human_readable = f"Decision '{decision_name}' (conf={prediction:.2f}): top factors — " + ", ".join(readable_parts)

        explanation = Explanation(
            ExplanationType.FEATURE_IMPORTANCE, decision_name,
            round(float(prediction), 4), attributions, human_readable=human_readable)
        self.explanations.append(explanation)

        record = DecisionRecord(drone_id, len(self.decision_log),
                               decision_name, dict(zip(feature_names, instance.tolist(), strict=False)),
                               float(prediction), explanation)
        self.decision_log.append(record)
        return explanation

    def summary(self) -> dict:
        """현재 상태 요약을 반환한다."""
        return {
            "decisions_explained": len(self.decision_log),
            "explanation_types": list({e.explanation_type.value for e in self.explanations}),
            "avg_confidence": round(float(np.mean([e.confidence for e in self.explanations])), 4) if self.explanations else 0,
        }
