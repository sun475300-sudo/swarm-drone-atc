"""GENESIS Phase 313 -- UAM 운용기준 정렬 점검 테스트.

검증 항목:
- ComplianceResult / ComplianceReport frozen
- UAM_STANDARDS / CATEGORIES 레지스트리 무결성
- check_standards / get_category_report / list_categories
- CLI: --check, --category, --categories, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.uam_operating_standards import (
    CATEGORIES,
    CATEGORY_NAMES,
    UAM_STANDARDS,
    ComplianceReport,
    ComplianceResult,
    check_standards,
    get_category_report,
    list_categories,
)


class TestComplianceResult:
    def test_frozen(self) -> None:
        r = ComplianceResult("U-001", "AIRSPACE", "test", "ALIGNED", ())
        with pytest.raises(AttributeError):
            r.status = "NOT_ALIGNED"  # type: ignore[misc]

    def test_fields(self) -> None:
        r = ComplianceResult("U-003", "AIRSPACE", "지오펜싱", "PARTIAL", ("a.py",))
        assert r.code == "U-003"
        assert r.status == "PARTIAL"
        assert r.evidence == ("a.py",)

    def test_as_dict(self) -> None:
        d = ComplianceResult("U-001", "AIRSPACE", "req", "ALIGNED", ("f.py",)).as_dict()
        assert d["status"] == "ALIGNED"
        assert d["evidence"] == ["f.py"]


class TestComplianceReport:
    def test_frozen(self) -> None:
        r = ComplianceReport((), 0, 0, 0, 0, 0.0, "미흡")
        with pytest.raises(AttributeError):
            r.total = 99  # type: ignore[misc]

    def test_as_dict(self) -> None:
        report = check_standards()
        d = report.as_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)
        assert "total" in d
        assert "verdict" in d


class TestRegistries:
    def test_uam_standards_is_tuple(self) -> None:
        assert isinstance(UAM_STANDARDS, tuple)

    def test_uam_standards_count(self) -> None:
        assert len(UAM_STANDARDS) == 23

    def test_categories_count(self) -> None:
        assert len(CATEGORIES) == 10

    def test_all_standard_categories_valid(self) -> None:
        for _, category, _, _ in UAM_STANDARDS:
            assert category in CATEGORIES, f"Invalid category: {category}"

    def test_unique_codes(self) -> None:
        codes = [code for code, _, _, _ in UAM_STANDARDS]
        assert len(codes) == len(set(codes))

    def test_all_pattern_groups_nonempty(self) -> None:
        for _, _, _, groups in UAM_STANDARDS:
            assert len(groups) > 0
            for patterns in groups:
                assert len(patterns) > 0

    def test_category_names_complete(self) -> None:
        for cat in CATEGORIES:
            assert cat in CATEGORY_NAMES


class TestCheckStandards:
    def test_returns_report(self) -> None:
        report = check_standards()
        assert isinstance(report, ComplianceReport)

    def test_total(self) -> None:
        report = check_standards()
        assert report.total == 23

    def test_counts_consistent(self) -> None:
        report = check_standards()
        total = report.aligned + report.partial + report.not_aligned
        assert total == report.total

    def test_alignment_rate_range(self) -> None:
        report = check_standards()
        assert 0 <= report.alignment_rate <= 1.0

    def test_verdict_valid(self) -> None:
        report = check_standards()
        assert report.verdict in ("적합", "부분 적합", "미흡")

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(check_standards().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            check_standards(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = check_standards(tmp_path)
        assert report.total == 23
        assert report.not_aligned == 23
        assert report.alignment_rate == 0.0
        assert report.verdict == "미흡"

    def test_results_have_evidence_when_aligned(self) -> None:
        report = check_standards()
        for r in report.results:
            if r.status in ("ALIGNED", "PARTIAL"):
                assert len(r.evidence) > 0, f"{r.code} has no evidence"


class TestGetCategoryReport:
    def test_valid_category(self) -> None:
        result = get_category_report("AIRSPACE")
        assert result["category"] == "AIRSPACE"
        assert "results" in result

    def test_all_categories(self) -> None:
        for cat in CATEGORIES:
            result = get_category_report(cat)
            assert result["category"] == cat

    def test_case_insensitive(self) -> None:
        result = get_category_report("airspace")
        assert result["category"] == "AIRSPACE"

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="유효하지 않은"):
            get_category_report("INVALID")

    def test_rate_range(self) -> None:
        result = get_category_report("AIRSPACE")
        assert 0 <= result["alignment_rate"] <= 1.0


class TestListCategories:
    def test_returns_list(self) -> None:
        cats = list_categories()
        assert isinstance(cats, list)

    def test_count(self) -> None:
        assert len(list_categories()) == 10

    def test_has_keys(self) -> None:
        for c in list_categories():
            assert "code" in c
            assert "name" in c

    def test_json_serializable(self) -> None:
        text = json.dumps(list_categories(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "uam_operating_standards.py")
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
        assert "UAM" in r.stdout

    def test_check_json(self) -> None:
        r = self._run("--check", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total" in data

    def test_category(self) -> None:
        r = self._run("--category", "AIRSPACE")
        assert r.returncode == 0

    def test_category_json(self) -> None:
        r = self._run("--category", "AIRSPACE", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["category"] == "AIRSPACE"

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
        assert len(data) == 10

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
