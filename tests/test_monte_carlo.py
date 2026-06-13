"""
Monte Carlo 파라미터 스윕 단위 테스트
"""
from __future__ import annotations

import pytest

from simulation.monte_carlo import (
    _load_mc_config,
    _run_single,
    compute_confidence_intervals,
    confidence_interval_report,
    summarize_results,
)

pytestmark = pytest.mark.e2e


class TestLoadConfig:
    def test_returns_dict(self):
        cfg = _load_mc_config()
        assert isinstance(cfg, dict)
        assert "master_seed" in cfg

    def test_has_quick_sweep(self):
        cfg = _load_mc_config()
        assert "quick_sweep" in cfg
        qs = cfg["quick_sweep"]
        assert "drone_density" in qs
        assert "n_per_config" in qs

    def test_has_full_sweep(self):
        cfg = _load_mc_config()
        assert "full_sweep" in cfg
        assert "drone_density" in cfg["full_sweep"]

    def test_acceptance_thresholds(self):
        cfg = _load_mc_config()
        th = cfg.get("acceptance_thresholds", {})
        assert th.get("conflict_resolution_rate_pct", 0) >= 99.0


class TestRunSingle:
    def test_returns_dict_with_required_keys(self):
        combo = {"drone_density": 50, "wind_speed_ms": 0,
                 "failure_rate_pct": 0, "comms_loss_rate": 0}
        result = _run_single((combo, 42))
        assert isinstance(result, dict)
        assert "collision_count" in result
        assert "near_miss_count" in result
        assert "conflict_resolution_rate" in result
        assert "route_efficiency" in result
        assert result["seed"] == 42

    def test_wind_override(self):
        combo = {"drone_density": 50, "wind_speed_ms": 10,
                 "failure_rate_pct": 0, "comms_loss_rate": 0}
        result = _run_single((combo, 99))
        assert result["seed"] == 99
        assert "collision_count" in result

    def test_failure_override(self):
        combo = {"drone_density": 50, "wind_speed_ms": 0,
                 "failure_rate_pct": 5, "comms_loss_rate": 0}
        result = _run_single((combo, 7))
        assert "collision_count" in result

    def test_comms_loss_override(self):
        combo = {"drone_density": 50, "wind_speed_ms": 0,
                 "failure_rate_pct": 0, "comms_loss_rate": 0.05}
        result = _run_single((combo, 11))
        assert "collision_count" in result


class TestSummarizeResults:
    def test_with_sample_data(self):
        rows = [
            {"drone_density": 50, "area_size_km2": 100,
             "failure_rate_pct": 0, "comms_loss_rate": 0, "wind_speed_ms": 0,
             "collision_count": 2, "near_miss_count": 5,
             "conflict_resolution_rate": 95.0, "route_efficiency": 1.05,
             "total_flight_time_s": 300, "total_distance_km": 10.0},
            {"drone_density": 50, "area_size_km2": 100,
             "failure_rate_pct": 0, "comms_loss_rate": 0, "wind_speed_ms": 0,
             "collision_count": 3, "near_miss_count": 7,
             "conflict_resolution_rate": 93.0, "route_efficiency": 1.08,
             "total_flight_time_s": 310, "total_distance_km": 11.0},
        ]
        text = summarize_results(rows)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_empty_group_cols(self):
        rows = [{"collision_count": 1, "x": 2}]
        text = summarize_results(rows)
        assert isinstance(text, str)


class TestConfidenceIntervals:
    """Phase 445 — Monte Carlo 신뢰구간 자동 리포트"""

    def _sample(self) -> list[dict]:
        # 동일 설정 그룹 4회 실행 (collision_count = 2,4,6,8 → mean=5, std≈2.582)
        return [
            {"drone_density": 50, "area_size_km2": 100, "failure_rate_pct": 0,
             "comms_loss_rate": 0, "wind_speed_ms": 0, "collision_count": c,
             "near_miss_count": c + 1, "conflict_resolution_rate": 95.0,
             "route_efficiency": 1.05}
            for c in (2, 4, 6, 8)
        ]

    def test_returns_one_row_per_metric(self):
        rows = compute_confidence_intervals(self._sample())
        # 단일 설정 그룹 × 4개 기본 지표 = 4행
        assert len(rows) == 4
        metrics = {r["metric"] for r in rows}
        assert metrics == {"collision_count", "near_miss_count",
                           "conflict_resolution_rate", "route_efficiency"}

    def test_interval_brackets_mean(self):
        rows = compute_confidence_intervals(self._sample())
        coll = next(r for r in rows if r["metric"] == "collision_count")
        assert coll["n"] == 4
        assert coll["mean"] == pytest.approx(5.0)
        assert coll["ci_low"] < coll["mean"] < coll["ci_high"]
        assert coll["half_width"] > 0

    def test_higher_confidence_widens_interval(self):
        rows95 = compute_confidence_intervals(self._sample(), confidence=0.95)
        rows99 = compute_confidence_intervals(self._sample(), confidence=0.99)
        hw95 = next(r for r in rows95 if r["metric"] == "collision_count")["half_width"]
        hw99 = next(r for r in rows99 if r["metric"] == "collision_count")["half_width"]
        assert hw99 > hw95

    def test_constant_metric_has_zero_width(self):
        rows = compute_confidence_intervals(self._sample())
        cr = next(r for r in rows if r["metric"] == "conflict_resolution_rate")
        assert cr["std"] == 0.0
        assert cr["half_width"] == 0.0
        assert cr["ci_low"] == cr["ci_high"] == pytest.approx(95.0)

    def test_single_sample_zero_width(self):
        rows = compute_confidence_intervals([
            {"drone_density": 10, "collision_count": 3}
        ])
        coll = next(r for r in rows if r["metric"] == "collision_count")
        assert coll["n"] == 1
        assert coll["half_width"] == 0.0

    @pytest.mark.parametrize("bad", [0.0, 1.0, 1.5, -0.1])
    def test_invalid_confidence_raises(self, bad):
        with pytest.raises(ValueError):
            compute_confidence_intervals(self._sample(), confidence=bad)

    def test_nan_values_excluded(self):
        rows = compute_confidence_intervals([
            {"drone_density": 10, "collision_count": 2.0},
            {"drone_density": 10, "collision_count": float("nan")},
            {"drone_density": 10, "collision_count": 4.0},
        ])
        coll = next(r for r in rows if r["metric"] == "collision_count")
        assert coll["n"] == 2
        assert coll["mean"] == pytest.approx(3.0)

    def test_empty_results(self):
        assert compute_confidence_intervals([]) == []

    def test_report_is_string(self):
        text = confidence_interval_report(self._sample())
        assert isinstance(text, str)
        assert "신뢰구간" in text
        assert "collision_count" in text

    def test_report_empty(self):
        assert "데이터 없음" in confidence_interval_report([])
