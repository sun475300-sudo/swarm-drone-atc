"""GENESIS Phase 394 -- 인수인계 체크리스트 테스트.

검증 항목:
- HandoverItem / CategoryResult / HandoverReport frozen
- HandoverItem __post_init__ 유효성 검증
- ITEM_DEFINITIONS / VALID_CATEGORIES 레지스트리 무결성
- check_handover / get_category / list_categories
- CLI: --check, --category, --categories, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.handover_checklist import (
    CATEGORY_NAMES_KO,
    ITEM_DEFINITIONS,
    VALID_CATEGORIES,
    CategoryResult,
    HandoverItem,
    HandoverReport,
    check_handover,
    get_category,
    list_categories,
)


class TestHandoverItem:
    def test_frozen(self) -> None:
        h = HandoverItem("t1", "environment", "desc", True, True, "ok")
        with pytest.raises(AttributeError):
            h.passed = False  # type: ignore[misc]

    def test_fields(self) -> None:
        h = HandoverItem("t1", "documentation", "desc", False, True, "note")
        assert h.item_id == "t1"
        assert h.category == "documentation"
        assert h.auto_checkable is False
        assert h.passed is True
        assert h.note == "note"

    def test_as_dict(self) -> None:
        d = HandoverItem("t1", "data", "desc", True, False, "n").as_dict()
        assert d["item_id"] == "t1"
        assert d["passed"] is False

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid category"):
            HandoverItem("t1", "invalid", "desc", True, True, "ok")


class TestCategoryResult:
    def test_frozen(self) -> None:
        c = CategoryResult("environment", "환경 설정", (), 0, 0)
        with pytest.raises(AttributeError):
            c.category = "x"  # type: ignore[misc]

    def test_completion_pct(self) -> None:
        c = CategoryResult("documentation", "문서 완비", (), 3, 5)
        assert c.completion_pct == 60.0

    def test_completion_pct_zero_total(self) -> None:
        c = CategoryResult("data", "데이터·자산", (), 0, 0)
        assert c.completion_pct == 0.0

    def test_as_dict(self) -> None:
        d = CategoryResult("knowledge", "지식 전수", (), 2, 4).as_dict()
        assert d["category"] == "knowledge"
        assert d["completion_pct"] == 50.0


class TestHandoverReport:
    def test_frozen(self) -> None:
        r = HandoverReport((), 10, 5, 50.0, "진행 중")
        with pytest.raises(AttributeError):
            r.readiness = "x"  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = HandoverReport((), 10, 8, 80.0, "거의 완료").as_dict()
        assert d["total_items"] == 10
        assert d["overall_pct"] == 80.0
        assert d["readiness"] == "거의 완료"
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestRegistries:
    def test_valid_categories_is_tuple(self) -> None:
        assert isinstance(VALID_CATEGORIES, tuple)

    def test_valid_categories_count(self) -> None:
        assert len(VALID_CATEGORIES) == 5

    def test_item_definitions_is_tuple(self) -> None:
        assert isinstance(ITEM_DEFINITIONS, tuple)

    def test_item_definitions_count(self) -> None:
        assert len(ITEM_DEFINITIONS) == 25

    def test_item_definitions_unique_ids(self) -> None:
        ids = [i[0] for i in ITEM_DEFINITIONS]
        assert len(ids) == len(set(ids))

    def test_item_definitions_valid_categories(self) -> None:
        for _, cat, _, _ in ITEM_DEFINITIONS:
            assert cat in VALID_CATEGORIES

    def test_category_names_ko_complete(self) -> None:
        for cat in VALID_CATEGORIES:
            assert cat in CATEGORY_NAMES_KO

    def test_all_categories_have_items(self) -> None:
        cats_with_items = {i[1] for i in ITEM_DEFINITIONS}
        for cat in VALID_CATEGORIES:
            assert cat in cats_with_items


class TestCheckHandover:
    def test_returns_report(self) -> None:
        report = check_handover()
        assert isinstance(report, HandoverReport)

    def test_has_all_categories(self) -> None:
        report = check_handover()
        cats = {c.category for c in report.categories}
        assert cats == set(VALID_CATEGORIES)

    def test_readiness_valid(self) -> None:
        report = check_handover()
        assert report.readiness in ("준비 완료", "거의 완료", "진행 중", "미준비")

    def test_overall_pct_range(self) -> None:
        report = check_handover()
        assert 0 <= report.overall_pct <= 100

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(check_handover().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = check_handover(tmp_path)
        assert report.overall_pct < 50
        assert report.total_passed < report.total_items

    def test_full_repo(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "README.md").touch()
        (tmp_path / "CLAUDE.md").touch()
        (tmp_path / "ROADMAP.md").touch()
        (tmp_path / "CHANGELOG.md").touch()
        (tmp_path / "LICENSE").touch()
        (tmp_path / ".gitignore").touch()
        (tmp_path / "requirements.txt").touch()
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "images").mkdir()
        (tmp_path / "docs" / "TECH_DEBT_LEDGER.md").touch()
        (tmp_path / "tests").mkdir()
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "default.yaml").touch()
        (tmp_path / "results").mkdir()
        (tmp_path / "simulation").mkdir()
        (tmp_path / "simulation" / "onboarding_automation.py").touch()
        (tmp_path / "simulation" / "curriculum_slide_package.py").touch()
        report = check_handover(tmp_path)
        assert report.overall_pct > 60


class TestGetCategory:
    def test_valid(self) -> None:
        c = get_category("environment")
        assert c.category == "environment"

    def test_all_categories(self) -> None:
        for cat in VALID_CATEGORIES:
            c = get_category(cat)
            assert c.category == cat

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown category"):
            get_category("nonexistent")


class TestListCategories:
    def test_returns_list(self) -> None:
        data = list_categories()
        assert isinstance(data, list)
        assert len(data) == 5

    def test_has_keys(self) -> None:
        d = list_categories()[0]
        assert "category" in d
        assert "name_ko" in d

    def test_json_serializable(self) -> None:
        text = json.dumps(list_categories(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "handover_checklist.py")
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
        r = self._run("--category", "environment")
        assert r.returncode == 0

    def test_category_json(self) -> None:
        r = self._run("--category", "documentation", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["category"] == "documentation"

    def test_category_invalid(self) -> None:
        r = self._run("--category", "nonexistent")
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
