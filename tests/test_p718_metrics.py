"""P718 — Prometheus 메트릭 모듈 단위 테스트."""
from __future__ import annotations

import pytest


class TestMetricsModule:
    def test_import_ok(self):
        from api.metrics import metrics_endpoint
        assert callable(metrics_endpoint)

    def test_metrics_endpoint_returns_response(self):
        from api.metrics import metrics_endpoint
        resp = metrics_endpoint()
        assert resp is not None
        assert resp.status_code in (200, 501)

    def test_noop_stubs_callable(self):
        from api.metrics import (
            active_drones,
            api_requests_total,
            sim_runs_total,
            ws_connections,
        )
        # should not raise regardless of whether prometheus_client is installed
        sim_runs_total.labels(scenario="test", method="sdacs").inc()
        active_drones.set(10)
        ws_connections.set(3)
        api_requests_total.labels(method="GET", endpoint="/healthz", status="200").inc()
