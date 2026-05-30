"""Phase 701-710: Research / Paper Infrastructure tests.

P703 - Benchmark dataset publication
P704 - Reproducibility package
P705 - Metrics formalization
P706 - Comparison experiments
"""
from __future__ import annotations

import json
import os

import pytest


# ---------------------------------------------------------------------------
# P704 — Reproducibility package
# ---------------------------------------------------------------------------

class TestP704Reproducibility:
    """Phase 704: Reproducibility utilities."""

    def test_reproducible_run_config_import(self):
        from simulation.reproducibility import ReproducibleRunConfig
        cfg = ReproducibleRunConfig(seed=42, n_drones=5, duration_s=10.0)
        assert cfg.seed == 42
        assert cfg.n_drones == 5

    def test_fingerprint_is_deterministic(self):
        from simulation.reproducibility import ReproducibleRunConfig
        cfg1 = ReproducibleRunConfig(seed=42, n_drones=5, duration_s=10.0)
        cfg2 = ReproducibleRunConfig(seed=42, n_drones=5, duration_s=10.0)
        assert cfg1.fingerprint() == cfg2.fingerprint()

    def test_fingerprint_changes_with_seed(self):
        from simulation.reproducibility import ReproducibleRunConfig
        cfg1 = ReproducibleRunConfig(seed=42, n_drones=5, duration_s=10.0)
        cfg2 = ReproducibleRunConfig(seed=43, n_drones=5, duration_s=10.0)
        assert cfg1.fingerprint() != cfg2.fingerprint()

    def test_fingerprint_length(self):
        from simulation.reproducibility import ReproducibleRunConfig
        cfg = ReproducibleRunConfig(seed=1, n_drones=10, duration_s=30.0)
        assert len(cfg.fingerprint()) == 16

    def test_set_deterministic_env(self):
        from simulation.reproducibility import set_deterministic_env
        set_deterministic_env(42)
        assert os.environ.get("PYTHONHASHSEED") == "42"

    def test_result_to_dict_roundtrip(self):
        import time
        from simulation.reproducibility import ReproducibleRunConfig, ReproducibleRunResult
        cfg = ReproducibleRunConfig(seed=7, n_drones=3, duration_s=5.0)
        result = ReproducibleRunResult(
            config=cfg,
            collision_count=0,
            near_miss_count=2,
            conflict_resolution_rate_pct=100.0,
            total_distance_m=1500.0,
            wall_time_s=0.5,
            created_at="2026-05-30T00:00:00Z",
        )
        d = result.to_dict()
        assert "fingerprint" in d
        assert d["collision_count"] == 0
        assert d["near_miss_count"] == 2

        restored = ReproducibleRunResult.from_dict(d)
        assert restored.config.seed == 7
        assert restored.near_miss_count == 2

    def test_save_and_load_result(self, tmp_path):
        from simulation.reproducibility import (
            ReproducibleRunConfig,
            ReproducibleRunResult,
            load_result,
            save_result,
        )
        cfg = ReproducibleRunConfig(seed=99, n_drones=10, duration_s=20.0)
        result = ReproducibleRunResult(
            config=cfg,
            collision_count=1,
            near_miss_count=3,
            conflict_resolution_rate_pct=90.0,
            total_distance_m=3000.0,
            wall_time_s=1.2,
            created_at="2026-05-30T12:00:00Z",
        )
        path = save_result(result, str(tmp_path))
        assert path.exists()

        loaded = load_result(str(path))
        assert loaded.collision_count == 1
        assert loaded.config.n_drones == 10


# ---------------------------------------------------------------------------
# P705 — Formal metrics
# ---------------------------------------------------------------------------

class TestP705FormalMetrics:
    """Phase 705: Formal evaluation metrics."""

    def test_near_miss_rate_zero_when_no_events(self):
        from simulation.formal_metrics import compute_near_miss_rate
        assert compute_near_miss_rate(0, 10, 60.0) == 0.0

    def test_near_miss_rate_calculation(self):
        from simulation.formal_metrics import compute_near_miss_rate
        rate = compute_near_miss_rate(near_miss_count=6, n_drones=10, duration_s=60.0)
        assert pytest.approx(rate, abs=1e-9) == 0.6

    def test_collision_rate_calculation(self):
        from simulation.formal_metrics import compute_collision_rate
        rate = compute_collision_rate(collision_count=2, n_drones=10, duration_s=60.0)
        assert pytest.approx(rate, abs=1e-9) == 0.2

    def test_conflict_resolution_rate_no_events(self):
        from simulation.formal_metrics import compute_conflict_resolution_rate
        assert compute_conflict_resolution_rate(0, 0) == 1.0

    def test_conflict_resolution_rate_perfect(self):
        from simulation.formal_metrics import compute_conflict_resolution_rate
        assert compute_conflict_resolution_rate(0, 10) == 1.0

    def test_conflict_resolution_rate_formula(self):
        from simulation.formal_metrics import compute_conflict_resolution_rate
        # 2 collisions, 8 conflicts → rate = 1 - 2/(8+2) = 0.8
        rate = compute_conflict_resolution_rate(collisions=2, conflicts_total=8)
        assert pytest.approx(rate) == 0.8

    def test_path_efficiency_perfect(self):
        from simulation.formal_metrics import compute_path_efficiency
        assert compute_path_efficiency(1000.0, 1000.0) == 1.0

    def test_path_efficiency_detour(self):
        from simulation.formal_metrics import compute_path_efficiency
        eff = compute_path_efficiency(planned_distance_m=1000.0, actual_distance_m=1200.0)
        assert eff < 1.0
        assert pytest.approx(eff, abs=1e-3) == 1000.0 / 1200.0

    def test_airspace_utilization(self):
        from simulation.formal_metrics import compute_airspace_utilization
        util = compute_airspace_utilization(occupied_cells=50, total_cells=200)
        assert pytest.approx(util) == 0.25

    def test_airspace_utilization_zero_cells(self):
        from simulation.formal_metrics import compute_airspace_utilization
        assert compute_airspace_utilization(0, 0) == 0.0

    def test_formal_metrics_dataclass(self):
        from simulation.formal_metrics import FormalMetrics
        m = FormalMetrics(
            near_miss_rate=0.1,
            collision_rate=0.0,
            conflict_resolution_rate=0.95,
            airspace_utilization=0.3,
            path_efficiency=0.92,
            throughput_mpm=5.0,
            mean_advisory_latency_ms=50.0,
            controller_hz=1.0,
        )
        d = m.to_dict()
        assert "near_miss_rate" in d
        assert "collision_rate" in d
        assert len(d) == 8

    def test_from_simulation_result(self):
        from simulation.formal_metrics import from_simulation_result
        sim_result = {
            "collision_count": 2,
            "near_miss_count": 10,
            "conflicts_total": 18,
            "total_planned_distance_m": 5000.0,
            "total_distance_m": 5500.0,
            "routes_completed": 8,
            "mean_advisory_latency_ms": 75.0,
            "controller_hz": 1.0,
        }
        metrics = from_simulation_result(sim_result, n_drones=10, duration_s=120.0)
        assert metrics.collision_rate > 0
        assert 0.0 <= metrics.conflict_resolution_rate <= 1.0
        assert metrics.path_efficiency <= 1.0

    def test_compare_algorithms(self):
        from simulation.formal_metrics import FormalMetrics, compare_algorithms
        baseline = FormalMetrics(
            near_miss_rate=0.5, collision_rate=0.1,
            conflict_resolution_rate=0.7, airspace_utilization=0.4,
            path_efficiency=0.85, throughput_mpm=3.0,
            mean_advisory_latency_ms=100.0, controller_hz=1.0,
        )
        proposed = FormalMetrics(
            near_miss_rate=0.3, collision_rate=0.0,
            conflict_resolution_rate=0.95, airspace_utilization=0.35,
            path_efficiency=0.92, throughput_mpm=4.0,
            mean_advisory_latency_ms=60.0, controller_hz=1.0,
        )
        comp = compare_algorithms(baseline, proposed)
        assert comp["conflict_resolution_delta"] > 0
        assert comp["near_miss_rate_delta"] > 0
        assert comp["path_efficiency_delta"] > 0


# ---------------------------------------------------------------------------
# P703 — Benchmark dataset
# ---------------------------------------------------------------------------

class TestP703BenchmarkDataset:
    """Phase 703: Benchmark dataset publication."""

    def test_benchmark_suite_import(self):
        from simulation.benchmark_suite import BenchmarkSuite
        bs = BenchmarkSuite()
        assert bs is not None

    def test_benchmark_run(self):
        from simulation.benchmark_suite import BenchmarkSuite
        bs = BenchmarkSuite()
        result = bs.run_benchmark("test_op", lambda: sum(range(100)), iterations=10)
        assert result.mean_ms >= 0
        assert result.throughput > 0

    def test_benchmark_report_generation(self):
        from simulation.benchmark_suite import BenchmarkSuite
        bs = BenchmarkSuite()
        bs.run_benchmark("op_a", lambda: sum(range(50)), iterations=5)
        report = bs.report()
        assert "op_a" in report

    def test_benchmark_baseline_comparison(self):
        from simulation.benchmark_suite import BenchmarkSuite
        bs = BenchmarkSuite()
        r = bs.run_benchmark("op_b", lambda: sum(range(50)), iterations=5)
        bs.set_baseline("op_b")
        comp = bs.compare_with_baseline("op_b")
        assert comp is not None
        assert "speedup" in comp
        assert "regression" in comp

    def test_benchmark_regression_detection(self):
        from simulation.benchmark_suite import BenchmarkSuite
        bs = BenchmarkSuite()
        bs.run_benchmark("fast", lambda: None, iterations=10)
        bs.set_baseline("fast")
        regressions = bs.detect_regressions()
        assert isinstance(regressions, list)

    def test_benchmark_summary(self):
        from simulation.benchmark_suite import BenchmarkSuite
        bs = BenchmarkSuite()
        bs.run_benchmark("work", lambda: [x**2 for x in range(10)], iterations=5)
        s = bs.summary()
        assert s["total_benchmarks"] == 1

    def test_benchmark_dataset_json_serializable(self, tmp_path):
        from simulation.benchmark_suite import BenchmarkSuite
        bs = BenchmarkSuite()
        bs.run_benchmark("serialize_test", lambda: sum(range(20)), iterations=5)
        results = {k: {
            "mean_ms": v.mean_ms,
            "p95_ms": v.p95_ms,
            "throughput": v.throughput,
        } for k, v in bs.all_results().items()}
        out = tmp_path / "benchmark.json"
        out.write_text(json.dumps(results))
        loaded = json.loads(out.read_text())
        assert "serialize_test" in loaded


# ---------------------------------------------------------------------------
# P706 — Comparison experiments
# ---------------------------------------------------------------------------

class TestP706Comparison:
    """Phase 706: Comparison with baseline algorithms."""

    def test_formal_metrics_comparison_structure(self):
        from simulation.formal_metrics import FormalMetrics, compare_algorithms
        baseline = FormalMetrics(
            near_miss_rate=1.0, collision_rate=0.2,
            conflict_resolution_rate=0.6, airspace_utilization=0.5,
            path_efficiency=0.8, throughput_mpm=2.0,
            mean_advisory_latency_ms=200.0, controller_hz=1.0,
        )
        proposed = FormalMetrics(
            near_miss_rate=0.5, collision_rate=0.05,
            conflict_resolution_rate=0.92, airspace_utilization=0.45,
            path_efficiency=0.9, throughput_mpm=3.0,
            mean_advisory_latency_ms=80.0, controller_hz=1.0,
        )
        comp = compare_algorithms(baseline, proposed)
        required_keys = {
            "near_miss_rate_delta", "collision_rate_delta",
            "conflict_resolution_delta", "path_efficiency_delta",
            "airspace_utilization_delta", "throughput_delta",
        }
        assert required_keys.issubset(comp.keys())

    def test_comparison_shows_improvement_when_better(self):
        from simulation.formal_metrics import FormalMetrics, compare_algorithms
        baseline = FormalMetrics(
            near_miss_rate=2.0, collision_rate=0.5,
            conflict_resolution_rate=0.5, airspace_utilization=0.6,
            path_efficiency=0.7, throughput_mpm=1.0,
            mean_advisory_latency_ms=300.0, controller_hz=1.0,
        )
        proposed = FormalMetrics(
            near_miss_rate=0.5, collision_rate=0.0,
            conflict_resolution_rate=0.95, airspace_utilization=0.4,
            path_efficiency=0.9, throughput_mpm=4.0,
            mean_advisory_latency_ms=50.0, controller_hz=1.0,
        )
        comp = compare_algorithms(baseline, proposed)
        # Better algorithm should show positive deltas in key metrics
        assert comp["near_miss_rate_delta"] > 0
        assert comp["conflict_resolution_delta"] > 0
        assert comp["path_efficiency_delta"] > 0

    def test_comparison_equal_algorithms(self):
        from simulation.formal_metrics import FormalMetrics, compare_algorithms
        m = FormalMetrics(
            near_miss_rate=1.0, collision_rate=0.1,
            conflict_resolution_rate=0.9, airspace_utilization=0.3,
            path_efficiency=0.95, throughput_mpm=5.0,
            mean_advisory_latency_ms=50.0, controller_hz=1.0,
        )
        comp = compare_algorithms(m, m)
        # Same algorithm should have zero deltas
        assert pytest.approx(comp["near_miss_rate_delta"], abs=1e-9) == 0.0
        assert pytest.approx(comp["conflict_resolution_delta"], abs=1e-9) == 0.0
