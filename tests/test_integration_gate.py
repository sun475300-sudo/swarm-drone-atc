"""GENESIS Phase 399 -- 최종 통합 게이트 테스트.

검증 항목:
- SubsystemGate / IntegrationGateReport frozen
- SUBSYSTEM_DEFS 레지스트리 무결성
- run_gate / get_summary
- CLI: --gate, --summary, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.integration_gate import (
    GATE_THRESHOLD,
    SUBSYSTEM_DEFS,
    IntegrationGateReport,
    SubsystemGate,
    get_summary,
    run_gate,
)


class TestSubsystemGate:
    def test_frozen(self) -> None:
        s = SubsystemGate("maturity", "mod", 80.0, "B", True)
        with pytest.raises(AttributeError):
            s.passed = False  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = SubsystemGate("x", "y", 90.0, "A", True).as_dict()
        assert d["name"] == "x"
        assert d["passed"] is True


class TestIntegrationGateReport:
    def test_frozen(self) -> None:
        r = IntegrationGateReport((), 0, 0, 0.0, "F", False)
        with pytest.raises(AttributeError):
            r.gate_passed = True  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = IntegrationGateReport((), 6, 6, 80.0, "B", True).as_dict()
        assert d["total_subsystems"] == 6
        assert d["gate_passed"] is True
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestRegistries:
    def test_subsystem_defs_is_tuple(self) -> None:
        assert isinstance(SUBSYSTEM_DEFS, tuple)

    def test_subsystem_count(self) -> None:
        assert len(SUBSYSTEM_DEFS) == 6

    def test_unique_names(self) -> None:
        names = [n for n, _ in SUBSYSTEM_DEFS]
        assert len(names) == len(set(names))

    def test_gate_threshold(self) -> None:
        assert GATE_THRESHOLD == 60.0


class TestRunGate:
    def test_returns_report(self) -> None:
        report = run_gate()
        assert isinstance(report, IntegrationGateReport)

    def test_subsystem_count(self) -> None:
        report = run_gate()
        assert report.total_subsystems == 6

    def test_subsystem_names(self) -> None:
        report = run_gate()
        names = {s.name for s in report.subsystems}
        expected = {n for n, _ in SUBSYSTEM_DEFS}
        assert names == expected

    def test_overall_score_range(self) -> None:
        report = run_gate()
        assert 0 <= report.overall_score <= 100

    def test_overall_grade_valid(self) -> None:
        report = run_gate()
        assert report.overall_grade in ("A", "B", "C", "D", "F")

    def test_all_passed_consistent(self) -> None:
        report = run_gate()
        count = sum(1 for s in report.subsystems if s.passed)
        assert report.all_passed == count

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(run_gate().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            run_gate(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = run_gate(tmp_path)
        assert report.total_subsystems == 6
        assert report.overall_score >= 0


class TestGetSummary:
    def test_returns_dict(self) -> None:
        summary = get_summary()
        assert isinstance(summary, dict)

    def test_has_keys(self) -> None:
        summary = get_summary()
        assert "gate_passed" in summary
        assert "overall_score" in summary
        assert "overall_grade" in summary
        assert "subsystem_grades" in summary

    def test_json_serializable(self) -> None:
        text = json.dumps(get_summary(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "integration_gate.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_gate(self) -> None:
        r = self._run("--gate")
        assert r.returncode == 0

    def test_gate_json(self) -> None:
        r = self._run("--gate", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total_subsystems" in data

    def test_summary(self) -> None:
        r = self._run("--summary")
        assert r.returncode == 0

    def test_summary_json(self) -> None:
        r = self._run("--summary", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "gate_passed" in data

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
