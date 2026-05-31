"""Tests for P717 — scripts/load_test.py (offline unit checks)."""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.load_test import LatencyBucket, LoadTestResult, _drone_frame


class TestLatencyBucket:
    def test_empty_report(self) -> None:
        b = LatencyBucket("test")
        r = b.report()
        assert r == {"count": 0}

    def test_single_sample(self) -> None:
        b = LatencyBucket("test")
        b.record(0.01)  # 10ms
        r = b.report()
        assert r["count"] == 1
        assert abs(r["p50_ms"] - 10.0) < 0.01
        assert r["mean_ms"] == 10.0

    def test_percentiles(self) -> None:
        b = LatencyBucket("test")
        for i in range(1, 101):
            b.record(i / 1000.0)  # 1ms … 100ms
        r = b.report()
        assert r["count"] == 100
        assert r["p50_ms"] == pytest.approx(50.0, abs=1.0)
        assert r["p95_ms"] == pytest.approx(95.0, abs=1.0)
        assert r["p99_ms"] == pytest.approx(99.0, abs=1.0)

    def test_stores_ms(self) -> None:
        b = LatencyBucket("test")
        b.record(1.0)  # 1000ms
        assert b.samples[0] == 1000.0


class TestLoadTestResult:
    def test_ws_fps_zero_duration(self) -> None:
        r = LoadTestResult()
        assert r.ws_fps == 0.0

    def test_ws_fps(self) -> None:
        r = LoadTestResult()
        r.ws_messages_received = 600
        r.ws_duration_s = 10.0
        assert r.ws_fps == 60.0

    def test_no_errors_initially(self) -> None:
        r = LoadTestResult()
        assert r.errors == []


class TestDroneFrame:
    def test_structure(self) -> None:
        frame = _drone_frame(100)
        assert frame["drones"] == 100
        assert "duration" in frame
        assert "seed" in frame

    def test_drones_param(self) -> None:
        assert _drone_frame(50)["drones"] == 50
        assert _drone_frame(1)["drones"] == 1
