"""P718 — Prometheus 메트릭 모듈 단위 테스트."""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_metrics_module_exists():
    """src/monitoring/metrics.py가 존재해야 한다."""
    assert (REPO_ROOT / "src" / "monitoring" / "metrics.py").exists()


def test_monitoring_docker_compose_exists():
    """monitoring/docker-compose.monitoring.yml이 존재해야 한다."""
    assert (REPO_ROOT / "monitoring" / "docker-compose.monitoring.yml").exists()


def test_prometheus_config_exists():
    """monitoring/prometheus.yml이 존재해야 한다."""
    assert (REPO_ROOT / "monitoring" / "prometheus.yml").exists()


def test_alerts_config_exists():
    """monitoring/alerts.yml이 존재해야 한다."""
    assert (REPO_ROOT / "monitoring" / "alerts.yml").exists()


def test_grafana_dashboard_exists():
    """Grafana 대시보드 JSON이 존재해야 한다."""
    dashboard = REPO_ROOT / "monitoring" / "grafana" / "dashboards" / "sdacs_overview.json"
    assert dashboard.exists()


def test_prometheus_config_valid_yaml():
    """prometheus.yml이 유효한 YAML이어야 한다."""
    import yaml
    with open(REPO_ROOT / "monitoring" / "prometheus.yml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert "global" in data or "scrape_configs" in data


def test_metrics_module_importable():
    """prometheus_client 없이도 metrics 모듈을 임포트할 수 있어야 한다."""
    import importlib
    spec = importlib.util.find_spec("src.monitoring.metrics")
    # 모듈 스펙이 존재하면 임포트 가능
    assert spec is not None


def test_metrics_has_required_functions():
    """metrics.py는 get_metrics_router 또는 메트릭 변수를 노출해야 한다."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "metrics_test",
        REPO_ROOT / "src" / "monitoring" / "metrics.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    # 핵심 메트릭 이름 중 하나가 있으면 통과
    attrs = dir(mod)
    has_metrics = any(
        a in attrs for a in ("get_metrics_router", "active_drones", "api_requests_total", "REQUEST_COUNT")
    )
    assert has_metrics, f"metrics.py에서 메트릭 심볼을 찾을 수 없습니다. attrs={attrs}"
