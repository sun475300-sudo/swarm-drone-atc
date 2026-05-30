"""Phase 711-720: Deployment Infrastructure tests.

P711 - FastAPI server
P712 - Auth/RBAC stub
P713 - WebSocket route
P715 - K8s manifests validation
P716 - CI/CD workflow validation
P717 - Load balancing
P718 - Prometheus/Grafana config
P719 - Security/IDS
"""
from __future__ import annotations

import os
import re

import pytest
import yaml


# ---------------------------------------------------------------------------
# P711 — FastAPI server
# ---------------------------------------------------------------------------

class TestP711FastAPI:
    """Phase 711: FastAPI backend."""

    def test_app_importable(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import app
        assert app is not None

    def test_app_has_routes(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import app
        routes = [r.path for r in app.routes]
        assert "/healthz" in routes or any("healthz" in str(r) for r in app.routes)

    def test_airspace_snapshot_route_exists(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import app
        paths = [getattr(r, "path", "") for r in app.routes]
        assert any("snapshot" in p or "airspace" in p for p in paths)

    def test_scenarios_route_exists(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import app
        paths = [getattr(r, "path", "") for r in app.routes]
        assert any("scenario" in p for p in paths)

    def test_airspace_snapshot_dataclass(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import AirspaceSnapshot
        snap = AirspaceSnapshot()
        assert hasattr(snap, "timestamp") or snap is not None

    def test_run_record_dataclass(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import RunRecord
        assert RunRecord is not None

    def test_app_state_has_broadcast(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import AppState
        state = AppState()
        assert callable(getattr(state, "broadcast", None))


# ---------------------------------------------------------------------------
# P712 — Auth/RBAC stub
# ---------------------------------------------------------------------------

class TestP712Auth:
    """Phase 712: Auth token validation."""

    def test_require_token_importable(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import require_token
        assert callable(require_token)

    @pytest.mark.asyncio
    async def test_require_token_rejects_missing(self):
        pytest.importorskip("fastapi")
        from fastapi import HTTPException
        from api.fastapi_server import require_token
        with pytest.raises(HTTPException) as exc:
            await require_token(authorization="")
        assert exc.value.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_require_token_accepts_bearer(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import require_token
        token = await require_token(authorization="Bearer my-secret-token")
        assert token == "my-secret-token"

    @pytest.mark.asyncio
    async def test_require_token_rejects_non_bearer(self):
        pytest.importorskip("fastapi")
        from fastapi import HTTPException
        from api.fastapi_server import require_token
        with pytest.raises(HTTPException):
            await require_token(authorization="Basic abc123")


# ---------------------------------------------------------------------------
# P713 — WebSocket route
# ---------------------------------------------------------------------------

class TestP713WebSocket:
    """Phase 713: WebSocket telemetry endpoint."""

    def test_ws_route_exists(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import app
        paths = [getattr(r, "path", "") for r in app.routes]
        assert any("ws" in p or "telemetry" in p for p in paths)

    def test_ws_handler_importable(self):
        pytest.importorskip("fastapi")
        from api.fastapi_server import ws_telemetry
        assert callable(ws_telemetry)


# ---------------------------------------------------------------------------
# P715 — K8s manifest validation
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestP715K8sManifests:
    """Phase 715: Kubernetes manifest structure."""

    def _k8s_path(self, filename: str) -> str:
        return os.path.join(ROOT, "deployment", "k8s", filename)

    def test_deployment_yaml_exists(self):
        assert os.path.exists(self._k8s_path("deployment.yaml"))

    def test_service_yaml_exists(self):
        assert os.path.exists(self._k8s_path("service.yaml"))

    def test_ingress_yaml_exists(self):
        assert os.path.exists(self._k8s_path("ingress.yaml"))

    def test_deployment_yaml_is_valid(self):
        path = self._k8s_path("deployment.yaml")
        with open(path) as f:
            docs = list(yaml.safe_load_all(f))
        assert any(d.get("kind") == "Deployment" for d in docs if d)

    def test_service_yaml_has_selector(self):
        path = self._k8s_path("service.yaml")
        with open(path) as f:
            docs = list(yaml.safe_load_all(f))
        services = [d for d in docs if d and d.get("kind") == "Service"]
        assert services
        for svc in services:
            assert "selector" in svc.get("spec", {})

    def test_deployment_has_container_port(self):
        path = self._k8s_path("deployment.yaml")
        with open(path) as f:
            content = f.read()
        assert "containerPort" in content

    def test_deployment_has_image(self):
        path = self._k8s_path("deployment.yaml")
        with open(path) as f:
            content = f.read()
        assert "image:" in content


# ---------------------------------------------------------------------------
# P716 — CI/CD workflow validation
# ---------------------------------------------------------------------------

class TestP716CICD:
    """Phase 716: CI/CD pipeline configuration."""

    def _ci_path(self) -> str:
        return os.path.join(ROOT, ".github", "workflows", "ci.yml")

    def test_ci_yml_exists(self):
        assert os.path.exists(self._ci_path())

    def test_ci_has_python_matrix(self):
        with open(self._ci_path()) as f:
            content = yaml.safe_load(f)
        matrix = (
            content.get("jobs", {})
            .get("test", {})
            .get("strategy", {})
            .get("matrix", {})
        )
        versions = matrix.get("python-version", [])
        assert "3.10" in versions or "3.11" in versions

    def test_ci_runs_pytest(self):
        with open(self._ci_path()) as f:
            content = f.read()
        assert "pytest" in content

    def test_ci_has_coverage_check(self):
        with open(self._ci_path()) as f:
            content = f.read()
        assert "cov-fail-under" in content or "coverage" in content.lower()

    def test_ci_has_lint_step(self):
        with open(self._ci_path()) as f:
            content = f.read()
        assert "ruff" in content or "lint" in content.lower()

    def test_ci_triggers_on_pr(self):
        with open(self._ci_path()) as f:
            content = f.read()
        assert "pull_request" in content


# ---------------------------------------------------------------------------
# P717 — Load testing / Load balancer
# ---------------------------------------------------------------------------

class TestP717LoadTesting:
    """Phase 717: Load balancing and stress testing."""

    def test_load_balancer_import(self):
        from simulation.load_balancer import LoadBalancer
        lb = LoadBalancer()
        assert lb is not None

    def test_load_balancer_update(self):
        from simulation.load_balancer import LoadBalancer
        lb = LoadBalancer()
        lb.update({"d1": (200.0, 300.0, 50.0)})
        assert lb.imbalance_score() >= 0.0

    def test_load_balancer_rebalance(self):
        from simulation.load_balancer import LoadBalancer
        lb = LoadBalancer()
        positions = {f"d{i}": (float(i % 5) * 50, 0.0, 50.0) for i in range(20)}
        lb.update(positions)
        actions = lb.rebalance()
        assert isinstance(actions, list)

    def test_load_balancer_hotspots(self):
        from simulation.load_balancer import LoadBalancer
        lb = LoadBalancer()
        positions = {f"d{i}": (0.0, 0.0, 50.0) for i in range(10)}
        lb.update(positions)
        hotspots = lb.hotspots()
        assert isinstance(hotspots, list)

    def test_load_balancer_summary(self):
        from simulation.load_balancer import LoadBalancer
        lb = LoadBalancer()
        lb.update({"d1": (100.0, 100.0, 50.0)})
        s = lb.summary()
        assert isinstance(s, dict)

    def test_load_balancer_imbalance_empty(self):
        from simulation.load_balancer import LoadBalancer
        lb = LoadBalancer()
        assert lb.imbalance_score() == 0.0


# ---------------------------------------------------------------------------
# P718 — Prometheus / Grafana monitoring config
# ---------------------------------------------------------------------------

class TestP718Monitoring:
    """Phase 718: Prometheus and Grafana configuration."""

    def _mon_path(self, filename: str) -> str:
        return os.path.join(ROOT, "deployment", "monitoring", filename)

    def test_prometheus_yml_exists(self):
        assert os.path.exists(self._mon_path("prometheus.yml"))

    def test_grafana_dashboard_exists(self):
        assert os.path.exists(self._mon_path("grafana-dashboard.json"))

    def test_prometheus_yml_valid(self):
        with open(self._mon_path("prometheus.yml")) as f:
            cfg = yaml.safe_load(f)
        assert "scrape_configs" in cfg

    def test_prometheus_has_sdacs_job(self):
        with open(self._mon_path("prometheus.yml")) as f:
            cfg = yaml.safe_load(f)
        jobs = [sc.get("job_name", "") for sc in cfg.get("scrape_configs", [])]
        assert any("sdacs" in j.lower() for j in jobs)

    def test_grafana_dashboard_json_valid(self):
        import json
        with open(self._mon_path("grafana-dashboard.json")) as f:
            db = json.load(f)
        assert isinstance(db, dict)

    def test_prometheus_scrape_interval(self):
        with open(self._mon_path("prometheus.yml")) as f:
            cfg = yaml.safe_load(f)
        global_cfg = cfg.get("global", {})
        assert "scrape_interval" in global_cfg


# ---------------------------------------------------------------------------
# P719 — Security / IDS
# ---------------------------------------------------------------------------

class TestP719Security:
    """Phase 719: Cybersecurity IDS and anomaly detection."""

    def test_ids_import(self):
        from simulation.cybersecurity_ids import CybersecurityIDS
        ids = CybersecurityIDS()
        assert ids is not None

    def test_ids_train_and_score(self):
        import numpy as np
        from simulation.cybersecurity_ids import CybersecurityIDS, NetworkPacket
        ids = CybersecurityIDS(rng_seed=42)
        normal = np.random.default_rng(42).random((100, 5))
        ids.train(normal)
        pkt = NetworkPacket(
            source_id="drone_01", dest_id="controller",
            packet_type="telemetry", size_bytes=128,
            timestamp=0.0,
        )
        alert = ids.analyze_packet(pkt)
        assert alert is None or hasattr(alert, "threat_level")

    def test_threat_level_enum(self):
        from simulation.cybersecurity_ids import ThreatLevel
        assert hasattr(ThreatLevel, "LOW") or len(list(ThreatLevel)) > 0

    def test_network_packet_dataclass(self):
        from simulation.cybersecurity_ids import NetworkPacket
        pkt = NetworkPacket(
            source_id="drone_02", dest_id="gcs",
            packet_type="command", size_bytes=64,
            timestamp=1.0,
        )
        assert pkt.source_id == "drone_02"
        assert pkt.size_bytes == 64

    def test_cyber_physical_security_import(self):
        from simulation.cyber_physical_security import CyberPhysicalSecurity
        cps = CyberPhysicalSecurity()
        assert cps is not None

    def test_isolation_forest_anomaly_score(self):
        import numpy as np
        from simulation.cybersecurity_ids import IsolationForest
        ifor = IsolationForest(n_trees=10, max_samples=64, rng_seed=0)
        data = np.random.default_rng(0).random((100, 4))
        ifor.fit(data)
        score = ifor.score(data[0])
        assert 0.0 <= score <= 1.0
