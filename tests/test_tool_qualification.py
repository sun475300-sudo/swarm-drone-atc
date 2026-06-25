"""GENESIS Phase 315 -- DO-178C 도구 자격 평가 테스트.

검증 항목:
- ToolQualResult / ToolQualReport frozen
- TOOLS / TOOL_CATEGORIES 레지스트리 무결성
- assess_tools / get_category_report / list_categories
- CLI: --assess, --category, --categories, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.tool_qualification import (
    CATEGORY_NAMES,
    TOOL_CATEGORIES,
    TOOLS,
    ToolQualReport,
    ToolQualResult,
    assess_tools,
    get_category_report,
    list_categories,
)


class TestToolQualResult:
    def test_frozen(self) -> None:
        r = ToolQualResult("TQ-001", "VERIFICATION", "pytest", "TQL-5", "QUALIFIED", ())
        with pytest.raises(AttributeError):
            r.status = "NOT_QUALIFIED"  # type: ignore[misc]

    def test_fields(self) -> None:
        r = ToolQualResult(
            "TQ-004", "CODING_STANDARD", "black", "TQL-5", "PARTIAL", ("a.toml",),
        )
        assert r.code == "TQ-004"
        assert r.tql_level == "TQL-5"
        assert r.status == "PARTIAL"
        assert r.evidence == ("a.toml",)

    def test_as_dict(self) -> None:
        d = ToolQualResult(
            "TQ-001", "VERIFICATION", "pytest", "TQL-5", "QUALIFIED", ("f.toml",),
        ).as_dict()
        assert d["status"] == "QUALIFIED"
        assert d["evidence"] == ["f.toml"]
        assert d["tql_level"] == "TQL-5"


class TestToolQualReport:
    def test_frozen(self) -> None:
        r = ToolQualReport((), 0, 0, 0, 0, 0.0, "미충족")
        with pytest.raises(AttributeError):
            r.total = 99  # type: ignore[misc]

    def test_as_dict(self) -> None:
        report = assess_tools()
        d = report.as_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)
        assert "total" in d
        assert "verdict" in d


class TestRegistries:
    def test_tools_is_tuple(self) -> None:
        assert isinstance(TOOLS, tuple)

    def test_tools_count(self) -> None:
        assert len(TOOLS) == 12

    def test_tool_categories_count(self) -> None:
        assert len(TOOL_CATEGORIES) == 4

    def test_all_tool_categories_valid(self) -> None:
        for _, category, _, _, _ in TOOLS:
            assert category in TOOL_CATEGORIES, f"Invalid category: {category}"

    def test_unique_codes(self) -> None:
        codes = [code for code, _, _, _, _ in TOOLS]
        assert len(codes) == len(set(codes))

    def test_all_pattern_groups_nonempty(self) -> None:
        for _, _, _, _, groups in TOOLS:
            assert len(groups) > 0
            for patterns in groups:
                assert len(patterns) > 0

    def test_category_names_complete(self) -> None:
        for cat in TOOL_CATEGORIES:
            assert cat in CATEGORY_NAMES


class TestAssessTools:
    def test_returns_report(self) -> None:
        report = assess_tools()
        assert isinstance(report, ToolQualReport)

    def test_total(self) -> None:
        report = assess_tools()
        assert report.total == 12

    def test_counts_consistent(self) -> None:
        report = assess_tools()
        total = report.qualified + report.partial + report.not_qualified
        assert total == report.total

    def test_qualification_rate_range(self) -> None:
        report = assess_tools()
        assert 0 <= report.qualification_rate <= 1.0

    def test_verdict_valid(self) -> None:
        report = assess_tools()
        assert report.verdict in ("도구 자격 충족", "부분 충족", "미충족")

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(assess_tools().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            assess_tools(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = assess_tools(tmp_path)
        assert report.total == 12
        assert report.not_qualified == 12
        assert report.qualification_rate == 0.0
        assert report.verdict == "미충족"

    def test_results_have_evidence_when_qualified(self) -> None:
        report = assess_tools()
        for r in report.results:
            if r.status in ("QUALIFIED", "PARTIAL"):
                assert len(r.evidence) > 0, f"{r.code} has no evidence"


class TestGetCategoryReport:
    def test_valid_category(self) -> None:
        result = get_category_report("VERIFICATION")
        assert result["category"] == "VERIFICATION"
        assert "results" in result

    def test_all_categories(self) -> None:
        for cat in TOOL_CATEGORIES:
            result = get_category_report(cat)
            assert result["category"] == cat

    def test_case_insensitive(self) -> None:
        result = get_category_report("verification")
        assert result["category"] == "VERIFICATION"

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="유효하지 않은"):
            get_category_report("INVALID")

    def test_rate_range(self) -> None:
        result = get_category_report("VERIFICATION")
        assert 0 <= result["qualification_rate"] <= 1.0


class TestListCategories:
    def test_returns_list(self) -> None:
        cats = list_categories()
        assert isinstance(cats, list)

    def test_count(self) -> None:
        assert len(list_categories()) == 4

    def test_has_keys(self) -> None:
        for c in list_categories():
            assert "code" in c
            assert "name" in c

    def test_json_serializable(self) -> None:
        text = json.dumps(list_categories(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "tool_qualification.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_assess(self) -> None:
        r = self._run("--assess")
        assert r.returncode == 0
        assert "TQL" in r.stdout

    def test_assess_json(self) -> None:
        r = self._run("--assess", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total" in data

    def test_category(self) -> None:
        r = self._run("--category", "VERIFICATION")
        assert r.returncode == 0

    def test_category_json(self) -> None:
        r = self._run("--category", "VERIFICATION", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["category"] == "VERIFICATION"

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
        assert len(data) == 4

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
