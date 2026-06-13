"""P719 보안 감사 — 스크립트 존재 및 구조 검증."""

import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).parent.parent


def test_security_audit_script_exists():
    """security_audit.sh 파일이 존재해야 한다."""
    script = REPO_ROOT / "scripts" / "security_audit.sh"
    assert script.exists(), f"보안 감사 스크립트가 없습니다: {script}"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows는 Unix 실행권한 비트(0o111)를 사용하지 않음",
)
def test_security_audit_script_executable():
    """security_audit.sh는 실행 권한이 있어야 한다."""
    script = REPO_ROOT / "scripts" / "security_audit.sh"
    assert script.exists()
    assert script.stat().st_mode & 0o111, "security_audit.sh에 실행 권한이 없습니다"


def test_security_workflow_exists():
    """GitHub Actions security.yml 워크플로우가 존재해야 한다."""
    workflow = REPO_ROOT / ".github" / "workflows" / "security.yml"
    assert workflow.exists(), f"보안 워크플로우가 없습니다: {workflow}"


def test_security_workflow_valid_yaml():
    """security.yml은 유효한 YAML이어야 한다."""
    workflow = REPO_ROOT / ".github" / "workflows" / "security.yml"
    assert workflow.exists()
    with open(workflow, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert "jobs" in data


def test_security_workflow_has_required_jobs():
    """security.yml은 bandit, pip-audit, trivy 잡을 포함해야 한다."""
    workflow = REPO_ROOT / ".github" / "workflows" / "security.yml"
    with open(workflow, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    jobs = data.get("jobs", {})
    assert "bandit" in jobs, "bandit 잡이 없습니다"
    assert "pip-audit" in jobs or "pip_audit" in jobs, "pip-audit 잡이 없습니다"
    assert "trivy" in jobs, "trivy 잡이 없습니다"


def test_security_workflow_triggers():
    """security.yml은 push, pull_request, schedule 트리거를 가져야 한다.

    yaml.safe_load는 'on' 키를 True로 파싱하는 YAML 특성이 있으므로 두 경우 모두 허용.
    """
    workflow = REPO_ROOT / ".github" / "workflows" / "security.yml"
    with open(workflow, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # 'on' 키가 True로 파싱될 수 있으므로 raw 텍스트에서 트리거 확인
    with open(workflow, encoding="utf-8") as f:
        raw = f.read()
    assert "push" in raw
    assert "pull_request" in raw
    assert "schedule" in raw
