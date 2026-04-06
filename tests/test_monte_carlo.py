"""
Monte Carlo 파라미터 스윕 단위 테스트
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from simulation.monte_carlo import _run_single, _load_mc_config, summarize_results


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
    @pytest.mark.timeout(300)
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

    @pytest.mark.timeout(300)
    def test_wind_override(self):
        combo = {"drone_density": 50, "wind_speed_ms": 10,
                 "failure_rate_pct": 0, "comms_loss_rate": 0}
        result = _run_single((combo, 99))
        assert result["seed"] == 99
        assert "collision_count" in result

    @pytest.mark.timeout(300)
    def test_failure_override(self):
        combo = {"drone_density": 50, "wind_speed_ms": 0,
                 "failure_rate_pct": 5, "comms_loss_rate": 0}
        result = _run_single((combo, 7))
        assert "collision_count" in result

    @pytest.mark.timeout(300)
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
