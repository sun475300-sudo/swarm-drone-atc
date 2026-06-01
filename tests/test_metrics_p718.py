"""P718 — Prometheus 메트릭 모듈 테스트."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.metrics import _counters, _gauges, _latencies, generate_text, inc, observe_latency, set_gauge


def _fresh_state() -> MagicMock:
    """AppState 스텁을 반환한다."""
    state = MagicMock()
    state.live_tracks = {}
    state.telemetry_subscribers = set()
    return state


def setup_function():
    """테스트 간 독립성: 전역 dict를 초기화한다."""
    _counters.clear()
    _gauges.clear()
    _latencies.clear()


# ---------------------------------------------------------------------------
# inc / set_gauge
# ---------------------------------------------------------------------------


def test_inc_basic():
    inc("sdacs_conflicts_total")
    assert _counters["sdacs_conflicts_total"] == 1.0


def test_inc_with_labels():
    inc("sdacs_api_requests_total", {"method": "GET", "status": "200"})
    key = 'sdacs_api_requests_total{method="GET",status="200"}'
    assert _counters[key] == 1.0


def test_inc_accumulates():
    inc("sdacs_runs_total", value=3.0)
    inc("sdacs_runs_total", value=2.0)
    assert _counters["sdacs_runs_total"] == 5.0


def test_set_gauge():
    set_gauge("sdacs_active_drones", 42.0)
    assert _gauges["sdacs_active_drones"] == 42.0


def test_set_gauge_overwrites():
    set_gauge("sdacs_active_drones", 10.0)
    set_gauge("sdacs_active_drones", 20.0)
    assert _gauges["sdacs_active_drones"] == 20.0


# ---------------------------------------------------------------------------
# observe_latency
# ---------------------------------------------------------------------------


def test_observe_latency_stores():
    observe_latency("/healthz", "GET", 5.0)
    assert ("/healthz", "GET") in _latencies
    assert _latencies[("/healthz", "GET")] == [5.0]


def test_observe_latency_multiple():
    observe_latency("/api/airspace/snapshot", "GET", 10.0)
    observe_latency("/api/airspace/snapshot", "GET", 20.0)
    assert len(_latencies[("/api/airspace/snapshot", "GET")]) == 2


def test_observe_latency_cap():
    # 10,001개 삽입 → 10,000개로 잘림
    for i in range(10_001):
        observe_latency("/test", "GET", float(i))
    assert len(_latencies[("/test", "GET")]) == 10_000


# ---------------------------------------------------------------------------
# generate_text
# ---------------------------------------------------------------------------


def test_generate_text_contains_metrics():
    state = _fresh_state()
    state.live_tracks = {"d1": {}, "d2": {}}
    state.telemetry_subscribers = {object()}

    text = generate_text(state)

    assert "sdacs_active_drones" in text
    assert "sdacs_ws_subscribers" in text
    assert "sdacs_uptime_seconds" in text


def test_generate_text_prometheus_format():
    state = _fresh_state()
    text = generate_text(state)

    lines = text.strip().split("\n")
    help_lines = [l for l in lines if l.startswith("# HELP")]
    type_lines = [l for l in lines if l.startswith("# TYPE")]

    assert len(help_lines) > 0
    assert len(type_lines) > 0
    # HELP 와 TYPE은 짝을 이룬다
    assert len(help_lines) == len(type_lines)


def test_generate_text_latency_histogram():
    observe_latency("/healthz", "GET", 5.0)
    observe_latency("/healthz", "GET", 15.0)
    state = _fresh_state()
    text = generate_text(state)

    assert "sdacs_api_latency_ms_sum" in text
    assert "sdacs_api_latency_ms_count" in text
    # 합계 = 20.0
    assert "20" in text


def test_generate_text_ends_with_newline():
    state = _fresh_state()
    text = generate_text(state)
    assert text.endswith("\n")
