"""P719 security_audit.py 단위 테스트."""
from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.security_audit import (
    AuditReport,
    Vulnerability,
    generate_markdown,
    main,
    parse_audit_output,
)


def _utcnow() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _sample_pip_audit_data() -> dict:
    return {
        "dependencies": [
            {
                "name": "numpy",
                "version": "2.0.0",
                "vulns": [],
            },
            {
                "name": "cryptography",
                "version": "41.0.7",
                "vulns": [
                    {
                        "id": "CVE-2024-0727",
                        "aliases": ["CVE-2024-0727"],
                        "fix_versions": ["42.0.2"],
                        "description": "NULL pointer dereference in PKCS12, denial of service.",
                    }
                ],
            },
            {
                "name": "setuptools",
                "version": "68.1.2",
                "vulns": [
                    {
                        "id": "CVE-2024-6345",
                        "aliases": [],
                        "fix_versions": ["70.0.0"],
                        "description": "Remote code execution via package_index download functions.",
                    }
                ],
            },
        ]
    }


# --- Vulnerability dataclass ---

def test_vulnerability_immutable():
    v = Vulnerability(
        package="pkg", version="1.0", vuln_id="ID-1",
        aliases=["CVE-2024-0001"], fix_versions=["1.1"],
        description="test",
    )
    with pytest.raises(Exception):
        v.package = "other"  # type: ignore[misc]


def test_vulnerability_severity_high():
    v = Vulnerability(
        package="p", version="1.0", vuln_id="X",
        aliases=[], fix_versions=[],
        description="This allows remote code execution via malicious input.",
    )
    assert v.severity == "HIGH"


def test_vulnerability_severity_medium():
    v = Vulnerability(
        package="p", version="1.0", vuln_id="X",
        aliases=[], fix_versions=[],
        description="Denial of service when processing large files.",
    )
    assert v.severity == "MEDIUM"


def test_vulnerability_severity_low():
    v = Vulnerability(
        package="p", version="1.0", vuln_id="X",
        aliases=[], fix_versions=[],
        description="Minor validation issue.",
    )
    assert v.severity == "LOW"


def test_vulnerability_cve_ids():
    v = Vulnerability(
        package="p", version="1.0", vuln_id="PYSEC-123",
        aliases=["CVE-2024-0001", "GHSA-xxxx", "CVE-2024-0002"],
        fix_versions=[], description="x",
    )
    assert v.cve_ids == ["CVE-2024-0001", "CVE-2024-0002"]


# --- AuditReport counters ---

def test_audit_report_counts():
    vulns = [
        Vulnerability("pkg", "1.0", "A", [], [], "remote code execution", is_direct_dep=True),
        Vulnerability("pkg", "1.0", "B", [], [], "remote code execution", is_direct_dep=False),
        Vulnerability("pkg", "1.0", "C", [], [], "denial of service", is_direct_dep=False),
        Vulnerability("pkg", "1.0", "D", [], [], "info", is_direct_dep=False),
    ]
    report = AuditReport(scan_time=_utcnow(), vulns=vulns)
    assert report.high_count == 2
    assert report.critical_count == 1  # only direct HIGH
    assert report.medium_count == 1
    assert report.low_count == 1


# --- parse_audit_output ---

def test_parse_audit_output_counts():
    data = _sample_pip_audit_data()
    report = parse_audit_output(data)
    assert report.total_packages == 3
    assert len(report.vulns) == 2  # numpy has no vulns


def test_parse_audit_output_severity():
    data = _sample_pip_audit_data()
    report = parse_audit_output(data)
    ids = {v.vuln_id: v.severity for v in report.vulns}
    assert ids["CVE-2024-6345"] == "HIGH"   # remote code execution
    assert ids["CVE-2024-0727"] == "MEDIUM"  # denial of service


def test_parse_audit_output_empty():
    report = parse_audit_output({"dependencies": []})
    assert report.total_packages == 0
    assert len(report.vulns) == 0


# --- generate_markdown ---

def test_generate_markdown_creates_file(tmp_path: Path):
    report = AuditReport(scan_time=_utcnow(), total_packages=3, vulns=[])
    out = tmp_path / "report.md"
    generate_markdown(report, out)
    assert out.exists()
    content = out.read_text()
    assert "SDACS" in content
    assert "취약점 없음" in content


def test_generate_markdown_table_row(tmp_path: Path):
    vulns = [
        Vulnerability(
            "cryptography", "41.0.7", "CVE-2024-0727",
            ["CVE-2024-0727"], ["42.0.2"],
            "denial of service.",
        )
    ]
    report = AuditReport(scan_time=_utcnow(), total_packages=10, vulns=vulns)
    out = tmp_path / "report.md"
    generate_markdown(report, out)
    content = out.read_text()
    assert "cryptography" in content
    assert "42.0.2" in content


# --- main() CLI ---

def test_main_exit_zero_no_fail_flag(tmp_path: Path):
    fake_data = {"dependencies": [{"name": "safe", "version": "1.0", "vulns": []}]}
    with patch("scripts.security_audit.run_pip_audit", return_value=fake_data):
        code = main(["--out-dir", str(tmp_path), "--format", "md"])
    assert code == 0


def test_main_exit_one_with_fail_flag_and_direct_high(tmp_path: Path):
    fake_data = {
        "dependencies": [{
            "name": "numpy",  # not in requirements.txt as direct dep by default
            "version": "2.0.0",
            "vulns": [{
                "id": "CVE-9999",
                "aliases": [],
                "fix_versions": [],
                "description": "Remote code execution.",
            }]
        }]
    }
    with patch("scripts.security_audit.run_pip_audit", return_value=fake_data), \
         patch("scripts.security_audit._load_project_deps", return_value={"numpy"}):
        code = main(["--out-dir", str(tmp_path), "--format", "md", "--fail-on-critical"])
    assert code == 1
