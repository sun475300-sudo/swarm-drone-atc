"""GENESIS Phase 393 -- 성숙도 자가 평가 테스트.

검증 항목:
- CheckItem / DimensionScore / MaturityAssessment frozen
- CheckItem __post_init__ 유효성 검증
- CHECK_DEFINITIONS / VALID_DIMENSIONS 레지스트리 무결성
- assess / get_dimension / list_dimensions
- CLI: --assess, --dimension, --dimensions, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.maturity_assessment import (
    CHECK_DEFINITIONS,
    DIMENSION_NAMES_KO,
    VALID_DIMENSIONS,
    CheckItem,
    DimensionScore,
    MaturityAssessment,
    assess,
    get_dimension,
    list_dimensions,
)


class TestCheckItem:
    def test_frozen(self) -> None:
        c = CheckItem("test", "documentation", "desc", 1.0, True)
        with pytest.raises(AttributeError):
            c.passed = False  # type: ignore[misc]

    def test_fields(self) -> None:
        c = CheckItem("test", "documentation", "desc", 1.5, True)
        assert c.check_id == "test"
        assert c.dimension == "documentation"
        assert c.weight == 1.5
        assert c.passed is True

    def test_as_dict(self) -> None:
        d = CheckItem("test", "testing", "desc", 1.0, False).as_dict()
        assert d["check_id"] == "test"
        assert d["passed"] is False

    def test_invalid_dimension_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid dimension"):
            CheckItem("test", "invalid", "desc", 1.0, True)

    def test_zero_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="weight must be > 0"):
            CheckItem("test", "documentation", "desc", 0, True)

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="weight must be > 0"):
            CheckItem("test", "documentation", "desc", -1, True)


class TestDimensionScore:
    def test_frozen(self) -> None:
        d = DimensionScore("documentation", "문서화", (), 0, 0, 0.0, 0.0)
        with pytest.raises(AttributeError):
            d.dimension = "x"  # type: ignore[misc]

    def test_score_pct(self) -> None:
        d = DimensionScore("testing", "테스트", (), 3, 5, 4.0, 8.0)
        assert d.score_pct == 50.0

    def test_score_pct_zero_max(self) -> None:
        d = DimensionScore("testing", "테스트", (), 0, 0, 0.0, 0.0)
        assert d.score_pct == 0.0

    def test_as_dict(self) -> None:
        d = DimensionScore("testing", "테스트", (), 1, 2, 1.0, 2.0).as_dict()
        assert d["dimension"] == "testing"
        assert d["score_pct"] == 50.0


class TestMaturityAssessment:
    def test_frozen(self) -> None:
        m = MaturityAssessment((), 80.0, "B", 10, 8)
        with pytest.raises(AttributeError):
            m.grade = "A"  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = MaturityAssessment((), 75.0, "C", 10, 7).as_dict()
        assert d["overall_score"] == 75.0
        assert d["grade"] == "C"
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestRegistries:
    def test_valid_dimensions_is_tuple(self) -> None:
        assert isinstance(VALID_DIMENSIONS, tuple)

    def test_valid_dimensions_count(self) -> None:
        assert len(VALID_DIMENSIONS) == 7

    def test_check_definitions_is_tuple(self) -> None:
        assert isinstance(CHECK_DEFINITIONS, tuple)

    def test_check_definitions_count(self) -> None:
        assert len(CHECK_DEFINITIONS) == 30

    def test_check_definitions_unique_ids(self) -> None:
        ids = [c[0] for c in CHECK_DEFINITIONS]
        assert len(ids) == len(set(ids))

    def test_check_definitions_valid_dimensions(self) -> None:
        for _, dim, _, _ in CHECK_DEFINITIONS:
            assert dim in VALID_DIMENSIONS

    def test_check_definitions_positive_weights(self) -> None:
        for _, _, _, weight in CHECK_DEFINITIONS:
            assert weight > 0

    def test_dimension_names_ko_complete(self) -> None:
        for dim in VALID_DIMENSIONS:
            assert dim in DIMENSION_NAMES_KO

    def test_all_dimensions_have_checks(self) -> None:
        dims_with_checks = {c[1] for c in CHECK_DEFINITIONS}
        for dim in VALID_DIMENSIONS:
            assert dim in dims_with_checks


class TestAssess:
    def test_returns_assessment(self) -> None:
        result = assess()
        assert isinstance(result, MaturityAssessment)

    def test_has_all_dimensions(self) -> None:
        result = assess()
        dims = {d.dimension for d in result.dimensions}
        assert dims == set(VALID_DIMENSIONS)

    def test_grade_valid(self) -> None:
        result = assess()
        assert result.grade in ("A", "B", "C", "D", "F")

    def test_overall_score_range(self) -> None:
        result = assess()
        assert 0 <= result.overall_score <= 100

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(assess().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        result = assess(tmp_path)
        assert result.overall_score < 50
        assert result.total_passed < result.total_checks

    def test_full_repo(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "README.md").touch()
        (tmp_path / "CHANGELOG.md").touch()
        (tmp_path / "LICENSE").touch()
        (tmp_path / "ROADMAP.md").touch()
        (tmp_path / "CONTRIBUTING.md").touch()
        (tmp_path / "CLAUDE.md").touch()
        (tmp_path / "CODE_OF_CONDUCT.md").touch()
        (tmp_path / "CITATION.cff").touch()
        (tmp_path / ".gitignore").touch()
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "requirements.txt").touch()
        (tmp_path / "Dockerfile").touch()
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "RELEASE_NOTES.md").touch()
        (tmp_path / "tests").mkdir()
        for i in range(55):
            (tmp_path / "tests" / f"test_{i}.py").touch()
        (tmp_path / "simulation").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "config").mkdir()
        (tmp_path / "electron").mkdir()
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "workflows").mkdir()
        (tmp_path / ".github" / "ISSUE_TEMPLATE").mkdir()
        (tmp_path / ".github" / "pull_request_template.md").touch()
        result = assess(tmp_path)
        assert result.overall_score > 80


class TestGetDimension:
    def test_valid(self) -> None:
        d = get_dimension("documentation")
        assert d.dimension == "documentation"

    def test_all_dimensions(self) -> None:
        for dim in VALID_DIMENSIONS:
            d = get_dimension(dim)
            assert d.dimension == dim

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown dimension"):
            get_dimension("nonexistent")


class TestListDimensions:
    def test_returns_list(self) -> None:
        data = list_dimensions()
        assert isinstance(data, list)
        assert len(data) == 7

    def test_has_keys(self) -> None:
        d = list_dimensions()[0]
        assert "dimension" in d
        assert "name_ko" in d

    def test_json_serializable(self) -> None:
        text = json.dumps(list_dimensions(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "maturity_assessment.py")
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
        assert "overall_score" in data

    def test_dimension(self) -> None:
        r = self._run("--dimension", "documentation")
        assert r.returncode == 0

    def test_dimension_json(self) -> None:
        r = self._run("--dimension", "testing", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["dimension"] == "testing"

    def test_dimension_invalid(self) -> None:
        r = self._run("--dimension", "nonexistent")
        assert r.returncode != 0

    def test_dimensions(self) -> None:
        r = self._run("--dimensions")
        assert r.returncode == 0

    def test_dimensions_json(self) -> None:
        r = self._run("--dimensions", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 7

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
