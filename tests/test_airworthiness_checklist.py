"""GENESIS Phase 314 -- 감항 인증 준비 체크리스트 테스트.

검증 항목:
- AirworthinessResult / AirworthinessReport frozen
- AIRWORTHINESS_ITEMS / PROCESS_CATEGORIES 레지스트리 무결성
- check_airworthiness / get_process_report / list_processes
- CLI: --check, --category, --categories, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.airworthiness_checklist import (
    AIRWORTHINESS_ITEMS,
    CATEGORY_NAMES,
    PROCESS_CATEGORIES,
    AirworthinessReport,
    AirworthinessResult,
    check_airworthiness,
    get_process_report,
    list_processes,
)


class TestAirworthinessResult:
    def test_frozen(self) -> None:
        r = AirworthinessResult("AW-001", "PLANNING", "test", "DAL-D", "COMPLIANT", ())
        with pytest.raises(AttributeError):
            r.status = "NON_COMPLIANT"  # type: ignore[misc]

    def test_fields(self) -> None:
        r = AirworthinessResult(
            "AW-003", "PLANNING", "형상관리", "DAL-D", "PARTIAL", ("a.py",),
        )
        assert r.code == "AW-003"
        assert r.dal_level == "DAL-D"
        assert r.status == "PARTIAL"
        assert r.evidence == ("a.py",)

    def test_as_dict(self) -> None:
        d = AirworthinessResult(
            "AW-001", "PLANNING", "req", "DAL-D", "COMPLIANT", ("f.py",),
        ).as_dict()
        assert d["status"] == "COMPLIANT"
        assert d["evidence"] == ["f.py"]
        assert d["dal_level"] == "DAL-D"


class TestAirworthinessReport:
    def test_frozen(self) -> None:
        r = AirworthinessReport((), 0, 0, 0, 0, 0.0, "준비 미흡")
        with pytest.raises(AttributeError):
            r.total = 99  # type: ignore[misc]

    def test_as_dict(self) -> None:
        report = check_airworthiness()
        d = report.as_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)
        assert "total" in d
        assert "verdict" in d


class TestRegistries:
    def test_airworthiness_items_is_tuple(self) -> None:
        assert isinstance(AIRWORTHINESS_ITEMS, tuple)

    def test_airworthiness_items_count(self) -> None:
        assert len(AIRWORTHINESS_ITEMS) == 20

    def test_process_categories_count(self) -> None:
        assert len(PROCESS_CATEGORIES) == 6

    def test_all_item_categories_valid(self) -> None:
        for _, category, _, _, _ in AIRWORTHINESS_ITEMS:
            assert category in PROCESS_CATEGORIES, f"Invalid category: {category}"

    def test_unique_codes(self) -> None:
        codes = [code for code, _, _, _, _ in AIRWORTHINESS_ITEMS]
        assert len(codes) == len(set(codes))

    def test_all_pattern_groups_nonempty(self) -> None:
        for _, _, _, _, groups in AIRWORTHINESS_ITEMS:
            assert len(groups) > 0
            for patterns in groups:
                assert len(patterns) > 0

    def test_category_names_complete(self) -> None:
        for cat in PROCESS_CATEGORIES:
            assert cat in CATEGORY_NAMES


class TestCheckAirworthiness:
    def test_returns_report(self) -> None:
        report = check_airworthiness()
        assert isinstance(report, AirworthinessReport)

    def test_total(self) -> None:
        report = check_airworthiness()
        assert report.total == 20

    def test_counts_consistent(self) -> None:
        report = check_airworthiness()
        total = report.compliant + report.partial + report.non_compliant
        assert total == report.total

    def test_compliance_rate_range(self) -> None:
        report = check_airworthiness()
        assert 0 <= report.compliance_rate <= 1.0

    def test_verdict_valid(self) -> None:
        report = check_airworthiness()
        assert report.verdict in ("인증 준비 완료", "부분 준비", "준비 미흡")

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(check_airworthiness().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            check_airworthiness(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = check_airworthiness(tmp_path)
        assert report.total == 20
        assert report.non_compliant == 20
        assert report.compliance_rate == 0.0
        assert report.verdict == "준비 미흡"

    def test_results_have_evidence_when_compliant(self) -> None:
        report = check_airworthiness()
        for r in report.results:
            if r.status in ("COMPLIANT", "PARTIAL"):
                assert len(r.evidence) > 0, f"{r.code} has no evidence"


class TestGetProcessReport:
    def test_valid_process(self) -> None:
        result = get_process_report("PLANNING")
        assert result["category"] == "PLANNING"
        assert "results" in result

    def test_all_processes(self) -> None:
        for cat in PROCESS_CATEGORIES:
            result = get_process_report(cat)
            assert result["category"] == cat

    def test_case_insensitive(self) -> None:
        result = get_process_report("planning")
        assert result["category"] == "PLANNING"

    def test_invalid_process_raises(self) -> None:
        with pytest.raises(ValueError, match="유효하지 않은"):
            get_process_report("INVALID")

    def test_rate_range(self) -> None:
        result = get_process_report("PLANNING")
        assert 0 <= result["compliance_rate"] <= 1.0


class TestListProcesses:
    def test_returns_list(self) -> None:
        procs = list_processes()
        assert isinstance(procs, list)

    def test_count(self) -> None:
        assert len(list_processes()) == 6

    def test_has_keys(self) -> None:
        for p in list_processes():
            assert "code" in p
            assert "name" in p

    def test_json_serializable(self) -> None:
        text = json.dumps(list_processes(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "airworthiness_checklist.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_check(self) -> None:
        r = self._run("--check")
        assert r.returncode == 0
        assert "감항" in r.stdout

    def test_check_json(self) -> None:
        r = self._run("--check", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total" in data

    def test_category(self) -> None:
        r = self._run("--category", "PLANNING")
        assert r.returncode == 0

    def test_category_json(self) -> None:
        r = self._run("--category", "PLANNING", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["category"] == "PLANNING"

    def test_category_invalid(self) -> None:
        r = self._run("--category", "INVALID")
        assert r.returncode != 0

    def test_categories(self) -> None:
        r = self._run("--categories")
        assert r.returncode == 0

    def test_categories_json(self) -> None:
        r = self._run("--categories", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 6

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
