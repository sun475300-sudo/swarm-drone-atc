"""P717 — 100-drone load test 단위 테스트."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.load_test_100_drones import LoadTestResult, run_load_test


class TestLoadTestResult:
    def test_str_pass(self):
        r = LoadTestResult(
            n_drones=100,
            sim_duration_s=30.0,
            wall_time_s=5.0,
            throughput_ratio=6.0,
            steps_per_second=60.0,
            meets_60fps_target=True,
        )
        assert "PASS" in str(r)
        assert "100" in str(r)

    def test_str_fail(self):
        r = LoadTestResult(
            n_drones=100,
            sim_duration_s=30.0,
            wall_time_s=60.0,
            throughput_ratio=0.5,
            steps_per_second=5.0,
            meets_60fps_target=False,
        )
        assert "FAIL" in str(r)

    def test_meets_target_at_60(self):
        r = LoadTestResult(
            n_drones=50,
            sim_duration_s=10.0,
            wall_time_s=1.0,
            throughput_ratio=10.0,
            steps_per_second=100.0,
            meets_60fps_target=True,
        )
        assert r.meets_60fps_target is True


@pytest.mark.slow
def test_run_load_test_10_drones():
    """10기 드론으로 부하 테스트 실행 (CI 속도 고려)."""
    result = run_load_test(n_drones=10, sim_duration_s=5.0, seed=0)
    assert result.n_drones == 10
    assert result.sim_duration_s == 5.0
    assert result.wall_time_s > 0
    assert result.steps_per_second > 0
    # 10기 드론은 충분히 빠르게 실행되어야 한다
    assert result.meets_60fps_target, (
        f"10 drones should easily meet 60 steps/s, got {result.steps_per_second:.1f}"
    )
