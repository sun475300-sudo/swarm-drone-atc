"""Tests for P718 Prometheus metrics endpoint in FastAPI server."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


# ---------------------------------------------------------------------------
# Helper: import the metrics helpers without requiring FastAPI at import time
# ---------------------------------------------------------------------------

def _import_metrics_helpers():
    """api.fastapi_server에서 P718 헬퍼를 임포트한다."""
    try:
        import api.fastapi_server as srv
        return srv
    except Exception:
        pytest.skip("fastapi not installed")


# ---------------------------------------------------------------------------
# Unit tests — metric helper functions
# ---------------------------------------------------------------------------

class TestMetricHelpers:
    def test_record_simulation_start_no_crash_without_prometheus(self):
        """prometheus_client 미설치 시 예외 없이 silently no-op."""
        srv = _import_metrics_helpers()
        with patch.object(srv, "_PROM_AVAILABLE", False):
            srv.record_simulation_start("01_corridor_crossing", "orca")

    def test_record_tick_latency_no_crash_without_prometheus(self):
        srv = _import_metrics_helpers()
        with patch.object(srv, "_PROM_AVAILABLE", False):
            srv.record_tick_latency(12.5)

    def test_record_near_miss_no_crash_without_prometheus(self):
        srv = _import_metrics_helpers()
        with patch.object(srv, "_PROM_AVAILABLE", False):
            srv.record_near_miss()

    def test_refresh_prom_gauges_no_crash_without_prometheus(self):
        srv = _import_metrics_helpers()
        with patch.object(srv, "_PROM_AVAILABLE", False):
            srv._refresh_prom_gauges()

    def test_record_simulation_start_with_prometheus(self):
        """prometheus_client 설치 시 카운터가 증가한다."""
        srv = _import_metrics_helpers()
        if not srv._PROM_AVAILABLE:
            pytest.skip("prometheus_client not installed")
        before = srv._prom_simulation_runs.labels(
            scenario="test_scen", method="test_meth"
        )._value.get()
        srv.record_simulation_start("test_scen", "test_meth")
        after = srv._prom_simulation_runs.labels(
            scenario="test_scen", method="test_meth"
        )._value.get()
        assert after == before + 1

    def test_record_tick_latency_with_prometheus(self):
        srv = _import_metrics_helpers()
        if not srv._PROM_AVAILABLE:
            pytest.skip("prometheus_client not installed")
        # Just verify no exception; histogram internal state is hard to assert precisely
        srv.record_tick_latency(5.0)

    def test_record_near_miss_with_prometheus(self):
        srv = _import_metrics_helpers()
        if not srv._PROM_AVAILABLE:
            pytest.skip("prometheus_client not installed")
        before = srv._prom_near_misses._value.get()
        srv.record_near_miss()
        after = srv._prom_near_misses._value.get()
        assert after == before + 1


# ---------------------------------------------------------------------------
# HTTP endpoint test — /metrics
# ---------------------------------------------------------------------------

class TestMetricsEndpoint:
    @pytest.fixture
    def client(self):
        try:
            from fastapi.testclient import TestClient
            import api.fastapi_server as srv
            return TestClient(srv.app)
        except Exception:
            pytest.skip("fastapi or httpx not installed")

    def test_metrics_endpoint_returns_200(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client):
        response = client.get("/metrics")
        ct = response.headers.get("content-type", "")
        assert "text/plain" in ct or "text" in ct

    def test_metrics_not_in_openapi_schema(self, client):
        """``/metrics`` 엔드포인트는 OpenAPI 스키마에서 숨겨진다."""
        openapi = client.get("/openapi.json")
        if openapi.status_code != 200:
            pytest.skip("no openapi endpoint")
        paths = openapi.json().get("paths", {})
        assert "/metrics" not in paths


# ---------------------------------------------------------------------------
# docker-compose.monitoring.yml existence check
# ---------------------------------------------------------------------------

class TestMonitoringConfig:
    def test_compose_monitoring_exists(self):
        path = _ROOT / "docker-compose.monitoring.yml"
        assert path.exists(), "docker-compose.monitoring.yml is missing"

    def test_prometheus_yml_has_sdacs_job(self):
        path = _ROOT / "deployment" / "monitoring" / "prometheus.yml"
        assert path.exists()
        content = path.read_text()
        assert "sdacs_api" in content

    def test_grafana_dashboard_has_panels(self):
        import json
        path = _ROOT / "deployment" / "monitoring" / "grafana-dashboard.json"
        assert path.exists()
        data = json.loads(path.read_text())
        panels = data.get("panels", [])
        assert len(panels) >= 5, "Dashboard should have at least 5 panels"

    def test_grafana_provisioning_datasource_exists(self):
        path = _ROOT / "deployment" / "monitoring" / "grafana-provisioning" / "datasources" / "prometheus.yml"
        assert path.exists()

    def test_grafana_provisioning_dashboard_exists(self):
        path = _ROOT / "deployment" / "monitoring" / "grafana-provisioning" / "dashboards" / "default.yml"
        assert path.exists()
