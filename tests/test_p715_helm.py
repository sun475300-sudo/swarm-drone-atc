"""P715 — Kubernetes Helm 차트 파일 존재 및 구조 검증."""
from __future__ import annotations

from pathlib import Path
import yaml
import pytest

HELM_ROOT = Path(__file__).parent.parent / "deploy" / "helm" / "sdacs"


def test_chart_yaml_exists():
    assert (HELM_ROOT / "Chart.yaml").exists()


def test_chart_yaml_valid():
    data = yaml.safe_load((HELM_ROOT / "Chart.yaml").read_text())
    assert data["name"] == "sdacs"
    assert "version" in data
    assert "appVersion" in data


def test_values_yaml_exists():
    assert (HELM_ROOT / "values.yaml").exists()


def test_values_has_replicacount():
    data = yaml.safe_load((HELM_ROOT / "values.yaml").read_text())
    assert "replicaCount" in data
    assert data["replicaCount"] >= 1


def test_values_has_image():
    data = yaml.safe_load((HELM_ROOT / "values.yaml").read_text())
    assert "image" in data
    assert "repository" in data["image"]


def test_deployment_template_exists():
    assert (HELM_ROOT / "templates" / "deployment.yaml").exists()


def test_service_template_exists():
    assert (HELM_ROOT / "templates" / "service.yaml").exists()


def test_helpers_template_exists():
    assert (HELM_ROOT / "templates" / "_helpers.tpl").exists()


def test_secret_template_exists():
    assert (HELM_ROOT / "templates" / "secret.yaml").exists()


def test_deployment_has_liveness_probe():
    content = (HELM_ROOT / "templates" / "deployment.yaml").read_text()
    assert "livenessProbe" in content


def test_deployment_has_security_context():
    content = (HELM_ROOT / "templates" / "deployment.yaml").read_text()
    assert "securityContext" in content
