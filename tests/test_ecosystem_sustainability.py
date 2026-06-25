"""GENESIS Phase 397 -- 생태계 자생력 평가 테스트.

검증 항목:
- CheckItem / DimensionResult / SustainabilityReport frozen
- CHECK_DEFINITIONS / VALID_DIMENSIONS 레지스트리 무결성
- assess_sustainability / get_dimension / list_dimensions
- CLI: --assess, --dimension, --dimensions, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.ecosystem_sustainability import (
    CHECK_DEFINITIONS,
    DIMENSION_NAMES_KO,
    SUSTAINABILITY_THRESHOLD,
    VALID_DIMENSIONS,
    CheckItem,
    DimensionResult,
    SustainabilityReport,
    assess_sustainability,
    get_dimension,
    list_dimensions,
)


class TestCheckItem:
    def test_frozen(self) -> None:
        c = CheckItem("doc_readme", "documentation", "README.md 존재", True, "ok")
        with pytest.raises(AttributeError):
            c.passed = False  # type: ignore[misc]

    def test_fields(self) -> None:
        c = CheckItem("test_1", "testing", "desc", False, "누락")
        assert c.check_id == "test_1"
        assert c.dimension == "testing"
        assert c.passed is False

    def test_as_dict(self) -> None:
        d = CheckItem("x", "y", "z", True, "ok").as_dict()
        assert d["check_id"] == "x"
        assert d["passed"] is True
        assert isinstance(d, dict)


class TestDimensionResult:
    def test_frozen(self) -> None:
        d = DimensionResult("testing", "테스트", (), 0, 0, 0.0)
        with pytest.raises(AttributeError):
            d.score = 100.0  # type: ignore[misc]

    def test_as_dict(self) -> None:
        c = CheckItem("a", "testing", "desc", True, "ok")
        d = DimensionResult("testing", "테스트", (c,), 1, 1, 100.0).as_dict()
        assert d["dimension"] == "testing"
        assert d["score"] == 100.0
        assert len(d["checks"]) == 1


class TestSustainabilityReport:
    def test_frozen(self) -> None:
        r = SustainabilityReport((), 0, 0, 0.0, "F", False)
        with pytest.raises(AttributeError):
            r.self_sustaining = True  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = SustainabilityReport((), 10, 7, 70.0, "C", True).as_dict()
        assert d["total_checks"] == 10
        assert d["self_sustaining"] is True
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestRegistries:
    def test_valid_dimensions_is_tuple(self) -> None:
        assert isinstance(VALID_DIMENSIONS, tuple)

    def test_valid_dimensions_count(self) -> None:
        assert len(VALID_DIMENSIONS) == 6

    def test_check_definitions_is_tuple(self) -> None:
        assert isinstance(CHECK_DEFINITIONS, tuple)

    def test_check_definitions_count(self) -> None:
        assert len(CHECK_DEFINITIONS) == 24

    def test_unique_check_ids(self) -> None:
        ids = [cid for cid, _, _ in CHECK_DEFINITIONS]
        assert len(ids) == len(set(ids))

    def test_all_check_dimensions_valid(self) -> None:
        for _, dim, _ in CHECK_DEFINITIONS:
            assert dim in VALID_DIMENSIONS

    def test_dimension_names_ko_complete(self) -> None:
        for dim in VALID_DIMENSIONS:
            assert dim in DIMENSION_NAMES_KO

    def test_sustainability_threshold(self) -> None:
        assert SUSTAINABILITY_THRESHOLD == 70.0


class TestAssessSustainability:
    def test_returns_report(self) -> None:
        report = assess_sustainability()
        assert isinstance(report, SustainabilityReport)

    def test_overall_score_range(self) -> None:
        report = assess_sustainability()
        assert 0 <= report.overall_score <= 100

    def test_has_dimensions(self) -> None:
        report = assess_sustainability()
        assert len(report.dimensions) == len(VALID_DIMENSIONS)

    def test_dimension_names(self) -> None:
        report = assess_sustainability()
        names = {d.dimension for d in report.dimensions}
        assert names == set(VALID_DIMENSIONS)

    def test_overall_grade_valid(self) -> None:
        report = assess_sustainability()
        assert report.overall_grade in ("A", "B", "C", "D", "F")

    def test_self_sustaining_flag(self) -> None:
        report = assess_sustainability()
        expected = report.overall_score >= SUSTAINABILITY_THRESHOLD
        assert report.self_sustaining == expected

    def test_total_checks_consistent(self) -> None:
        report = assess_sustainability()
        assert report.total_checks == len(CHECK_DEFINITIONS)
        dim_total = sum(d.total_count for d in report.dimensions)
        assert report.total_checks == dim_total

    def test_passed_count_consistent(self) -> None:
        report = assess_sustainability()
        dim_passed = sum(d.passed_count for d in report.dimensions)
        assert report.total_passed == dim_passed

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(assess_sustainability().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            assess_sustainability(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = assess_sustainability(tmp_path)
        assert report.total_passed == 0
        assert report.overall_score == 0.0
        assert report.overall_grade == "F"
        assert report.self_sustaining is False


class TestGetDimension:
    def test_valid_dimension(self) -> None:
        d = get_dimension("documentation")
        assert isinstance(d, DimensionResult)
        assert d.dimension == "documentation"

    def test_all_dimensions(self) -> None:
        for dim in VALID_DIMENSIONS:
            d = get_dimension(dim)
            assert d.dimension == dim

    def test_invalid_dimension_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown dimension"):
            get_dimension("invalid_dimension")

    def test_score_range(self) -> None:
        for dim in VALID_DIMENSIONS:
            d = get_dimension(dim)
            assert 0 <= d.score <= 100


class TestListDimensions:
    def test_returns_list(self) -> None:
        dims = list_dimensions()
        assert isinstance(dims, list)

    def test_count(self) -> None:
        assert len(list_dimensions()) == 6

    def test_has_keys(self) -> None:
        for d in list_dimensions():
            assert "dimension" in d
            assert "name_ko" in d

    def test_json_serializable(self) -> None:
        text = json.dumps(list_dimensions(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "ecosystem_sustainability.py")
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

    def test_assess_json(self) -> None:
        r = self._run("--assess", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total_checks" in data

    def test_dimension(self) -> None:
        r = self._run("--dimension", "testing")
        assert r.returncode == 0

    def test_dimension_json(self) -> None:
        r = self._run("--dimension", "documentation", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["dimension"] == "documentation"

    def test_dimension_invalid(self) -> None:
        r = self._run("--dimension", "invalid_dim")
        assert r.returncode != 0

    def test_dimensions(self) -> None:
        r = self._run("--dimensions")
        assert r.returncode == 0

    def test_dimensions_json(self) -> None:
        r = self._run("--dimensions", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 6

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
