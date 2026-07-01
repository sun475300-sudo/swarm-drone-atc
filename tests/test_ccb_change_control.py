"""GENESIS Phase 318 -- CCB 변경 통제 테스트.

검증 항목:
- CcbFinding / CcbReport frozen
- CCB_CHECKS / CCB_AREAS 레지스트리 무결성
- run_ccb_audit / get_area_report / list_areas
- CLI: --audit, --area, --areas, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.ccb_change_control import (
    AREA_NAMES,
    CCB_AREAS,
    CCB_CHECKS,
    CcbFinding,
    CcbReport,
    get_area_report,
    list_areas,
    run_ccb_audit,
)


class TestCcbFinding:
    def test_frozen(self) -> None:
        f = CcbFinding("CC-001", "BASELINE", "test", "MET", ())
        with pytest.raises(AttributeError):
            f.status = "NOT_MET"  # type: ignore[misc]

    def test_fields(self) -> None:
        f = CcbFinding("CC-004", "CHANGE_REQUEST", "템플릿", "MET", ("a.md",))
        assert f.code == "CC-004"
        assert f.area == "CHANGE_REQUEST"
        assert f.evidence == ("a.md",)

    def test_as_dict(self) -> None:
        d = CcbFinding("CC-001", "BASELINE", "기선", "MET", ()).as_dict()
        assert d["status"] == "MET"
        assert isinstance(d["evidence"], list)


class TestCcbReport:
    def test_frozen(self) -> None:
        r = CcbReport((), 0, 0, 0, 0, 0.0, "미충족")
        with pytest.raises(AttributeError):
            r.total = 99  # type: ignore[misc]

    def test_as_dict(self) -> None:
        report = run_ccb_audit()
        d = report.as_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)
        assert "total" in d
        assert "verdict" in d


class TestRegistries:
    def test_checks_is_tuple(self) -> None:
        assert isinstance(CCB_CHECKS, tuple)

    def test_checks_count(self) -> None:
        assert len(CCB_CHECKS) == 15

    def test_areas_count(self) -> None:
        assert len(CCB_AREAS) == 5

    def test_all_check_areas_valid(self) -> None:
        for code, area, _, _ in CCB_CHECKS:
            assert area in CCB_AREAS, f"{code}: invalid {area}"

    def test_unique_codes(self) -> None:
        codes = [code for code, _, _, _ in CCB_CHECKS]
        assert len(codes) == len(set(codes))

    def test_area_names_complete(self) -> None:
        for a in CCB_AREAS:
            assert a in AREA_NAMES

    def test_pattern_groups_nonempty(self) -> None:
        for code, _, _, patterns in CCB_CHECKS:
            assert len(patterns) > 0, f"{code} has empty pattern_groups"


class TestRunCcbAudit:
    def test_returns_report(self) -> None:
        report = run_ccb_audit()
        assert isinstance(report, CcbReport)

    def test_total(self) -> None:
        report = run_ccb_audit()
        assert report.total == 15

    def test_counts_consistent(self) -> None:
        report = run_ccb_audit()
        total = report.met + report.partial + report.not_met
        assert total == report.total

    def test_compliance_rate_range(self) -> None:
        report = run_ccb_audit()
        assert 0 <= report.compliance_rate <= 1.0

    def test_verdict_valid(self) -> None:
        report = run_ccb_audit()
        assert report.verdict in ("변경 통제 충족", "부분 충족", "미충족")

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(run_ccb_audit().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            run_ccb_audit(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = run_ccb_audit(tmp_path)
        assert report.total == 15
        assert report.verdict in ("변경 통제 충족", "부분 충족", "미충족")


class TestGetAreaReport:
    def test_valid_area(self) -> None:
        result = get_area_report("BASELINE")
        assert result["area"] == "BASELINE"
        assert "findings" in result

    def test_all_areas(self) -> None:
        for a in CCB_AREAS:
            result = get_area_report(a)
            assert result["area"] == a

    def test_case_insensitive(self) -> None:
        result = get_area_report("baseline")
        assert result["area"] == "BASELINE"

    def test_invalid_area_raises(self) -> None:
        with pytest.raises(ValueError, match="유효하지 않은"):
            get_area_report("INVALID")

    def test_rate_range(self) -> None:
        result = get_area_report("BASELINE")
        assert 0 <= result["compliance_rate"] <= 1.0


class TestListAreas:
    def test_returns_list(self) -> None:
        areas = list_areas()
        assert isinstance(areas, list)

    def test_count(self) -> None:
        assert len(list_areas()) == 5

    def test_has_keys(self) -> None:
        for a in list_areas():
            assert "code" in a
            assert "name" in a

    def test_json_serializable(self) -> None:
        text = json.dumps(list_areas(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "ccb_change_control.py")
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

    def test_area(self) -> None:
        r = self._run("--area", "BASELINE")
        assert r.returncode == 0

    def test_area_json(self) -> None:
        r = self._run("--area", "BASELINE", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["area"] == "BASELINE"

    def test_area_invalid(self) -> None:
        r = self._run("--area", "INVALID")
        assert r.returncode != 0

    def test_areas(self) -> None:
        r = self._run("--areas")
        assert r.returncode == 0

    def test_areas_json(self) -> None:
        r = self._run("--areas", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 5

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
