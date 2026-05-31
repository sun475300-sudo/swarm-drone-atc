"""P717 — 부하 테스트 스크립트 단위 테스트."""
from __future__ import annotations

import time

import pytest

from scripts.load_test import LoadTestConfig, LoadTestReport, RequestResult


class TestLoadTestReport:
    def _make_report(self, results: list[RequestResult]) -> LoadTestReport:
        cfg = LoadTestConfig()
        r = LoadTestReport(config=cfg, start_time=time.time() - 1.0)
        r.results = results
        r.end_time = time.time()
        return r

    def test_error_count_none(self):
        results = [RequestResult("/healthz", 200, 10.0) for _ in range(5)]
        report = self._make_report(results)
        assert report.error_count == 0

    def test_error_count_with_errors(self):
        results = [
            RequestResult("/healthz", 200, 10.0),
            RequestResult("/healthz", 500, 10.0),
            RequestResult("/healthz", 0, 10.0, error="connection refused"),
        ]
        report = self._make_report(results)
        assert report.error_count == 2

    def test_error_rate(self):
        results = [RequestResult("/h", 200, 5.0)] * 9 + [RequestResult("/h", 500, 5.0)]
        report = self._make_report(results)
        assert abs(report.error_rate - 0.1) < 1e-9

    def test_percentile_p50(self):
        results = [RequestResult("/h", 200, float(i)) for i in range(1, 101)]
        report = self._make_report(results)
        p50 = report.percentile(50)
        assert 49.0 <= p50 <= 51.0

    def test_percentile_p99(self):
        results = [RequestResult("/h", 200, float(i)) for i in range(1, 101)]
        report = self._make_report(results)
        p99 = report.percentile(99)
        assert p99 >= 98.0

    def test_empty_latencies(self):
        results = [RequestResult("/h", 0, 5.0, error="err")]
        report = self._make_report(results)
        assert report.percentile(99) == 0.0

    def test_duration_positive(self):
        report = self._make_report([])
        assert report.duration_s > 0


class TestLoadTestConfig:
    def test_defaults(self):
        cfg = LoadTestConfig()
        assert cfg.n_drones == 100
        assert cfg.duration_s == 30.0
        assert cfg.telemetry_hz == 2.0
        assert cfg.concurrent_http == 10
