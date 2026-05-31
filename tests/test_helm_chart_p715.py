"""P715 — Docker Compose → Kubernetes Helm chart 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CHART_DIR = Path(__file__).resolve().parent.parent / "helm" / "sdacs"


class TestHelmChartStructure:
    def test_chart_directory_exists(self):
        assert CHART_DIR.is_dir()

    def test_chart_yaml_exists(self):
        assert (CHART_DIR / "Chart.yaml").is_file()

    def test_values_yaml_exists(self):
        assert (CHART_DIR / "values.yaml").is_file()

    def test_templates_directory_exists(self):
        assert (CHART_DIR / "templates").is_dir()

    def test_required_templates_exist(self):
        templates = CHART_DIR / "templates"
        assert (templates / "redis.yaml").is_file()
        assert (templates / "backend.yaml").is_file()
        assert (templates / "dashboard.yaml").is_file()


class TestChartYaml:
    @pytest.fixture
    def chart_meta(self):
        with open(CHART_DIR / "Chart.yaml", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_api_version(self, chart_meta):
        assert chart_meta["apiVersion"] == "v2"

    def test_name(self, chart_meta):
        assert chart_meta["name"] == "sdacs"

    def test_version_format(self, chart_meta):
        parts = chart_meta["version"].split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_description_present(self, chart_meta):
        assert len(chart_meta.get("description", "")) > 0


class TestValuesYaml:
    @pytest.fixture
    def values(self):
        with open(CHART_DIR / "values.yaml", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_redis_config(self, values):
        assert "redis" in values
        assert values["redis"]["service"]["port"] == 6379

    def test_backend_config(self, values):
        assert "backend" in values
        assert values["backend"]["enabled"] is True
        assert values["backend"]["service"]["port"] == 8080

    def test_dashboard_config(self, values):
        assert "dashboard" in values
        assert values["dashboard"]["enabled"] is True
        assert values["dashboard"]["service"]["port"] == 3000

    def test_vllm_disabled_by_default(self, values):
        # vLLM is GPU-only, disabled by default
        assert values.get("vllm", {}).get("enabled", False) is False

    def test_redis_command_includes_keyspace(self, values):
        cmd = " ".join(values["redis"]["command"])
        assert "notify-keyspace-events" in cmd

    def test_backend_env_has_redis_url(self, values):
        env = values["backend"]["env"]
        assert "REDIS_URL" in env
        assert "redis" in env["REDIS_URL"].lower()
