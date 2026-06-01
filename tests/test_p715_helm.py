"""P715 — Kubernetes Helm 차트 구조 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

HELM_ROOT = Path(__file__).parent.parent / "deployment" / "helm" / "sdacs"


class TestHelmChart:
    def test_chart_yaml_exists(self):
        assert (HELM_ROOT / "Chart.yaml").exists()

    def test_chart_yaml_valid(self):
        data = yaml.safe_load((HELM_ROOT / "Chart.yaml").read_text())
        assert data["apiVersion"] == "v2"
        assert "name" in data
        assert "version" in data

    def test_values_yaml_exists(self):
        assert (HELM_ROOT / "values.yaml").exists()

    def test_values_yaml_valid(self):
        data = yaml.safe_load((HELM_ROOT / "values.yaml").read_text())
        assert "image" in data
        assert "service" in data
        assert "ingress" in data

    def test_templates_dir_exists(self):
        assert (HELM_ROOT / "templates").is_dir()

    def test_required_templates_exist(self):
        templates = {f.name for f in (HELM_ROOT / "templates").iterdir()}
        for required in ("deployment.yaml", "service.yaml", "ingress.yaml"):
            assert required in templates, f"template {required} missing"

    def test_timescaledb_template_exists(self):
        assert (HELM_ROOT / "templates" / "timescaledb.yaml").exists()
