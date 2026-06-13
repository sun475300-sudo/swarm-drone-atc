"""Tests for scripts/comparison_experiment.py — P706 comparison runner."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.comparison_experiment import (
    RunResult,
    _is_nan,
    _mann_whitney_u,
    _normal_cdf,
    _rank_data,
    aggregate_results,
    discover_scenarios,
    generate_markdown_report,
    significance_tests,
)


def _make_run(
    scenario: str = "01_corridor_crossing",
    method: str = "sdacs_hybrid",
    seed: int = 42,
    **metric_overrides: float,
) -> RunResult:
    metrics: dict[str, float] = {
        "NMR": 0.0,
        "MSD": 12.0,
        "PE": 0.95,
        "MS_s": 80.0,
        "FT_drone_s": 320.0,
        "AU": 0.6,
        "RTF": 15.0,
    }
    metrics.update(metric_overrides)
    return RunResult(
        scenario=scenario,
        method=method,
        seed=seed,
        metrics=metrics,
        wall_seconds=1.5,
    )


class TestRankData:
    def test_distinct_values(self) -> None:
        data = np.array([10.0, 30.0, 20.0])
        ranks = _rank_data(data)
        assert ranks[0] == 1.0
        assert ranks[1] == 3.0
        assert ranks[2] == 2.0

    def test_tied_values(self) -> None:
        data = np.array([5.0, 5.0, 3.0])
        ranks = _rank_data(data)
        assert ranks[2] == 1.0
        assert ranks[0] == 2.5
        assert ranks[1] == 2.5

    def test_single_element(self) -> None:
        ranks = _rank_data(np.array([7.0]))
        assert ranks[0] == 1.0


class TestNormalCdf:
    def test_zero(self) -> None:
        assert abs(_normal_cdf(0.0) - 0.5) < 1e-10

    def test_large_positive(self) -> None:
        assert _normal_cdf(5.0) > 0.999

    def test_large_negative(self) -> None:
        assert _normal_cdf(-5.0) < 0.001


class TestMannWhitneyU:
    def test_identical_samples(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        u, p = _mann_whitney_u(x, x.copy())
        assert p > 0.05

    def test_clearly_different(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
        u, p = _mann_whitney_u(x, y)
        assert p < 0.05

    def test_returns_float_pair(self) -> None:
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([4.0, 5.0, 6.0])
        u, p = _mann_whitney_u(x, y)
        assert isinstance(u, float)
        assert isinstance(p, float)
        assert 0.0 <= p <= 1.0


class TestIsNan:
    def test_none(self) -> None:
        assert _is_nan(None) is True

    def test_nan(self) -> None:
        assert _is_nan(float("nan")) is True

    def test_normal(self) -> None:
        assert _is_nan(1.0) is False

    def test_string(self) -> None:
        assert _is_nan("hello") is True


class TestAggregateResults:
    def test_single_run(self) -> None:
        runs = [_make_run()]
        agg = aggregate_results(runs)
        key = "01_corridor_crossing__sdacs_hybrid"
        assert key in agg
        assert agg[key]["n_runs"] == 1
        assert agg[key]["NMR_mean"] == 0.0

    def test_multiple_seeds(self) -> None:
        runs = [
            _make_run(seed=1, PE=0.90),
            _make_run(seed=2, PE=0.96),
            _make_run(seed=3, PE=0.93),
        ]
        agg = aggregate_results(runs)
        key = "01_corridor_crossing__sdacs_hybrid"
        assert agg[key]["n_runs"] == 3
        assert abs(agg[key]["PE_mean"] - np.mean([0.90, 0.96, 0.93])) < 1e-10

    def test_multiple_methods(self) -> None:
        runs = [
            _make_run(method="sdacs_hybrid"),
            _make_run(method="orca"),
        ]
        agg = aggregate_results(runs)
        assert "01_corridor_crossing__sdacs_hybrid" in agg
        assert "01_corridor_crossing__orca" in agg


class TestSignificanceTests:
    def test_no_ref_returns_empty(self) -> None:
        runs = [_make_run(method="orca", seed=i) for i in range(5)]
        sig = significance_tests(runs, reference="sdacs_hybrid")
        assert sig == []

    def test_produces_entries(self) -> None:
        runs = (
            [_make_run(method="sdacs_hybrid", seed=i, NMR=0.0) for i in range(5)]
            + [_make_run(method="orca", seed=i, NMR=0.01) for i in range(5)]
        )
        sig = significance_tests(runs)
        assert len(sig) > 0
        assert all("p_value" in s for s in sig)
        assert all("sdacs_wins" in s for s in sig)

    def test_sdacs_wins_lower_is_better(self) -> None:
        runs = (
            [_make_run(method="sdacs_hybrid", seed=i, NMR=0.001) for i in range(5)]
            + [_make_run(method="orca", seed=i, NMR=0.1) for i in range(5)]
        )
        sig = significance_tests(runs)
        nmr_entries = [s for s in sig if s["metric"] == "NMR" and s["sdacs_vs"] == "orca"]
        assert len(nmr_entries) == 1
        assert nmr_entries[0]["sdacs_wins"] is True


class TestDiscoverScenarios:
    def test_finds_scenarios(self) -> None:
        scenarios = discover_scenarios()
        assert len(scenarios) >= 1
        assert "01_corridor_crossing" in scenarios


class TestSDACSHybridAdapter:
    """Tests for the real CBS+APF SDACS hybrid adapter."""

    @pytest.fixture(scope="class")
    def manifest(self) -> dict:
        import yaml
        path = REPO_ROOT / "benchmarks" / "scenarios" / "01_corridor_crossing" / "manifest.yaml"
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_adapter_creates_valid_trace(self, manifest: dict) -> None:
        from benchmarks.baselines._base import make_adapter
        adapter = make_adapter("sdacs_hybrid", manifest, seed=42)
        trace = adapter.run(hard_wall_time_s=30.0)
        assert trace.method == "sdacs_hybrid"
        assert len(trace.agents) > 0
        assert trace.wall_clock_seconds > 0

    def test_regulatory_fields_populated(self, manifest: dict) -> None:
        from benchmarks.baselines._base import make_adapter
        adapter = make_adapter("sdacs_hybrid", manifest, seed=42)
        trace = adapter.run(hard_wall_time_s=30.0)
        assert len(trace.remote_id_valid_seconds_per_agent) == len(trace.agents)
        assert len(trace.laanc_request_latencies_ms) == len(trace.agents)
        assert all(80.0 <= lat <= 120.0 for lat in trace.laanc_request_latencies_ms)
        assert len(trace.geofence_violation_timestamps) == 0

    def test_cpa_conflicts_detected(self, manifest: dict) -> None:
        from benchmarks.baselines._base import make_adapter
        adapter = make_adapter("sdacs_hybrid", manifest, seed=42)
        trace = adapter.run(hard_wall_time_s=30.0)
        assert isinstance(trace.predicted_conflicts, list)
        for c in trace.predicted_conflicts:
            assert c.lead_time_s >= 0
            assert c.predicted_min_distance_m >= 0

    def test_voronoi_assignments_per_step(self, manifest: dict) -> None:
        from benchmarks.baselines._base import make_adapter
        adapter = make_adapter("sdacs_hybrid", manifest, seed=42)
        trace = adapter.run(hard_wall_time_s=30.0)
        assert len(trace.voronoi_assignments) > 0
        for step in trace.voronoi_assignments:
            assert isinstance(step, dict)
            for cell in step.values():
                assert cell in (0, 1, 2, 3)

    def test_agents_reach_goals(self, manifest: dict) -> None:
        from benchmarks.baselines._base import make_adapter
        adapter = make_adapter("sdacs_hybrid", manifest, seed=42)
        trace = adapter.run(hard_wall_time_s=60.0)
        arrived = sum(1 for a in trace.agents if a.goal_reached_at_s is not None)
        assert arrived > 0

    def test_rid_compliance_is_perfect(self, manifest: dict) -> None:
        from benchmarks.baselines._base import make_adapter
        from src.analytics.metrics import Evaluator
        adapter = make_adapter("sdacs_hybrid", manifest, seed=42)
        trace = adapter.run(hard_wall_time_s=30.0)
        result = Evaluator().evaluate(trace)
        assert result["RID_CR"] == pytest.approx(1.0)

    def test_deterministic_with_same_seed(self, manifest: dict) -> None:
        from benchmarks.baselines._base import make_adapter
        adapter1 = make_adapter("sdacs_hybrid", manifest, seed=99)
        trace1 = adapter1.run(hard_wall_time_s=30.0)
        adapter2 = make_adapter("sdacs_hybrid", manifest, seed=99)
        trace2 = adapter2.run(hard_wall_time_s=30.0)
        for a1, a2 in zip(trace1.agents, trace2.agents):
            assert len(a1.positions) == len(a2.positions)


class TestGenerateMarkdownReport:
    def test_writes_file(self, tmp_path: Path) -> None:
        runs = (
            [_make_run(method="sdacs_hybrid", seed=i) for i in range(3)]
            + [_make_run(method="orca", seed=i, PE=0.80) for i in range(3)]
        )
        agg = aggregate_results(runs)
        sig = significance_tests(runs)
        out = tmp_path / "report.md"
        generate_markdown_report(agg, sig, out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "P706" in content
        assert "NMR" in content
        assert "sdacs_hybrid" in content
