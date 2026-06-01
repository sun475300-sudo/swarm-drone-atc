"""P718 — api/metrics.py Prometheus 계측 테스트."""

from __future__ import annotations

import pytest


def test_metrics_module_importable():
    from api.metrics import (
        CONFLICT_TOTAL,
        DRONE_COUNT,
        REQUEST_COUNT,
        REQUEST_LATENCY,
        RUN_TOTAL,
        WS_CONNECTIONS,
    )
    assert REQUEST_COUNT is not None
    assert WS_CONNECTIONS is not None


def test_ws_connections_gauge():
    from api.metrics import WS_CONNECTIONS

    WS_CONNECTIONS.set(5)
    samples = list(WS_CONNECTIONS.collect())[0].samples
    gauge_sample = next(s for s in samples if not s.name.endswith(("_total", "_created")))
    assert gauge_sample.value == 5.0


def test_request_count_increments():
    from api.metrics import REQUEST_COUNT

    before = _get_counter_value(REQUEST_COUNT, method="GET", path="/test-probe", status="200")
    REQUEST_COUNT.labels(method="GET", path="/test-probe", status="200").inc()
    after = _get_counter_value(REQUEST_COUNT, method="GET", path="/test-probe", status="200")
    assert after == before + 1.0


def test_run_total_counter():
    from api.metrics import RUN_TOTAL

    before = _get_counter_value(RUN_TOTAL, scenario="probe-s01", status="completed")
    RUN_TOTAL.labels(scenario="probe-s01", status="completed").inc()
    after = _get_counter_value(RUN_TOTAL, scenario="probe-s01", status="completed")
    assert after == before + 1.0


def test_drone_count_gauge():
    from api.metrics import DRONE_COUNT

    DRONE_COUNT.set(42)
    samples = list(DRONE_COUNT.collect())[0].samples
    gauge_sample = next(s for s in samples if not s.name.endswith(("_total", "_created")))
    assert gauge_sample.value == 42.0


def test_metrics_endpoint_returns_prometheus_text():
    import asyncio
    from api.metrics import metrics_endpoint

    response = asyncio.run(metrics_endpoint())
    assert "text/plain" in response.media_type
    assert len(response.body) > 0
    body_text = response.body.decode()
    assert "sdacs_" in body_text


def _get_counter_value(counter, **labels) -> float:
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                if all(sample.labels.get(k) == v for k, v in labels.items()):
                    return sample.value
    return 0.0
