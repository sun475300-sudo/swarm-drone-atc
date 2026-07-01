"""GENESIS Phase 398 -- 교육 자산 공개 준비 체크리스트 테스트.

검증 항목:
- PublicationItem / CategoryResult / PublicationReport frozen
- CHECK_DEFINITIONS / VALID_CATEGORIES 레지스트리 무결성
- check_publication / get_category / list_categories
- CLI: --check, --category, --categories, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.asset_publication_checklist import (
    CATEGORY_NAMES_KO,
    CHECK_DEFINITIONS,
    PUBLICATION_THRESHOLD,
    VALID_CATEGORIES,
    CategoryResult,
    PublicationItem,
    PublicationReport,
    check_publication,
    get_category,
    list_categories,
)


class TestPublicationItem:
    def test_frozen(self) -> None:
        p = PublicationItem("lic_file", "licensing", "LICENSE", True, "ok")
        with pytest.raises(AttributeError):
            p.satisfied = False  # type: ignore[misc]

    def test_fields(self) -> None:
        p = PublicationItem("x", "y", "z", False, "누락")
        assert p.item_id == "x"
        assert p.satisfied is False

    def test_as_dict(self) -> None:
        d = PublicationItem("a", "b", "c", True, "ok").as_dict()
        assert d["item_id"] == "a"
        assert d["satisfied"] is True


class TestCategoryResult:
    def test_frozen(self) -> None:
        c = CategoryResult("licensing", "라이선스", (), 0, 0, 0.0)
        with pytest.raises(AttributeError):
            c.score = 100.0  # type: ignore[misc]

    def test_as_dict(self) -> None:
        item = PublicationItem("a", "licensing", "desc", True, "ok")
        d = CategoryResult("licensing", "라이선스", (item,), 1, 1, 100.0).as_dict()
        assert d["category"] == "licensing"
        assert len(d["items"]) == 1


class TestPublicationReport:
    def test_frozen(self) -> None:
        r = PublicationReport((), 0, 0, 0.0, "F", False)
        with pytest.raises(AttributeError):
            r.publication_ready = True  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = PublicationReport((), 10, 8, 80.0, "B", True).as_dict()
        assert d["total_items"] == 10
        assert d["publication_ready"] is True
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestRegistries:
    def test_valid_categories_is_tuple(self) -> None:
        assert isinstance(VALID_CATEGORIES, tuple)

    def test_valid_categories_count(self) -> None:
        assert len(VALID_CATEGORIES) == 5

    def test_check_definitions_is_tuple(self) -> None:
        assert isinstance(CHECK_DEFINITIONS, tuple)

    def test_check_definitions_count(self) -> None:
        assert len(CHECK_DEFINITIONS) == 20

    def test_unique_item_ids(self) -> None:
        ids = [iid for iid, _, _ in CHECK_DEFINITIONS]
        assert len(ids) == len(set(ids))

    def test_all_check_categories_valid(self) -> None:
        for _, cat, _ in CHECK_DEFINITIONS:
            assert cat in VALID_CATEGORIES

    def test_category_names_ko_complete(self) -> None:
        for cat in VALID_CATEGORIES:
            assert cat in CATEGORY_NAMES_KO

    def test_publication_threshold(self) -> None:
        assert PUBLICATION_THRESHOLD == 80.0


class TestCheckPublication:
    def test_returns_report(self) -> None:
        report = check_publication()
        assert isinstance(report, PublicationReport)

    def test_overall_score_range(self) -> None:
        report = check_publication()
        assert 0 <= report.overall_score <= 100

    def test_has_categories(self) -> None:
        report = check_publication()
        assert len(report.categories) == len(VALID_CATEGORIES)

    def test_category_names(self) -> None:
        report = check_publication()
        names = {c.category for c in report.categories}
        assert names == set(VALID_CATEGORIES)

    def test_overall_grade_valid(self) -> None:
        report = check_publication()
        assert report.overall_grade in ("A", "B", "C", "D", "F")

    def test_publication_ready_flag(self) -> None:
        report = check_publication()
        expected = report.overall_score >= PUBLICATION_THRESHOLD
        assert report.publication_ready == expected

    def test_total_items_consistent(self) -> None:
        report = check_publication()
        assert report.total_items == len(CHECK_DEFINITIONS)
        cat_total = sum(c.total for c in report.categories)
        assert report.total_items == cat_total

    def test_passed_count_consistent(self) -> None:
        report = check_publication()
        cat_passed = sum(c.passed for c in report.categories)
        assert report.total_passed == cat_passed

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(check_publication().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            check_publication(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = check_publication(tmp_path)
        assert report.overall_grade == "F"
        assert report.publication_ready is False


class TestGetCategory:
    def test_valid_category(self) -> None:
        c = get_category("licensing")
        assert isinstance(c, CategoryResult)
        assert c.category == "licensing"

    def test_all_categories(self) -> None:
        for cat in VALID_CATEGORIES:
            c = get_category(cat)
            assert c.category == cat

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown category"):
            get_category("invalid_cat")

    def test_score_range(self) -> None:
        for cat in VALID_CATEGORIES:
            c = get_category(cat)
            assert 0 <= c.score <= 100


class TestListCategories:
    def test_returns_list(self) -> None:
        cats = list_categories()
        assert isinstance(cats, list)

    def test_count(self) -> None:
        assert len(list_categories()) == 5

    def test_has_keys(self) -> None:
        for c in list_categories():
            assert "category" in c
            assert "name_ko" in c

    def test_json_serializable(self) -> None:
        text = json.dumps(list_categories(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "asset_publication_checklist.py")
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

    def test_check_json(self) -> None:
        r = self._run("--check", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total_items" in data

    def test_category(self) -> None:
        r = self._run("--category", "licensing")
        assert r.returncode == 0

    def test_category_json(self) -> None:
        r = self._run("--category", "documentation", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["category"] == "documentation"

    def test_category_invalid(self) -> None:
        r = self._run("--category", "invalid_cat")
        assert r.returncode != 0

    def test_categories(self) -> None:
        r = self._run("--categories")
        assert r.returncode == 0

    def test_categories_json(self) -> None:
        r = self._run("--categories", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 5

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
