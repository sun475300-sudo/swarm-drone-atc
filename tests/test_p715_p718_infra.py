"""P715/P718 — Kubernetes Helm chart and observability stack tests."""
from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore

ROOT = Path(__file__).parent.parent
HELM_DIR = ROOT / "deploy" / "helm" / "sdacs"
OBS_DIR = ROOT / "deploy" / "observability"


# ---------------------------------------------------------------------------
# P715 Helm chart tests
# ---------------------------------------------------------------------------

def test_helm_chart_yaml_exists():
    assert (HELM_DIR / "Chart.yaml").exists()


def test_helm_chart_yaml_is_valid():
    chart = yaml.safe_load((HELM_DIR / "Chart.yaml").read_text())
    assert chart["apiVersion"] == "v2"
    assert "name" in chart
    assert "version" in chart


def test_helm_values_yaml_exists():
    assert (HELM_DIR / "values.yaml").exists()


def test_helm_values_yaml_is_valid():
    values = yaml.safe_load((HELM_DIR / "values.yaml").read_text())
    assert "replicaCount" in values
    assert "image" in values
    assert "service" in values
    assert "resources" in values


def test_helm_templates_directory_has_required_files():
    templates = HELM_DIR / "templates"
    assert templates.is_dir()
    assert (templates / "deployment.yaml").exists()
    assert (templates / "service.yaml").exists()
    assert (templates / "configmap.yaml").exists()


def test_helm_deployment_template_contains_key_fields():
    tmpl = (HELM_DIR / "templates" / "deployment.yaml").read_text()
    assert "Deployment" in tmpl
    assert "livenessProbe" in tmpl
    assert "readinessProbe" in tmpl
    assert "prometheus.io/scrape" in tmpl


def test_helm_values_resources_are_set():
    values = yaml.safe_load((HELM_DIR / "values.yaml").read_text())
    resources = values["resources"]
    assert "requests" in resources
    assert "limits" in resources
    assert "cpu" in resources["requests"]
    assert "memory" in resources["requests"]


# ---------------------------------------------------------------------------
# P718 Observability stack tests
# ---------------------------------------------------------------------------

def test_observability_docker_compose_exists():
    assert (ROOT / "docker-compose.observability.yml").exists()


def test_observability_compose_has_required_services():
    compose = yaml.safe_load(
        (ROOT / "docker-compose.observability.yml").read_text()
    )
    services = compose.get("services", {})
    assert "prometheus" in services
    assert "grafana" in services
    assert "loki" in services


def test_prometheus_config_exists_and_valid():
    prom_cfg = OBS_DIR / "prometheus.yml"
    assert prom_cfg.exists()
    cfg = yaml.safe_load(prom_cfg.read_text())
    assert "scrape_configs" in cfg
    assert "global" in cfg
    assert cfg["global"]["scrape_interval"] == "15s"


def test_loki_config_exists_and_valid():
    loki_cfg = OBS_DIR / "loki-config.yml"
    assert loki_cfg.exists()
    cfg = yaml.safe_load(loki_cfg.read_text())
    assert "schema_config" in cfg
    assert "storage_config" in cfg


def test_grafana_datasources_provisioning_exists():
    ds = OBS_DIR / "grafana" / "provisioning" / "datasources" / "datasources.yml"
    assert ds.exists()
    cfg = yaml.safe_load(ds.read_text())
    names = [d["name"] for d in cfg.get("datasources", [])]
    assert "Prometheus" in names
    assert "Loki" in names


def test_promtail_config_exists():
    assert (OBS_DIR / "promtail-config.yml").exists()


def test_observability_compose_has_volumes():
    compose = yaml.safe_load(
        (ROOT / "docker-compose.observability.yml").read_text()
    )
    volumes = compose.get("volumes", {})
    assert "prometheus_data" in volumes
    assert "grafana_data" in volumes
    assert "loki_data" in volumes
