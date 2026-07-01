"""GENESIS Phase 316 -- 빌드 환경 사양서 자동 수집 테스트.

검증 항목:
- EnvItem / EnvReport frozen
- ENV_ITEMS / ENV_CATEGORIES 레지스트리 무결성
- collect_env / get_category_report / list_categories
- CLI: --collect, --category, --categories, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.build_env_spec import (
    CATEGORY_NAMES,
    ENV_CATEGORIES,
    ENV_ITEMS,
    EnvItem,
    EnvReport,
    collect_env,
    get_category_report,
    list_categories,
)


class TestEnvItem:
    def test_frozen(self) -> None:
        r = EnvItem("BE-001", "PYTHON", "test", "3.12", "DOCUMENTED")
        with pytest.raises(AttributeError):
            r.status = "UNDOCUMENTED"  # type: ignore[misc]

    def test_fields(self) -> None:
        r = EnvItem("BE-007", "OS_ENV", "운영체제", "Windows 11", "DOCUMENTED")
        assert r.code == "BE-007"
        assert r.category == "OS_ENV"
        assert r.value == "Windows 11"

    def test_as_dict(self) -> None:
        d = EnvItem("BE-001", "PYTHON", "버전", "3.12", "DOCUMENTED").as_dict()
        assert d["status"] == "DOCUMENTED"
        assert d["value"] == "3.12"


class TestEnvReport:
    def test_frozen(self) -> None:
        r = EnvReport((), 0, 0, 0, 0, 0.0, "문서화 미흡")
        with pytest.raises(AttributeError):
            r.total = 99  # type: ignore[misc]

    def test_as_dict(self) -> None:
        report = collect_env()
        d = report.as_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)
        assert "total" in d
        assert "verdict" in d


class TestRegistries:
    def test_env_items_is_tuple(self) -> None:
        assert isinstance(ENV_ITEMS, tuple)

    def test_env_items_count(self) -> None:
        assert len(ENV_ITEMS) == 15

    def test_env_categories_count(self) -> None:
        assert len(ENV_CATEGORIES) == 5

    def test_all_item_categories_valid(self) -> None:
        for _, category, _, _ in ENV_ITEMS:
            assert category in ENV_CATEGORIES, f"Invalid category: {category}"

    def test_unique_codes(self) -> None:
        codes = [code for code, _, _, _ in ENV_ITEMS]
        assert len(codes) == len(set(codes))

    def test_category_names_complete(self) -> None:
        for cat in ENV_CATEGORIES:
            assert cat in CATEGORY_NAMES


class TestCollectEnv:
    def test_returns_report(self) -> None:
        report = collect_env()
        assert isinstance(report, EnvReport)

    def test_total(self) -> None:
        report = collect_env()
        assert report.total == 15

    def test_counts_consistent(self) -> None:
        report = collect_env()
        total = report.documented + report.partial + report.undocumented
        assert total == report.total

    def test_documentation_rate_range(self) -> None:
        report = collect_env()
        assert 0 <= report.documentation_rate <= 1.0

    def test_verdict_valid(self) -> None:
        report = collect_env()
        assert report.verdict in ("환경 문서화 충족", "부분 문서화", "문서화 미흡")

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(collect_env().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            collect_env(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = collect_env(tmp_path)
        assert report.total == 15
        assert report.documented >= 6
        assert report.verdict in ("환경 문서화 충족", "부분 문서화", "문서화 미흡")

    def test_runtime_items_always_documented(self) -> None:
        report = collect_env()
        runtime_items = [i for i in report.items if i.code in (
            "BE-001", "BE-002", "BE-003", "BE-007", "BE-008", "BE-009",
        )]
        for i in runtime_items:
            assert i.status == "DOCUMENTED", f"{i.code} should be DOCUMENTED"
            assert i.value, f"{i.code} should have a value"


class TestGetCategoryReport:
    def test_valid_category(self) -> None:
        result = get_category_report("PYTHON")
        assert result["category"] == "PYTHON"
        assert "items" in result

    def test_all_categories(self) -> None:
        for cat in ENV_CATEGORIES:
            result = get_category_report(cat)
            assert result["category"] == cat

    def test_case_insensitive(self) -> None:
        result = get_category_report("python")
        assert result["category"] == "PYTHON"

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="유효하지 않은"):
            get_category_report("INVALID")

    def test_rate_range(self) -> None:
        result = get_category_report("PYTHON")
        assert 0 <= result["documentation_rate"] <= 1.0


class TestListCategories:
    def test_returns_list(self) -> None:
        cats = list_categories()
        assert isinstance(cats, list)

    def test_count(self) -> None:
        assert len(list_categories()) == 5

    def test_has_keys(self) -> None:
        for c in list_categories():
            assert "code" in c
            assert "name" in c

    def test_json_serializable(self) -> None:
        text = json.dumps(list_categories(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "build_env_spec.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_collect(self) -> None:
        r = self._run("--collect")
        assert r.returncode == 0

    def test_collect_json(self) -> None:
        r = self._run("--collect", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total" in data

    def test_category(self) -> None:
        r = self._run("--category", "PYTHON")
        assert r.returncode == 0

    def test_category_json(self) -> None:
        r = self._run("--category", "PYTHON", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["category"] == "PYTHON"

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
        assert len(data) == 5

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
