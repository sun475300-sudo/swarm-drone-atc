"""P719 — 보안 감사 스크립트 단위 테스트."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from scripts.security_audit import (
    SEVERITY_ORDER,
    _has_critical,
    run_bandit,
    run_pip_audit,
)


class TestSeverityOrder:
    def test_critical_highest(self):
        assert SEVERITY_ORDER["CRITICAL"] > SEVERITY_ORDER["HIGH"]
        assert SEVERITY_ORDER["HIGH"] > SEVERITY_ORDER["MEDIUM"]
        assert SEVERITY_ORDER["MEDIUM"] > SEVERITY_ORDER["LOW"]


class TestHasCritical:
    def test_no_critical(self):
        result = {"severity_counts": {"LOW": 3, "MEDIUM": 1}}
        assert not _has_critical(result)

    def test_has_critical(self):
        result = {"severity_counts": {"CRITICAL": 2}}
        assert _has_critical(result)

    def test_empty_result(self):
        assert not _has_critical({})


class TestRunBandit:
    def test_no_targets_returns_unavailable(self):
        result = run_bandit([Path("/nonexistent/path")])
        assert not result["available"]

    def test_bandit_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = run_bandit([Path(".")])
            assert not result["available"]
            assert "bandit" in result["error"].lower()

    def test_parses_bandit_json_output(self):
        bandit_output = json.dumps({
            "results": [
                {
                    "filename": "api/test.py",
                    "line_number": 10,
                    "issue_severity": "HIGH",
                    "issue_confidence": "MEDIUM",
                    "test_id": "B106",
                    "issue_text": "Hardcoded password string",
                },
                {
                    "filename": "src/test.py",
                    "line_number": 5,
                    "issue_severity": "LOW",
                    "issue_confidence": "LOW",
                    "test_id": "B101",
                    "issue_text": "assert statement",
                },
            ],
            "metrics": {},
        })
        mock_result = MagicMock(stdout=bandit_output, returncode=1)
        with patch("subprocess.run", return_value=mock_result):
            result = run_bandit([Path("api")])
        assert result["available"]
        assert result["total_issues"] == 2
        assert result["severity_counts"]["HIGH"] == 1
        assert result["severity_counts"]["LOW"] == 1

    def test_min_severity_filter(self):
        bandit_output = json.dumps({
            "results": [
                {"filename": "f.py", "line_number": 1, "issue_severity": "LOW",
                 "issue_confidence": "HIGH", "test_id": "B1", "issue_text": "low"},
                {"filename": "f.py", "line_number": 2, "issue_severity": "HIGH",
                 "issue_confidence": "HIGH", "test_id": "B2", "issue_text": "high"},
            ],
            "metrics": {},
        })
        mock_result = MagicMock(stdout=bandit_output, returncode=1)
        with patch("subprocess.run", return_value=mock_result):
            result = run_bandit([Path("api")], min_severity="HIGH")
        assert result["total_issues"] == 1
        assert result["severity_counts"]["HIGH"] == 1


class TestRunPipAudit:
    def test_pip_audit_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = run_pip_audit()
            assert not result["available"]

    def test_no_vulnerabilities(self):
        mock_output = json.dumps([
            {"name": "numpy", "version": "2.0.0", "vulns": []},
        ])
        mock_result = MagicMock(stdout=mock_output, returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            result = run_pip_audit()
        assert result["available"]
        assert result["vulnerable_packages"] == 0

    def test_with_vulnerability(self):
        mock_output = json.dumps([
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [{"id": "CVE-2023-1234", "description": "SSRF"}],
            }
        ])
        mock_result = MagicMock(stdout=mock_output, returncode=1)
        with patch("subprocess.run", return_value=mock_result):
            result = run_pip_audit()
        assert result["available"]
        assert result["vulnerable_packages"] == 1
