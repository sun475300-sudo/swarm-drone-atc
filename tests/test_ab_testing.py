"""Phase 200-219 tests: A/B Testing Framework."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest


class TestABTestRunner:
    def test_init_defaults(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        assert runner._n_samples == 100
        assert runner._confidence == 0.95

    def test_init_custom(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner(n_samples=50, confidence_level=0.99, seed=42)
        assert runner._n_samples == 50
        assert runner._confidence == 0.99
        assert runner._rng is not None

    def test_add_variant(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        runner.add_variant("control", [1.0, 2.0, 3.0])
        runner.add_variant("treatment", [2.0, 3.0, 4.0])
        assert "control" in runner._results
        assert "treatment" in runner._results

    def test_run_ttest(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        runner.add_variant("control", [1.0, 2.0, 3.0, 4.0, 5.0])
        runner.add_variant("treatment", [2.0, 3.0, 4.0, 5.0, 6.0])
        t, p = runner.run_ttest("control", "treatment")
        assert isinstance(t, float)
        assert isinstance(p, float)

    def test_run_ttest_insufficient_data(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        runner.add_variant("control", [1.0])
        runner.add_variant("treatment", [2.0])
        t, p = runner.run_ttest("control", "treatment")
        assert t == 0.0
        assert p == 1.0

    def test_calculate_effect_size(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        runner.add_variant("control", [1.0, 2.0, 3.0, 4.0, 5.0])
        runner.add_variant("treatment", [10.0, 11.0, 12.0, 13.0, 14.0])
        effect = runner.calculate_effect_size("control", "treatment")
        assert effect > 1.0

    def test_compare(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner(confidence_level=0.95)
        runner.add_variant("control", [1.0, 2.0, 3.0, 4.0, 5.0])
        runner.add_variant("treatment", [5.0, 6.0, 7.0, 8.0, 9.0])
        result = runner.compare("control", "treatment")
        assert "control_mean" in result
        assert "treatment_mean" in result
        assert "p_value" in result
        assert "significant" in result
        assert "effect_size" in result

    def test_interpret_effect(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        assert runner._interpret_effect(0.1) == "negligible"
        assert runner._interpret_effect(0.3) == "small"
        assert runner._interpret_effect(0.6) == "medium"
        assert runner._interpret_effect(1.0) == "large"

    def test_get_summary(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        runner.add_variant("control", [1.0, 2.0, 3.0, 4.0, 5.0])
        runner.add_variant("treatment", [2.0, 3.0, 4.0, 5.0, 6.0])
        summary = runner.get_summary()
        assert "control" in summary
        assert "treatment" in summary
        assert summary["control"]["n"] == 5
        assert summary["control"]["mean"] == 3.0

    def test_export_results(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        runner.add_variant("control", [1.0, 2.0, 3.0])
        runner.add_variant("treatment", [2.0, 3.0, 4.0])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            runner.export_results(filepath)
            with open(filepath) as f:
                data = json.load(f)
            assert "variants" in data
            assert "control" in data["variants"]
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestMultiArmedBandit:
    def test_init(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a", "b", "c"])
        assert len(bandit._arms) == 3
        assert bandit._epsilon == 0.1

    def test_init_custom_epsilon(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a", "b"], epsilon=0.2)
        assert bandit._epsilon == 0.2

    def test_select_arm_explore(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a", "b"], epsilon=1.0, seed=42)
        arm = bandit.select_arm()
        assert arm in ["a", "b"]

    def test_select_arm_exploit(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a", "b"], epsilon=0.0)
        bandit._values["a"] = 1.0
        bandit._values["b"] = 0.5
        arm = bandit.select_arm()
        assert arm == "a"

    def test_update(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a", "b"])
        bandit.update("a", 1.0)
        assert bandit._counts["a"] == 1
        assert bandit._values["a"] == 1.0

    def test_update_multiple(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a"])
        bandit.update("a", 1.0)
        bandit.update("a", 2.0)
        bandit.update("a", 3.0)
        assert bandit._counts["a"] == 3
        assert bandit._values["a"] == 2.0

    def test_get_best_arm(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a", "b", "c"])
        bandit._values = {"a": 0.5, "b": 0.8, "c": 0.3}
        assert bandit.get_best_arm() == "b"

    def test_get_statistics(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a", "b"], seed=42)
        bandit.select_arm()
        stats = bandit.get_statistics()
        assert "arms" in stats
        assert "counts" in stats
        assert "values" in stats
        assert "best_arm" in stats


class TestScenarioABComparator:
    def test_init(self):
        from simulation.ab_testing import ScenarioABComparator

        comparator = ScenarioABComparator()
        assert comparator._comparisons == {}

    def test_scenarios_defined(self):
        from simulation.ab_testing import ScenarioABComparator

        assert "high_density" in ScenarioABComparator.SCENARIOS
        assert "weather_disturbance" in ScenarioABComparator.SCENARIOS
        assert "emergency_failure" in ScenarioABComparator.SCENARIOS

    def test_add_comparison(self):
        from simulation.ab_testing import ScenarioABComparator

        comparator = ScenarioABComparator()
        comparator.add_comparison("high_density", "apf", 0.05)
        comparator.add_comparison("high_density", "cbs", 0.03)
        assert "high_density" in comparator._comparisons
        assert comparator._comparisons["high_density"]["apf"] == 0.05

    def test_compare_algorithms_minimize(self):
        from simulation.ab_testing import ScenarioABComparator

        comparator = ScenarioABComparator()
        comparator.add_comparison("high_density", "apf", 0.05)
        comparator.add_comparison("high_density", "cbs", 0.03)
        result = comparator.compare_algorithms("high_density", "apf", "cbs")
        assert result["winner"] == "cbs"
        assert result["improvement_pct"] > 0

    def test_compare_algorithms_error(self):
        from simulation.ab_testing import ScenarioABComparator

        comparator = ScenarioABComparator()
        result = comparator.compare_algorithms("unknown", "a", "b")
        assert "error" in result

    def test_get_ranking_minimize(self):
        from simulation.ab_testing import ScenarioABComparator

        comparator = ScenarioABComparator()
        comparator.add_comparison("high_density", "apf", 0.05)
        comparator.add_comparison("high_density", "cbs", 0.03)
        comparator.add_comparison("high_density", "orca", 0.04)
        ranking = comparator.get_ranking("high_density")
        assert ranking[0][0] == "cbs"
        assert ranking[1][0] == "orca"
        assert ranking[2][0] == "apf"

    def test_get_ranking_empty(self):
        from simulation.ab_testing import ScenarioABComparator

        comparator = ScenarioABComparator()
        ranking = comparator.get_ranking("unknown")
        assert ranking == []

    def test_export_comparison_matrix(self):
        from simulation.ab_testing import ScenarioABComparator

        comparator = ScenarioABComparator()
        comparator.add_comparison("high_density", "apf", 0.05)
        comparator.add_comparison("high_density", "cbs", 0.03)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            comparator.export_comparison_matrix(filepath)
            with open(filepath) as f:
                data = json.load(f)
            assert "comparisons" in data
            assert "rankings" in data
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestABTestingEdgeCases:
    def test_empty_runner(self):
        from simulation.ab_testing import ABTestRunner

        runner = ABTestRunner()
        summary = runner.get_summary()
        assert summary == {}

    def test_bandit_zero_counts(self):
        from simulation.ab_testing import MultiArmedBandit

        bandit = MultiArmedBandit(["a", "b"])
        stats = bandit.get_statistics()
        assert stats["total_selections"] == 0

    def test_comparator_multiple_scenarios(self):
        from simulation.ab_testing import ScenarioABComparator

        comparator = ScenarioABComparator()
        comparator.add_comparison("high_density", "apf", 0.05)
        comparator.add_comparison("weather_disturbance", "apf", 0.10)
        comparator.add_comparison("emergency_failure", "apf", 2.0)
        assert len(comparator._comparisons) == 3
