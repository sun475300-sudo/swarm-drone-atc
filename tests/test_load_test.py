"""Tests for scripts/load_test.py — P717 load test framework."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.load_test import (
    LoadTestResult,
    _status_label,
    aggregate_by_count,
)


def _make_result(
    drone_count: int = 50,
    seed: int = 42,
    wall_seconds: float = 2.0,
    rtf: float = 30.0,
    collisions: int = 5,
    **kwargs: float,
) -> LoadTestResult:
    return LoadTestResult(
        drone_count=drone_count,
        seed=seed,
        duration_s=60.0,
        wall_seconds=wall_seconds,
        real_time_factor=rtf,
        collision_count=collisions,
        near_miss_count=int(kwargs.get("near_misses", 10)),
        conflict_resolution_rate_pct=kwargs.get("resolution", 98.0),
        clearances_per_sec=kwargs.get("clearances", 5.0),
        route_efficiency_mean=kwargs.get("efficiency", 1.03),
        peak_memory_mb=kwargs.get("memory", 150.0),
    )


class TestStatusLabel:
    def test_excellent(self) -> None:
        assert _status_label(1250.0) == "Excellent"

    def test_good(self) -> None:
        assert _status_label(62.0) == "Good"

    def test_acceptable(self) -> None:
        assert _status_label(2.5) == "Acceptable"

    def test_below_realtime(self) -> None:
        assert _status_label(0.5) == "Below real-time"

    def test_boundary_100(self) -> None:
        assert _status_label(100.0) == "Excellent"

    def test_boundary_10(self) -> None:
        assert _status_label(10.0) == "Good"

    def test_boundary_1(self) -> None:
        assert _status_label(1.0) == "Acceptable"


class TestAggregateByCount:
    def test_single_count(self) -> None:
        results = [_make_result(drone_count=20, seed=i) for i in range(3)]
        agg = aggregate_by_count(results)
        assert len(agg) == 1
        assert agg[0]["drone_count"] == 20
        assert agg[0]["n_seeds"] == 3

    def test_multiple_counts(self) -> None:
        results = [
            _make_result(drone_count=20),
            _make_result(drone_count=50),
            _make_result(drone_count=100),
        ]
        agg = aggregate_by_count(results)
        assert len(agg) == 3
        counts = [e["drone_count"] for e in agg]
        assert counts == [20, 50, 100]

    def test_aggregation_values(self) -> None:
        results = [
            _make_result(drone_count=50, rtf=30.0, collisions=5, memory=100.0),
            _make_result(drone_count=50, rtf=40.0, collisions=3, memory=120.0),
        ]
        agg = aggregate_by_count(results)
        entry = agg[0]
        assert abs(entry["rtf_mean"] - 35.0) < 0.1
        assert abs(entry["collisions_mean"] - 4.0) < 0.1
        assert abs(entry["peak_memory_mb_max"] - 120.0) < 0.1


class TestLoadTestResult:
    def test_frozen(self) -> None:
        r = _make_result()
        with pytest.raises(AttributeError):
            r.drone_count = 100  # type: ignore[misc]

    def test_fields(self) -> None:
        r = _make_result(drone_count=200, rtf=16.0)
        assert r.drone_count == 200
        assert r.real_time_factor == 16.0
