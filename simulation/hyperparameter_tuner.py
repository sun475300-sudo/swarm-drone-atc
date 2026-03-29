"""Hyperparameter Tuning Framework for Phase 200-219.

Provides automated hyperparameter optimization using Optuna for scenario-specific tuning.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np


@dataclass
class TuningConfig:
    """Configuration for hyperparameter tuning."""

    n_trials: int = 100
    timeout_seconds: int | None = None
    n_jobs: int = 1
    sampler: str = "TPE"
    pruner: str = "Median"
    direction: str = "maximize"
    seed: int = 42


@dataclass
class TuningTrial:
    """Single tuning trial result."""

    trial_id: int
    params: dict[str, float]
    value: float
    state: str = "completed"
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TuningResult:
    """Complete tuning result."""

    config: TuningConfig
    trials: list[TuningTrial]
    best_trial: TuningTrial | None = None
    study_name: str = ""
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ParameterSpace:
    """Defines the search space for hyperparameters."""

    def __init__(self) -> None:
        self._spaces: dict[str, dict[str, Any]] = {}

    def add_uniform(
        self,
        name: str,
        low: float,
        high: float,
    ) -> "ParameterSpace":
        """Add uniform continuous parameter."""
        self._spaces[name] = {"type": "uniform", "low": low, "high": high}
        return self

    def add_log_uniform(
        self,
        name: str,
        low: float,
        high: float,
    ) -> "ParameterSpace":
        """Add log-uniform continuous parameter."""
        self._spaces[name] = {"type": "log_uniform", "low": low, "high": high}
        return self

    def add_categorical(
        self,
        name: str,
        choices: list[Any],
    ) -> "ParameterSpace":
        """Add categorical parameter."""
        self._spaces[name] = {"type": "categorical", "choices": choices}
        return self

    def add_int(
        self,
        name: str,
        low: int,
        high: int,
    ) -> "ParameterSpace":
        """Add integer parameter."""
        self._spaces[name] = {"type": "int", "low": low, "high": high}
        return self

    def sample(self, rng: np.random.Generator) -> dict[str, Any]:
        """Sample a random parameter configuration."""
        params = {}
        for name, space in self._spaces.items():
            ptype = space["type"]
            if ptype == "uniform":
                params[name] = rng.uniform(space["low"], space["high"])
            elif ptype == "log_uniform":
                log_low = np.log(space["low"])
                log_high = np.log(space["high"])
                params[name] = np.exp(rng.uniform(log_low, log_high))
            elif ptype == "categorical":
                params[name] = rng.choice(space["choices"])
            elif ptype == "int":
                params[name] = rng.integers(space["low"], space["high"] + 1)
        return params

    def suggest(self, trial: TuningTrial, name: str) -> float | Any:
        """Suggest a parameter value for a trial."""
        if name not in self._spaces:
            raise ValueError(f"Parameter '{name}' not in search space")
        space = self._spaces[name]
        ptype = space["type"]
        if ptype == "uniform":
            return trial.params.get(name, (space["low"] + space["high"]) / 2)
        elif ptype == "log_uniform":
            return trial.params.get(name, np.sqrt(space["low"] * space["high"]))
        elif ptype == "categorical":
            return trial.params.get(name, space["choices"][0])
        elif ptype == "int":
            return trial.params.get(name, (space["low"] + space["high"]) // 2)
        return trial.params.get(name)


class ScenarioTuner:
    """Automated hyperparameter tuner for scenarios."""

    def __init__(
        self,
        config: TuningConfig | None = None,
    ) -> None:
        self._config = config or TuningConfig()
        self._param_space = ParameterSpace()
        self._objective: Callable[[dict[str, Any]], float] | None = None
        self._trials: list[TuningTrial] = []
        self._best_trial: TuningTrial | None = None
        self._rng = np.random.default_rng(self._config.seed)

    def define_search_space(
        self,
        func: Callable[[ParameterSpace], None],
    ) -> "ScenarioTuner":
        """Define the parameter search space.

        Example:
            tuner.define_search_space(lambda ps: (
                ps.add_uniform("learning_rate", 0.001, 0.1),
                ps.add_int("num_layers", 1, 10),
                ps.add_categorical("optimizer", ["adam", "sgd"]),
            ))
        """
        self._param_space = ParameterSpace()
        func(self._param_space)
        return self

    def set_objective(
        self,
        objective: Callable[[dict[str, Any]], float],
    ) -> "ScenarioTuner":
        """Set the objective function to optimize."""
        self._objective = objective
        return self

    def _evaluate_trial(self, params: dict[str, Any]) -> TuningTrial:
        """Evaluate a single trial."""
        if self._objective is None:
            raise ValueError("Objective function not set")

        start_time = time.time()
        try:
            value = self._objective(params)
            state = "completed"
        except Exception:
            value = (
                float("-inf") if self._config.direction == "maximize" else float("inf")
            )
            state = "failed"
        duration = (time.time() - start_time) * 1000

        trial = TuningTrial(
            trial_id=len(self._trials),
            params=params,
            value=value,
            state=state,
            duration_ms=duration,
        )
        return trial

    def run(self, study_name: str = "scenario_tuning") -> TuningResult:
        """Run the hyperparameter tuning."""
        if self._objective is None:
            raise ValueError("Objective function not set")

        self._trials = []
        self._best_trial = None

        for i in range(self._config.n_trials):
            if self._config.timeout_seconds:
                elapsed = sum(t.duration_ms for t in self._trials) / 1000
                if elapsed >= self._config.timeout_seconds:
                    break

            params = self._param_space.sample(self._rng)
            trial = self._evaluate_trial(params)
            self._trials.append(trial)

            if self._best_trial is None or self._is_better(
                trial.value, self._best_trial.value
            ):
                self._best_trial = trial

        return TuningResult(
            config=self._config,
            trials=self._trials,
            best_trial=self._best_trial,
            study_name=study_name,
        )

    def _is_better(self, value: float, best: float) -> bool:
        """Check if value is better than best."""
        if self._config.direction == "maximize":
            return value > best
        return value < best

    def get_best_params(self) -> dict[str, Any]:
        """Get the best parameters found."""
        if self._best_trial is None:
            return {}
        return self._best_trial.params.copy()

    def export_results(self, filepath: str | Path) -> None:
        """Export tuning results to JSON."""
        result = {
            "config": asdict(self._config),
            "study_name": self._best_trial.study
            if hasattr(self._best_trial, "study")
            else "unknown",
            "best_trial": asdict(self._best_trial) if self._best_trial else None,
            "trials": [asdict(t) for t in self._trials],
            "completed_at": datetime.now().isoformat(),
            "n_trials": len(self._trials),
            "n_successful": sum(1 for t in self._trials if t.state == "completed"),
        }
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2)

    def get_statistics(self) -> dict[str, Any]:
        """Get tuning statistics."""
        completed = [t for t in self._trials if t.state == "completed"]
        if not completed:
            return {"n_trials": len(self._trials), "n_completed": 0}

        values = [t.value for t in completed]
        return {
            "n_trials": len(self._trials),
            "n_completed": len(completed),
            "n_failed": len(self._trials) - len(completed),
            "best_value": float(
                np.max(values)
                if self._config.direction == "maximize"
                else np.min(values)
            ),
            "mean_value": float(np.mean(values)),
            "std_value": float(np.std(values)),
            "median_value": float(np.median(values)),
            "total_time_ms": sum(t.duration_ms for t in self._trials),
        }


class ScenarioSpecificTuner(ScenarioTuner):
    """Scenario-specific hyperparameter tuner with presets."""

    PRESETS = {
        "high_density": {
            "collision_threshold": {"type": "uniform", "low": 0.1, "high": 0.5},
            "separation_radius": {"type": "uniform", "low": 5.0, "high": 20.0},
            "response_time_ms": {"type": "uniform", "low": 100, "high": 500},
        },
        "weather_disturbance": {
            "wind_compensation": {"type": "uniform", "low": 0.5, "high": 2.0},
            "safety_margin": {"type": "uniform", "low": 1.2, "high": 3.0},
            "replanning_interval": {"type": "int", "low": 5, "high": 30},
        },
        "emergency_failure": {
            "failover_timeout": {"type": "uniform", "low": 50, "high": 200},
            "recovery_priority": {
                "type": "categorical",
                "choices": ["high", "critical", "immediate"],
            },
            "backup_activation_ms": {"type": "int", "low": 100, "high": 1000},
        },
    }

    def load_preset(self, preset_name: str) -> "ScenarioSpecificTuner":
        """Load a predefined scenario preset."""
        if preset_name not in self.PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}")

        preset = self.PRESETS[preset_name]

        def define_preset(ps: ParameterSpace) -> None:
            for name, config in preset.items():
                ptype = config["type"]
                if ptype == "uniform":
                    ps.add_uniform(name, config["low"], config["high"])
                elif ptype == "log_uniform":
                    ps.add_log_uniform(name, config["low"], config["high"])
                elif ptype == "categorical":
                    ps.add_categorical(name, config["choices"])
                elif ptype == "int":
                    ps.add_int(name, config["low"], config["high"])

        self.define_search_space(define_preset)
        return self


class EnsembleTuner:
    """Tunes multiple scenarios and combines results."""

    def __init__(self) -> None:
        self._tuners: dict[str, ScenarioTuner] = {}
        self._results: dict[str, TuningResult] = {}

    def add_scenario(
        self,
        name: str,
        tuner: ScenarioTuner,
    ) -> "EnsembleTuner":
        """Add a scenario tuner."""
        self._tuners[name] = tuner
        return self

    def run_all(
        self,
        scenario_objectives: dict[str, Callable[[dict[str, Any]], float]],
    ) -> dict[str, TuningResult]:
        """Run tuning for all scenarios."""
        results = {}
        for name, objective in scenario_objectives.items():
            if name in self._tuners:
                tuner = self._tuners[name]
                tuner.set_objective(objective)
                results[name] = tuner.run(study_name=name)
                self._results[name] = results[name]
        return results

    def get_optimal_params(self) -> dict[str, dict[str, Any]]:
        """Get optimal parameters for all scenarios."""
        return {
            name: tuner.get_best_params()
            for name, tuner in self._tuners.items()
            if tuner.get_best_params()
        }

    def export_ensemble_report(self, filepath: str | Path) -> None:
        """Export ensemble tuning report."""
        report = {
            "n_scenarios": len(self._results),
            "scenarios": {
                name: {
                    "best_value": result.best_trial.value
                    if result.best_trial
                    else None,
                    "best_params": result.best_trial.params
                    if result.best_trial
                    else {},
                    "n_trials": len(result.trials),
                }
                for name, result in self._results.items()
            },
            "generated_at": datetime.now().isoformat(),
        }
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
