"""Phase 200-219 tests: Hyperparameter Tuning Framework."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest


class TestTuningConfig:
    def test_default_config(self):
        from simulation.hyperparameter_tuner import TuningConfig

        config = TuningConfig()
        assert config.n_trials == 100
        assert config.timeout_seconds is None
        assert config.n_jobs == 1
        assert config.sampler == "TPE"
        assert config.pruner == "Median"
        assert config.direction == "maximize"
        assert config.seed == 42

    def test_custom_config(self):
        from simulation.hyperparameter_tuner import TuningConfig

        config = TuningConfig(
            n_trials=50,
            timeout_seconds=300,
            direction="minimize",
            seed=123,
        )
        assert config.n_trials == 50
        assert config.timeout_seconds == 300
        assert config.direction == "minimize"
        assert config.seed == 123


class TestTuningTrial:
    def test_trial_creation(self):
        from simulation.hyperparameter_tuner import TuningTrial

        trial = TuningTrial(
            trial_id=0,
            params={"lr": 0.01, "layers": 3},
            value=0.95,
        )
        assert trial.trial_id == 0
        assert trial.params["lr"] == 0.01
        assert trial.value == 0.95
        assert trial.state == "completed"
        assert trial.duration_ms == 0.0
        assert trial.timestamp is not None

    def test_failed_trial(self):
        from simulation.hyperparameter_tuner import TuningTrial

        trial = TuningTrial(
            trial_id=1,
            params={},
            value=-float("inf"),
            state="failed",
            duration_ms=150.5,
        )
        assert trial.state == "failed"
        assert trial.duration_ms == 150.5


class TestTuningResult:
    def test_result_with_trials(self):
        from simulation.hyperparameter_tuner import (
            TuningConfig,
            TuningResult,
            TuningTrial,
        )

        config = TuningConfig()
        trials = [
            TuningTrial(trial_id=0, params={"x": 1.0}, value=0.5),
            TuningTrial(trial_id=1, params={"x": 2.0}, value=0.8),
        ]
        result = TuningResult(
            config=config,
            trials=trials,
            best_trial=trials[1],
            study_name="test_study",
        )
        assert result.config == config
        assert len(result.trials) == 2
        assert result.best_trial == trials[1]
        assert result.study_name == "test_study"


class TestParameterSpace:
    def test_add_uniform(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_uniform("lr", 0.001, 0.1)
        assert "lr" in ps._spaces
        assert ps._spaces["lr"]["type"] == "uniform"
        assert ps._spaces["lr"]["low"] == 0.001
        assert ps._spaces["lr"]["high"] == 0.1

    def test_add_log_uniform(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_log_uniform("lr", 1e-5, 1e-1)
        assert "lr" in ps._spaces
        assert ps._spaces["lr"]["type"] == "log_uniform"

    def test_add_categorical(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_categorical("optimizer", ["adam", "sgd", "rmsprop"])
        assert "optimizer" in ps._spaces
        assert ps._spaces["optimizer"]["type"] == "categorical"
        assert len(ps._spaces["optimizer"]["choices"]) == 3

    def test_add_int(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_int("num_layers", 1, 10)
        assert "num_layers" in ps._spaces
        assert ps._spaces["num_layers"]["type"] == "int"

    def test_sample_uniform(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_uniform("lr", 0.001, 0.1)
        rng = np.random.default_rng(42)
        params = ps.sample(rng)
        assert "lr" in params
        assert 0.001 <= params["lr"] <= 0.1

    def test_sample_log_uniform(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_log_uniform("lr", 1e-5, 1e-1)
        rng = np.random.default_rng(42)
        params = ps.sample(rng)
        assert "lr" in params
        assert 1e-5 <= params["lr"] <= 1e-1

    def test_sample_categorical(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_categorical("optimizer", ["adam", "sgd"])
        rng = np.random.default_rng(42)
        params = ps.sample(rng)
        assert "optimizer" in params
        assert params["optimizer"] in ["adam", "sgd"]

    def test_sample_int(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_int("num_layers", 1, 10)
        rng = np.random.default_rng(42)
        params = ps.sample(rng)
        assert "num_layers" in params
        assert 1 <= params["num_layers"] <= 10

    def test_sample_multiple_params(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_uniform("lr", 0.001, 0.1)
        ps.add_int("layers", 1, 10)
        ps.add_categorical("opt", ["a", "b"])
        rng = np.random.default_rng(42)
        params = ps.sample(rng)
        assert len(params) == 3

    def test_suggest_with_params(self):
        from simulation.hyperparameter_tuner import ParameterSpace, TuningTrial

        ps = ParameterSpace()
        ps.add_uniform("lr", 0.001, 0.1)
        trial = TuningTrial(trial_id=0, params={"lr": 0.05}, value=0.8)
        value = ps.suggest(trial, "lr")
        assert value == 0.05

    def test_suggest_without_params(self):
        from simulation.hyperparameter_tuner import ParameterSpace, TuningTrial

        ps = ParameterSpace()
        ps.add_uniform("lr", 0.001, 0.1)
        trial = TuningTrial(trial_id=0, params={}, value=0.0)
        value = ps.suggest(trial, "lr")
        assert abs(value - 0.0505) < 0.01

    def test_suggest_invalid_param(self):
        from simulation.hyperparameter_tuner import ParameterSpace, TuningTrial

        ps = ParameterSpace()
        ps.add_uniform("lr", 0.001, 0.1)
        trial = TuningTrial(trial_id=0, params={}, value=0.0)
        with pytest.raises(ValueError, match="not in search space"):
            ps.suggest(trial, "nonexistent")


class TestScenarioTuner:
    def test_init_default(self):
        from simulation.hyperparameter_tuner import ScenarioTuner

        tuner = ScenarioTuner()
        assert tuner._config is not None
        assert tuner._param_space is not None
        assert tuner._objective is None

    def test_init_custom_config(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=10)
        tuner = ScenarioTuner(config)
        assert tuner._config.n_trials == 10

    def test_define_search_space(self):
        from simulation.hyperparameter_tuner import ScenarioTuner

        tuner = ScenarioTuner()
        tuner.define_search_space(
            lambda ps: (
                ps.add_uniform("lr", 0.001, 0.1),
                ps.add_int("layers", 1, 10),
            )
        )
        assert "lr" in tuner._param_space._spaces
        assert "layers" in tuner._param_space._spaces

    def test_set_objective(self):
        from simulation.hyperparameter_tuner import ScenarioTuner

        tuner = ScenarioTuner()

        def objective(params):
            return -(params.get("x", 0) ** 2)

        tuner.set_objective(objective)
        assert tuner._objective is not None

    def test_run_without_objective_raises(self):
        from simulation.hyperparameter_tuner import ScenarioTuner

        tuner = ScenarioTuner()
        with pytest.raises(ValueError, match="Objective function not set"):
            tuner.run()

    def test_run_with_simple_objective(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=5, direction="maximize")
        tuner = ScenarioTuner(config)
        tuner.define_search_space(lambda ps: ps.add_uniform("x", -10.0, 10.0))

        def objective(params):
            return -((params["x"] - 3.0) ** 2)

        tuner.set_objective(objective)
        result = tuner.run("test_study")
        assert len(result.trials) == 5
        assert result.best_trial is not None
        assert result.study_name == "test_study"

    def test_run_with_timeout(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=10, timeout_seconds=3)
        tuner = ScenarioTuner(config)
        tuner.define_search_space(lambda ps: ps.add_uniform("x", 0.0, 1.0))

        def objective(params):
            import time

            time.sleep(0.5)
            return params["x"]

        tuner.set_objective(objective)
        result = tuner.run()
        assert 1 <= len(result.trials) <= 10

    def test_run_minimize_direction(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=10, direction="minimize")
        tuner = ScenarioTuner(config)
        tuner.define_search_space(lambda ps: ps.add_uniform("x", -10.0, 10.0))

        def objective(params):
            return (params["x"] - 3.0) ** 2

        tuner.set_objective(objective)
        result = tuner.run()
        assert abs(result.best_trial.params["x"] - 3.0) < 2.0

    def test_run_with_failed_objective(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=5)
        tuner = ScenarioTuner(config)
        tuner.define_search_space(lambda ps: ps.add_uniform("x", 0.0, 1.0))

        def objective(params):
            raise ValueError("Objective failed")

        tuner.set_objective(objective)
        result = tuner.run()
        assert all(t.state == "failed" for t in result.trials)

    def test_get_best_params(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=5)
        tuner = ScenarioTuner(config)
        tuner.define_search_space(lambda ps: ps.add_uniform("x", 0.0, 1.0))
        tuner.set_objective(lambda p: p["x"])
        tuner.run()

        best = tuner.get_best_params()
        assert "x" in best

    def test_get_best_params_before_run(self):
        from simulation.hyperparameter_tuner import ScenarioTuner

        tuner = ScenarioTuner()
        assert tuner.get_best_params() == {}

    def test_export_results(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=3)
        tuner = ScenarioTuner(config)
        tuner.define_search_space(lambda ps: ps.add_uniform("x", 0.0, 1.0))
        tuner.set_objective(lambda p: p["x"])
        tuner.run()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            tuner.export_results(filepath)
            with open(filepath) as f:
                data = json.load(f)
            assert "config" in data
            assert "trials" in data
            assert len(data["trials"]) == 3
            assert data["n_trials"] == 3
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_get_statistics(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=5)
        tuner = ScenarioTuner(config)
        tuner.define_search_space(lambda ps: ps.add_uniform("x", 0.0, 1.0))

        def objective(params):
            return params["x"] * 2

        tuner.set_objective(objective)
        tuner.run()
        stats = tuner.get_statistics()
        assert stats["n_trials"] == 5
        assert stats["n_completed"] == 5
        assert stats["n_failed"] == 0
        assert "best_value" in stats
        assert "mean_value" in stats


class TestScenarioSpecificTuner:
    def test_presets_exist(self):
        from simulation.hyperparameter_tuner import ScenarioSpecificTuner

        assert "high_density" in ScenarioSpecificTuner.PRESETS
        assert "weather_disturbance" in ScenarioSpecificTuner.PRESETS
        assert "emergency_failure" in ScenarioSpecificTuner.PRESETS

    def test_load_high_density_preset(self):
        from simulation.hyperparameter_tuner import ScenarioSpecificTuner

        tuner = ScenarioSpecificTuner()
        tuner.load_preset("high_density")
        assert "collision_threshold" in tuner._param_space._spaces
        assert "separation_radius" in tuner._param_space._spaces

    def test_load_weather_preset(self):
        from simulation.hyperparameter_tuner import ScenarioSpecificTuner

        tuner = ScenarioSpecificTuner()
        tuner.load_preset("weather_disturbance")
        assert "wind_compensation" in tuner._param_space._spaces
        assert "safety_margin" in tuner._param_space._spaces

    def test_load_emergency_preset(self):
        from simulation.hyperparameter_tuner import ScenarioSpecificTuner

        tuner = ScenarioSpecificTuner()
        tuner.load_preset("emergency_failure")
        assert "failover_timeout" in tuner._param_space._spaces
        assert "recovery_priority" in tuner._param_space._spaces

    def test_load_invalid_preset_raises(self):
        from simulation.hyperparameter_tuner import ScenarioSpecificTuner

        tuner = ScenarioSpecificTuner()
        with pytest.raises(ValueError, match="Unknown preset"):
            tuner.load_preset("nonexistent")

    def test_preset_tuning(self):
        from simulation.hyperparameter_tuner import ScenarioSpecificTuner

        tuner = ScenarioSpecificTuner()
        tuner.load_preset("high_density")
        tuner.set_objective(lambda p: -p.get("collision_threshold", 0.5))
        result = tuner.run()
        assert len(result.trials) > 0


class TestEnsembleTuner:
    def test_add_scenario(self):
        from simulation.hyperparameter_tuner import EnsembleTuner, ScenarioTuner

        ensemble = EnsembleTuner()
        tuner = ScenarioTuner()
        ensemble.add_scenario("scenario_a", tuner)
        assert "scenario_a" in ensemble._tuners

    def test_run_all(self):
        from simulation.hyperparameter_tuner import EnsembleTuner, ScenarioTuner

        ensemble = EnsembleTuner()

        tuner_a = ScenarioTuner()
        tuner_a.define_search_space(lambda ps: ps.add_uniform("x", 0, 1))

        tuner_b = ScenarioTuner()
        tuner_b.define_search_space(lambda ps: ps.add_uniform("y", 0, 1))

        ensemble.add_scenario("a", tuner_a)
        ensemble.add_scenario("b", tuner_b)

        objectives = {
            "a": lambda p: p.get("x", 0),
            "b": lambda p: p.get("y", 0),
        }

        results = ensemble.run_all(objectives)
        assert "a" in results
        assert "b" in results

    def test_get_optimal_params(self):
        from simulation.hyperparameter_tuner import EnsembleTuner, ScenarioTuner

        ensemble = EnsembleTuner()

        tuner = ScenarioTuner()
        tuner.define_search_space(lambda ps: ps.add_uniform("x", 0, 1))
        tuner.set_objective(lambda p: p.get("x", 0))
        tuner.run()

        ensemble.add_scenario("test", tuner)
        optimal = ensemble.get_optimal_params()
        assert "test" in optimal

    def test_export_ensemble_report(self):
        from simulation.hyperparameter_tuner import EnsembleTuner, ScenarioTuner

        ensemble = EnsembleTuner()
        tuner = ScenarioTuner()
        tuner.define_search_space(lambda ps: ps.add_uniform("x", 0, 1))
        tuner.set_objective(lambda p: p.get("x", 0))
        tuner.run()
        ensemble.add_scenario("test", tuner)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            ensemble.export_ensemble_report(filepath)
            with open(filepath) as f:
                data = json.load(f)
            assert data["n_scenarios"] == 1
            assert "test" in data["scenarios"]
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestHyperparameterTunerEdgeCases:
    def test_empty_search_space(self):
        from simulation.hyperparameter_tuner import ScenarioTuner, TuningConfig

        config = TuningConfig(n_trials=3)
        tuner = ScenarioTuner(config)

        def objective(params):
            return 0.5

        tuner.set_objective(objective)
        result = tuner.run()
        assert len(result.trials) == 3

    def test_chained_methods(self):
        from simulation.hyperparameter_tuner import ScenarioTuner

        tuner = (
            ScenarioTuner()
            .define_search_space(lambda ps: ps.add_uniform("x", 0, 1))
            .set_objective(lambda p: p.get("x", 0))
        )
        assert tuner._objective is not None

    def test_all_parameter_types_sample(self):
        from simulation.hyperparameter_tuner import ParameterSpace

        ps = ParameterSpace()
        ps.add_uniform("u", 0.0, 1.0)
        ps.add_log_uniform("lu", 1e-4, 1e-1)
        ps.add_categorical("c", ["a", "b", "c"])
        ps.add_int("i", 1, 100)

        rng = np.random.default_rng(42)
        params = ps.sample(rng)
        assert len(params) == 4
        assert 0.0 <= params["u"] <= 1.0
        assert 1e-4 <= params["lu"] <= 1e-1
        assert params["c"] in ["a", "b", "c"]
        assert 1 <= params["i"] <= 100
