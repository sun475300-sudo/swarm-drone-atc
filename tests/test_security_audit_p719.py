"""P719 — Security audit: pip-audit CVE scan + bandit SAST."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.security_audit import (
    AuditFinding,
    AuditReport,
    audit,
    run_cve_scan,
    run_sast_scan,
)


class TestAuditFinding:
    def test_fields(self):
        f = AuditFinding(tool="bandit", severity="HIGH", description="SQL injection", location="api/auth.py:42")
        assert f.tool == "bandit"
        assert f.severity == "HIGH"
        assert f.location == "api/auth.py:42"

    def test_default_location(self):
        f = AuditFinding(tool="pip-audit", severity="CRITICAL", description="CVE-2024-1234")
        assert f.location == ""


class TestAuditReport:
    def test_passed_when_no_high_or_critical(self):
        r = AuditReport()
        r.cve_findings = [AuditFinding("pip-audit", "MEDIUM", "CVE-medium")]
        r.sast_findings = [AuditFinding("bandit", "LOW", "subprocess usage")]
        assert r.passed is True

    def test_fails_on_critical(self):
        r = AuditReport()
        r.cve_findings = [AuditFinding("pip-audit", "CRITICAL", "CVE-critical")]
        assert r.passed is False
        assert r.critical_count == 1

    def test_fails_on_high(self):
        r = AuditReport()
        r.sast_findings = [AuditFinding("bandit", "HIGH", "hardcoded password")]
        assert r.passed is False
        assert r.high_count == 1

    def test_all_findings_combines_cve_and_sast(self):
        r = AuditReport()
        r.cve_findings = [AuditFinding("pip-audit", "MEDIUM", "CVE-1")]
        r.sast_findings = [AuditFinding("bandit", "LOW", "issue-1")]
        assert len(r.all_findings) == 2

    def test_empty_report_passes(self):
        r = AuditReport()
        assert r.passed is True
        assert r.critical_count == 0
        assert r.high_count == 0


class TestRunCveScan:
    def _pip_audit_output(self, vulns: list[dict]) -> str:
        return json.dumps({"dependencies": vulns})

    def test_clean_scan_returns_no_findings(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = self._pip_audit_output([])

        with patch("scripts.security_audit._run", return_value=mock_proc):
            findings, ok, err = run_cve_scan()

        assert ok is True
        assert findings == []
        assert err is None

    def test_vuln_found_creates_finding(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = self._pip_audit_output([
            {
                "name": "requests",
                "version": "2.28.0",
                "vulns": [
                    {"id": "CVE-2023-1234", "description": "SSRF via redirect", "fix_versions": ["2.31.0"]},
                ],
            }
        ])

        with patch("scripts.security_audit._run", return_value=mock_proc):
            findings, ok, err = run_cve_scan()

        assert ok is True
        assert len(findings) == 1
        assert findings[0].tool == "pip-audit"
        assert "CVE-2023-1234" in findings[0].description

    def test_tool_unavailable_returns_error(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 2
        mock_proc.stderr = "No module named pip_audit"

        with patch("scripts.security_audit._run", return_value=mock_proc):
            findings, ok, err = run_cve_scan()

        assert ok is False
        assert findings == []
        assert err is not None


class TestRunSastScan:
    def _bandit_output(self, results: list[dict]) -> str:
        return json.dumps({"results": results})

    def test_clean_scan_returns_no_findings(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = self._bandit_output([])

        with patch("scripts.security_audit._run", return_value=mock_proc):
            findings, ok, err = run_sast_scan()

        assert ok is True
        assert findings == []
        assert err is None

    def test_issue_found_creates_finding(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = self._bandit_output([
            {
                "test_id": "B602",
                "issue_text": "subprocess call with shell=True",
                "issue_severity": "HIGH",
                "filename": "src/utils.py",
                "line_number": 77,
            }
        ])

        with patch("scripts.security_audit._run", return_value=mock_proc):
            findings, ok, err = run_sast_scan()

        assert ok is True
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"
        assert "B602" in findings[0].description
        assert "src/utils.py:77" in findings[0].location

    def test_tool_unavailable_returns_error(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 3
        mock_proc.stderr = "bandit not found"

        with patch("scripts.security_audit._run", return_value=mock_proc):
            findings, ok, err = run_sast_scan()

        assert ok is False
        assert err is not None


class TestAuditIntegration:
    def test_audit_runs_both_scanners(self):
        clean_proc = MagicMock()
        clean_proc.returncode = 0
        clean_proc.stdout = json.dumps({"dependencies": [], "results": []})

        with patch("scripts.security_audit._run", return_value=clean_proc):
            report = audit(run_cve=True, run_sast=True)

        assert report.cve_scan_ok is True
        assert report.sast_scan_ok is True

    def test_audit_cve_only(self):
        clean_proc = MagicMock()
        clean_proc.returncode = 0
        clean_proc.stdout = json.dumps({"dependencies": []})

        with patch("scripts.security_audit._run", return_value=clean_proc):
            report = audit(run_cve=True, run_sast=False)

        assert report.cve_scan_ok is True
        assert report.sast_scan_ok is False

    def test_audit_sast_only(self):
        clean_proc = MagicMock()
        clean_proc.returncode = 0
        clean_proc.stdout = json.dumps({"results": []})

        with patch("scripts.security_audit._run", return_value=clean_proc):
            report = audit(run_cve=False, run_sast=True)

        assert report.cve_scan_ok is False
        assert report.sast_scan_ok is True
