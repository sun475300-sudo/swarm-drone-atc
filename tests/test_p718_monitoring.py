"""P718 — 관측성 스택 설정 파일 검증."""
from __future__ import annotations

from pathlib import Path
import yaml
import json
import pytest

MONITORING = Path(__file__).parent.parent / "monitoring"


def test_prometheus_config_exists():
    assert (MONITORING / "prometheus.yml").exists()


def test_prometheus_config_valid():
    data = yaml.safe_load((MONITORING / "prometheus.yml").read_text())
    assert "scrape_configs" in data
    jobs = [j["job_name"] for j in data["scrape_configs"]]
    assert "sdacs-api" in jobs


def test_alert_rules_exist():
    rules_path = MONITORING / "rules" / "sdacs_alerts.yml"
    assert rules_path.exists()


def test_alert_rules_valid():
    data = yaml.safe_load((MONITORING / "rules" / "sdacs_alerts.yml").read_text())
    assert "groups" in data
    all_alerts = [
        alert["alert"]
        for group in data["groups"]
        for alert in group.get("rules", [])
        if "alert" in alert
    ]
    assert "HighConflictRate" in all_alerts
    assert "APIHighLatency" in all_alerts


def test_docker_compose_monitoring_exists():
    assert (MONITORING / "docker-compose.monitoring.yml").exists()


def test_docker_compose_has_prometheus_grafana_loki():
    data = yaml.safe_load((MONITORING / "docker-compose.monitoring.yml").read_text())
    services = data.get("services", {})
    assert "prometheus" in services
    assert "grafana" in services
    assert "loki" in services


def test_grafana_dashboard_exists():
    dashboard = MONITORING / "grafana" / "dashboards" / "sdacs_overview.json"
    assert dashboard.exists()


def test_grafana_dashboard_valid():
    data = json.loads((MONITORING / "grafana" / "dashboards" / "sdacs_overview.json").read_text())
    assert data["title"]
    assert len(data.get("panels", [])) >= 3
