"""GENESIS Phase 317 -- SQA 감사 로그 테스트.

검증 항목:
- SqaFinding / SqaReport frozen
- SQA_CHECKS / SQA_OBJECTIVES 레지스트리 무결성
- run_sqa_audit / get_objective_report / list_objectives
- CLI: --audit, --objective, --objectives, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.sqa_audit import (
    OBJECTIVE_NAMES,
    SQA_CHECKS,
    SQA_OBJECTIVES,
    SqaFinding,
    SqaReport,
    get_objective_report,
    list_objectives,
    run_sqa_audit,
)


class TestSqaFinding:
    def test_frozen(self) -> None:
        f = SqaFinding("SQ-001", "SQA_PLANNING", "test", "MET", ())
        with pytest.raises(AttributeError):
            f.status = "NOT_MET"  # type: ignore[misc]

    def test_fields(self) -> None:
        f = SqaFinding("SQ-005", "PROCESS_COMPLIANCE", "테스트", "MET", ("a.py",))
        assert f.code == "SQ-005"
        assert f.objective == "PROCESS_COMPLIANCE"
        assert f.evidence == ("a.py",)

    def test_as_dict(self) -> None:
        d = SqaFinding("SQ-001", "SQA_PLANNING", "계획", "MET", ()).as_dict()
        assert d["status"] == "MET"
        assert isinstance(d["evidence"], list)


class TestSqaReport:
    def test_frozen(self) -> None:
        r = SqaReport((), 0, 0, 0, 0, 0.0, "미준수")
        with pytest.raises(AttributeError):
            r.total = 99  # type: ignore[misc]

    def test_as_dict(self) -> None:
        report = run_sqa_audit()
        d = report.as_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)
        assert "total" in d
        assert "verdict" in d


class TestRegistries:
    def test_checks_is_tuple(self) -> None:
        assert isinstance(SQA_CHECKS, tuple)

    def test_checks_count(self) -> None:
        assert len(SQA_CHECKS) == 15

    def test_objectives_count(self) -> None:
        assert len(SQA_OBJECTIVES) == 5

    def test_all_check_objectives_valid(self) -> None:
        for code, objective, _, _ in SQA_CHECKS:
            assert objective in SQA_OBJECTIVES, f"{code}: invalid {objective}"

    def test_unique_codes(self) -> None:
        codes = [code for code, _, _, _ in SQA_CHECKS]
        assert len(codes) == len(set(codes))

    def test_objective_names_complete(self) -> None:
        for obj in SQA_OBJECTIVES:
            assert obj in OBJECTIVE_NAMES

    def test_pattern_groups_nonempty(self) -> None:
        for code, _, _, patterns in SQA_CHECKS:
            assert len(patterns) > 0, f"{code} has empty pattern_groups"


class TestRunSqaAudit:
    def test_returns_report(self) -> None:
        report = run_sqa_audit()
        assert isinstance(report, SqaReport)

    def test_total(self) -> None:
        report = run_sqa_audit()
        assert report.total == 15

    def test_counts_consistent(self) -> None:
        report = run_sqa_audit()
        total = report.met + report.partial + report.not_met
        assert total == report.total

    def test_compliance_rate_range(self) -> None:
        report = run_sqa_audit()
        assert 0 <= report.compliance_rate <= 1.0

    def test_verdict_valid(self) -> None:
        report = run_sqa_audit()
        assert report.verdict in ("SQA 준수", "부분 준수", "미준수")

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(run_sqa_audit().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            run_sqa_audit(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = run_sqa_audit(tmp_path)
        assert report.total == 15
        assert report.verdict in ("SQA 준수", "부분 준수", "미준수")


class TestGetObjectiveReport:
    def test_valid_objective(self) -> None:
        result = get_objective_report("SQA_PLANNING")
        assert result["objective"] == "SQA_PLANNING"
        assert "findings" in result

    def test_all_objectives(self) -> None:
        for obj in SQA_OBJECTIVES:
            result = get_objective_report(obj)
            assert result["objective"] == obj

    def test_case_insensitive(self) -> None:
        result = get_objective_report("sqa_planning")
        assert result["objective"] == "SQA_PLANNING"

    def test_invalid_objective_raises(self) -> None:
        with pytest.raises(ValueError, match="유효하지 않은"):
            get_objective_report("INVALID")

    def test_rate_range(self) -> None:
        result = get_objective_report("SQA_PLANNING")
        assert 0 <= result["compliance_rate"] <= 1.0


class TestListObjectives:
    def test_returns_list(self) -> None:
        objs = list_objectives()
        assert isinstance(objs, list)

    def test_count(self) -> None:
        assert len(list_objectives()) == 5

    def test_has_keys(self) -> None:
        for o in list_objectives():
            assert "code" in o
            assert "name" in o

    def test_json_serializable(self) -> None:
        text = json.dumps(list_objectives(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "sqa_audit.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_audit(self) -> None:
        r = self._run("--audit")
        assert r.returncode == 0

    def test_audit_json(self) -> None:
        r = self._run("--audit", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total" in data

    def test_objective(self) -> None:
        r = self._run("--objective", "SQA_PLANNING")
        assert r.returncode == 0

    def test_objective_json(self) -> None:
        r = self._run("--objective", "SQA_PLANNING", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["objective"] == "SQA_PLANNING"

    def test_objective_invalid(self) -> None:
        r = self._run("--objective", "INVALID")
        assert r.returncode != 0

    def test_objectives(self) -> None:
        r = self._run("--objectives")
        assert r.returncode == 0

    def test_objectives_json(self) -> None:
        r = self._run("--objectives", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 5

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
