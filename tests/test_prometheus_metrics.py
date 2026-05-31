"""P718 — Prometheus 메트릭 모듈 테스트."""
from __future__ import annotations

from monitoring.prometheus_metrics import (
    _Counter,
    _Gauge,
    _Histogram,
    generate_metrics_text,
    drones_active,
    conflicts_active,
    scenario_runs_total,
    api_request_duration,
)


class TestGauge:
    def test_set_and_reflect_in_text(self):
        drones_active.set(42.0)
        text = generate_metrics_text()
        assert "sdacs_drones_active 42.0" in text

    def test_set_zero(self):
        conflicts_active.set(0)
        text = generate_metrics_text()
        assert "sdacs_conflicts_active 0.0" in text

    def test_labeled_gauge(self):
        g = _Gauge("test_labeled_gauge", "test", labelnames=["scenario"])
        g.labels(scenario="high_density").set(7.0)
        text = generate_metrics_text()
        assert "test_labeled_gauge" in text


class TestCounter:
    def test_increment(self):
        c = _Counter("test_counter_inc", "test counter")
        initial = c._meta["value"]
        c.inc()
        assert c._meta["value"] == initial + 1.0

    def test_increment_by_amount(self):
        c = _Counter("test_counter_amount", "test counter")
        c.inc(5.0)
        assert c._meta["value"] >= 5.0


class TestHistogram:
    def test_observe(self):
        h = _Histogram("test_histogram_obs", "test histogram")
        h.observe(0.1)
        h.observe(0.5)
        assert h._count == 2
        assert h._sum == pytest.approx(0.6, abs=1e-9)

    def test_bucket_counts(self):
        h = _Histogram("test_histogram_buckets", "test")
        h.observe(0.005)
        assert h._buckets[0.005] >= 1
        assert h._buckets[10.0] >= 1  # 모든 상위 버킷에도 카운트


class TestGenerateMetricsText:
    def test_returns_string(self):
        text = generate_metrics_text()
        assert isinstance(text, str)

    def test_ends_with_newline(self):
        text = generate_metrics_text()
        assert text.endswith("\n")

    def test_contains_help_and_type(self):
        text = generate_metrics_text()
        assert "# HELP" in text
        assert "# TYPE" in text

    def test_known_metrics_present(self):
        text = generate_metrics_text()
        assert "sdacs_drones_active" in text
        assert "sdacs_conflicts_active" in text
        assert "sdacs_ws_subscribers" in text


import pytest
