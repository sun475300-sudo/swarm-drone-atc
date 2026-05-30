"""P717 부하 테스트 단위 검증."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from tests.load.load_test_swarm import run_local_benchmark, LoadTestResult, _make_frame
import numpy as np


@pytest.mark.unit
class TestLoadTestResult:
    def test_pass_condition(self):
        r = LoadTestResult(
            n_drones=100, duration_s=5.0, target_hz=10,
            frames_sent=5000, frames_per_s=1000.0,
            p50_ms=1.0, p95_ms=2.0, p99_ms=3.0, max_ms=5.0,
            target_fps=60.0,
        )
        assert r.passed

    def test_fail_condition(self):
        r = LoadTestResult(
            n_drones=100, duration_s=5.0, target_hz=10,
            frames_sent=100, frames_per_s=20.0,
            p50_ms=50.0, p95_ms=100.0, p99_ms=150.0, max_ms=200.0,
            target_fps=60.0,
        )
        assert not r.passed

    def test_report_contains_status(self):
        r = LoadTestResult(
            n_drones=10, duration_s=1.0, target_hz=10,
            frames_sent=100, frames_per_s=100.0,
            p50_ms=1.0, p95_ms=2.0, p99_ms=3.0, max_ms=5.0,
            target_fps=60.0,
        )
        report = r.report()
        assert "PASS" in report or "FAIL" in report
        assert "Drones" in report


@pytest.mark.unit
class TestMakeFrame:
    def test_frame_has_required_fields(self):
        rng = np.random.default_rng(42)
        frame = _make_frame("D-001", 1.0, rng)
        for key in ("drone_id", "timestamp", "x", "y", "z", "vx", "vy", "vz", "battery", "state"):
            assert key in frame

    def test_battery_decreases_over_time(self):
        rng = np.random.default_rng(42)
        frame_early = _make_frame("D-001", 0.0, rng)
        frame_late = _make_frame("D-001", 1000.0, np.random.default_rng(42))
        assert frame_early["battery"] > frame_late["battery"]


@pytest.mark.slow
@pytest.mark.unit
class TestLocalBenchmark:
    def test_benchmark_runs(self):
        result = run_local_benchmark(n_drones=10, duration_s=1.0, target_hz=5)
        assert result.frames_sent > 0
        assert result.frames_per_s > 0
        assert result.p50_ms >= 0
        assert result.duration_s >= 1.0

    def test_benchmark_scales_with_drones(self):
        r10 = run_local_benchmark(n_drones=10, duration_s=1.0, target_hz=5)
        r50 = run_local_benchmark(n_drones=50, duration_s=1.0, target_hz=5)
        # More drones → more frames in same time
        assert r50.frames_sent > r10.frames_sent

    def test_benchmark_100_drones_passes(self):
        result = run_local_benchmark(n_drones=100, duration_s=2.0, target_hz=10)
        # Should process 100 drones × 10 Hz = 1000 frames/s >> 60 FPS threshold
        assert result.frames_per_s > 60.0
