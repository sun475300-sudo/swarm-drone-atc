"""A/B Testing Framework for Phase 200-219.

Provides statistical comparison between algorithms and policies.
"""

from __future__ import annotations

import json
import time
from dataclasses as dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np


@dataclass
class Variant:
    """Single A/B test variant."""

    name: str
    run: Callable[[], float]
    weight: float = 1.0


@dataclass
class VariantResult:
    """Result of a single variant."""

    name: str
    values: list[float] = field(default_factory=list)
    n_samples: int = 0
    mean: float = 0.0
    std: float = 0.0
    median: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    duration_ms: float = 0.0


@dataclass
class ABTestResult:
    """Complete A/B test result."""

    test_name: str
    control: VariantResult
    treatments: list[VariantResult]
    winner: str | None = None
    p_value: float = 0.0
    confidence: float = 0.0
    effect_size: float = 0.0
    run_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ABTestRunner:
    """Runner for A/B tests with statistical analysis."""

    def __init__(
        self,
        n_samples: int = 100,
        confidence_level: float = 0.95,
        seed: int | None = None,
    ) -> None:
        self._n_samples = n_samples
        self._confidence = confidence_level
        self._rng = np.random.default_rng(seed) if seed else np.random.default_rng()
        self._results: dict[str, list[float]] = {}

    def add_variant(self, name: str, values: list[float]) -> "ABTestRunner":
        """Add a variant with pre-computed values."""
        self._results[name] = values
        return self

    def run_ttest(
        self,
        control: str,
        treatment: str,
    ) -> tuple[float, float]:
        """Run independent t-test between control and treatment.
        
        Returns: (t_statistic, p_value)
        """
        ctrl = np.array(self._results.get(control, []))
        treat = np.array(self._results.get(treatment, []))
        
        if len(ctrl) < 2 or len(treat) < 2:
            return 0.0, 1.0
        
        from scipy import stats
        t, p = stats.ttest_ind(ctrl, treat)
        return float(t), float(p)

    def calculate_effect_size(
        self,
        control: str,
        treatment: str,
    ) -> float:
        """Calculate Cohen's d effect size."""
        ctrl = np.array(self._results.get(control, []))
        treat = np.array(self._results.get(treatment, []))
        
        if len(ctrl) < 2 or len(treat) < 2:
            return 0.0
        
        pooled_std = np.sqrt((np.var(ctrl) + np.var(treat)) / 2)
        if pooled_std == 0:
            return 0.0
        
        return float((np.mean(treat) - np.mean(ctrl)) / pooled_std)

    def compare(
        self,
        control: str,
        treatment: str,
    ) -> dict[str, Any]:
        """Compare two variants with statistical analysis."""
        _, p_value = self.run_ttest(control, treatment)
        effect = self.calculate_effect_size(control, treatment)
        
        ctrl_mean = float(np.mean(self._results.get(control, [0])))
        treat_mean = float(np.mean(self._results.get(treatment, [0])))
        
        return {
            "control_mean": ctrl_mean,
            "treatment_mean": treat_mean,
            "relative_change": (treat_mean - ctrl_mean) / ctrl_mean if ctrl_mean else 0.0,
            "p_value": p_value,
            "significant": p_value < (1 - self._confidence),
            "effect_size": effect,
            "effect_interpretation": self._interpret_effect(effect),
        }

    def _interpret_effect(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        d = abs(d)
        if d < 0.2:
            return "negligible"
        elif d < 0.5:
            return "small"
        elif d < 0.8:
            return "medium"
        return "large"

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics for all variants."""
        return {
            name: {
                "n": len(values),
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "median": float(np.median(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }
            for name, values in self._results.items()
        }

    def export_results(self, filepath: str | Path) -> None:
        """Export test results to JSON."""
        data = {
            "n_samples": self._n_samples,
            "confidence_level": self._confidence,
            "variants": self.get_summary(),
            "exported_at": datetime.now().isoformat(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)


class MultiArmedBandit:
    """Multi-armed bandit for adaptive A/B testing."""

    def __init__(
        self,
        arms: list[str],
        epsilon: float = 0.1,
        seed: int | None = None,
    ) -> None:
        self._arms = arms
        self._epsilon = epsilon
        self._rng = np.random.default_rng(seed) if seed else np.random.default_rng()
        self._counts: dict[str, int] = {arm: 0 for arm in arms}
        self._values: dict[str, float] = {arm: 0.0 for arm in arms}
        self._history: list[tuple[str, float]] = []

    def select_arm(self) -> str:
        """Select arm using epsilon-greedy strategy."""
        if self._rng.random() < self._epsilon:
            return self._rng.choice(self._arms)
        
        max_value = max(self._values.values())
        best_arms = [arm for arm, v in self._values.items() if v == max_value]
        return self._rng.choice(best_arms)

    def update(self, arm: str, reward: float) -> None:
        """Update arm value estimate."""
        self._counts[arm] += 1
        n = self._counts[arm]
        value = self._values[arm]
        self._values[arm] = value + (reward - value) / n
        self._history.append((arm, reward))

    def get_best_arm(self) -> str:
        """Get current best arm."""
        return max(self._values.items(), key=lambda x: x[1])[0]

    def get_statistics(self) -> dict[str, Any]:
        """Get bandit statistics."""
        total = sum(self._counts.values())
        return {
            "arms": self._arms,
            "counts": self._counts,
            "values": self._values,
            "best_arm": self.get_best_arm(),
            "total_selections": total,
            "arm_distribution": {
                arm: count / total if total else 0.0
                for arm, count in self._counts.items()
            },
        }


class ScenarioABComparator:
    """A/B comparator for scenario-based comparisons."""

    SCENARIOS = {
        "high_density": {
            "description": "High drone density scenario",
            "metric": "collision_rate",
            "direction": "minimize",
        },
        "weather_disturbance": {
            "description": "Weather disturbance scenario",
            "metric": "throughput_degradation",
            "direction": "minimize",
        },
        "emergency_failure": {
            "description": "Emergency drone failure scenario",
            "metric": "recovery_time",
            "direction": "minimize",
        },
    }

    def __init__(self) -> None:
        self._comparisons: dict[str, dict[str, float]] = {}

    def add_comparison(
        self,
        scenario: str,
        algorithm: str,
        metric_value: float,
    ) -> "ScenarioABComparator":
        """Add a comparison result."""
        if scenario not in self._comparisons:
            self._comparisons[scenario] = {}
        self._comparisons[scenario][algorithm] = metric_value
        return self

    def compare_algorithms(
        self,
        scenario: str,
        algorithm_a: str,
        algorithm_b: str,
    ) -> dict[str, Any]:
        """Compare two algorithms on a scenario."""
        if scenario not in self._comparisons:
            return {"error": "Scenario not found"}
        
        comp = self._comparisons[scenario]
        if algorithm_a not in comp or algorithm_b not in comp:
            return {"error": "Algorithm not found"}
        
        val_a = comp[algorithm_a]
        val_b = comp[algorithm_b]
        scenario_info = self.SCENARIOS.get(scenario, {})
        
        if scenario_info.get("direction") == "minimize":
            winner = algorithm_a if val_a < val_b else algorithm_b
            improvement = (val_b - val_a) / val_a if val_a else 0.0
        else:
            winner = algorithm_a if val_a > val_b else algorithm_b
            improvement = (val_a - val_b) / val_b if val_b else 0.0
        
        return {
            "scenario": scenario,
            "algorithm_a": algorithm_a,
            "algorithm_b": algorithm_b,
            "value_a": val_a,
            "value_b": val_b,
            "winner": winner,
            "improvement_pct": improvement * 100,
            "metric": scenario_info.get("metric", "unknown"),
        }

    def get_ranking(self, scenario: str) -> list[tuple[str, float]]:
        """Get algorithm ranking for a scenario."""
        if scenario not in self._comparisons:
            return []
        
        items = self._comparisons[scenario].items()
        direction = self.SCENARIOS.get(scenario, {}).get("direction", "minimize")
        
        if direction == "minimize":
            return sorted(items, key=lambda x: x[1])
        return sorted(items, key=lambda x: x[1], reverse=True)

    def export_comparison_matrix(self, filepath: str | Path) -> None:
        """Export full comparison matrix."""
        data = {
            "scenarios": self.SCENARIOS,
            "comparisons": self._comparisons,
            "rankings": {
                scenario: self.get_ranking(scenario)
                for scenario in self._comparisons
            },
            "generated_at": datetime.now().isoformat(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
