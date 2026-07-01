"""GENESIS Phase 390 -- 아카이브 전략 테스트.

검증 항목:
- FieldCheck / ZenodoValidation / SwhSaveRequest / ArchiveCheckItem / ArchiveStrategy frozen
- validate_zenodo(): 정상 파일, 필드 누락, 파일 없음, 파싱 오류
- build_swh_request(): 기본값 및 커스텀 URL
- build_checklist(): 자동 감지 (파일 존재/미존재)
- build_strategy(): 전체 보고서 통합
- CLI: --validate, --swh, --checklist, --report, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.archive_strategy import (
    ARCHIVE_ITEMS,
    ZENODO_RECOMMENDED_FIELDS,
    ZENODO_REQUIRED_FIELDS,
    ArchiveCheckItem,
    ArchiveStrategy,
    FieldCheck,
    SwhSaveRequest,
    ZenodoValidation,
    build_checklist,
    build_strategy,
    build_swh_request,
    validate_zenodo,
)


FULL_ZENODO: dict = {
    "title": "SDACS",
    "description": "Swarm Drone ATC",
    "creators": [{"name": "Test"}],
    "upload_type": "software",
    "access_right": "open",
    "license": "MIT",
    "keywords": ["drone"],
    "communities": [{"identifier": "test"}],
    "language": "kor",
    "related_identifiers": [{"identifier": "10.0/test"}],
    "notes": "test notes",
}


class TestFieldCheck:
    def test_frozen(self) -> None:
        fc = FieldCheck("title", True, True, True, "OK")
        with pytest.raises(AttributeError):
            fc.field = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        fc = FieldCheck("title", True, True, True, "OK")
        assert fc.field == "title"
        assert fc.required is True
        assert fc.present is True
        assert fc.valid is True
        assert fc.message == "OK"


class TestZenodoValidation:
    def test_frozen(self) -> None:
        zv = ZenodoValidation(True, (), 0, 0, 0, 0)
        with pytest.raises(AttributeError):
            zv.file_exists = False  # type: ignore[misc]

    def test_is_complete_true(self) -> None:
        zv = ZenodoValidation(True, (), 7, 7, 3, 4)
        assert zv.is_complete is True

    def test_is_complete_false(self) -> None:
        zv = ZenodoValidation(True, (), 5, 7, 3, 4)
        assert zv.is_complete is False

    def test_as_dict(self) -> None:
        fc = FieldCheck("title", True, True, True, "OK")
        zv = ZenodoValidation(True, (fc,), 1, 1, 0, 0)
        d = zv.as_dict()
        assert d["file_exists"] is True
        assert d["is_complete"] is True
        assert len(d["checks"]) == 1
        assert d["checks"][0]["field"] == "title"


class TestSwhSaveRequest:
    def test_frozen(self) -> None:
        swh = build_swh_request()
        with pytest.raises(AttributeError):
            swh.origin_url = "mutated"  # type: ignore[misc]

    def test_default_values(self) -> None:
        swh = build_swh_request()
        assert "swarm-drone-atc" in swh.origin_url
        assert swh.visit_type == "git"
        assert "softwareheritage" in swh.api_endpoint

    def test_custom_url(self) -> None:
        swh = build_swh_request("https://github.com/test/repo")
        assert swh.origin_url == "https://github.com/test/repo"
        assert "test/repo" in swh.curl_command

    def test_as_dict(self) -> None:
        swh = build_swh_request()
        d = swh.as_dict()
        assert "origin_url" in d
        assert "curl_command" in d
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestArchiveCheckItem:
    def test_frozen(self) -> None:
        item = ArchiveCheckItem("test", "desc", "필수", False)
        with pytest.raises(AttributeError):
            item.completed = True  # type: ignore[misc]


class TestArchiveItems:
    def test_is_tuple(self) -> None:
        assert isinstance(ARCHIVE_ITEMS, tuple)

    def test_12_items(self) -> None:
        assert len(ARCHIVE_ITEMS) == 12

    def test_valid_priorities(self) -> None:
        for item_id, desc, priority in ARCHIVE_ITEMS:
            assert priority in ("필수", "권장"), f"{item_id} has invalid priority: {priority}"

    def test_unique_ids(self) -> None:
        ids = [item_id for item_id, _, _ in ARCHIVE_ITEMS]
        assert len(ids) == len(set(ids))

    def test_required_count(self) -> None:
        req = sum(1 for _, _, p in ARCHIVE_ITEMS if p == "필수")
        assert req == 7

    def test_recommended_count(self) -> None:
        rec = sum(1 for _, _, p in ARCHIVE_ITEMS if p == "권장")
        assert rec == 5


class TestValidateZenodo:
    def test_file_not_exists(self, tmp_path: pathlib.Path) -> None:
        result = validate_zenodo(str(tmp_path / "nonexistent.json"))
        assert result.file_exists is False
        assert result.required_pass == 0
        assert result.is_complete is False
        assert len(result.checks) == len(ZENODO_REQUIRED_FIELDS) + len(ZENODO_RECOMMENDED_FIELDS)

    def test_full_zenodo(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / ".zenodo.json"
        path.write_text(json.dumps(FULL_ZENODO), encoding="utf-8")
        result = validate_zenodo(str(path))
        assert result.file_exists is True
        assert result.is_complete is True
        assert result.required_pass == len(ZENODO_REQUIRED_FIELDS)
        assert result.recommended_pass == len(ZENODO_RECOMMENDED_FIELDS)

    def test_missing_required_fields(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / ".zenodo.json"
        partial = {"title": "SDACS", "description": "test"}
        path.write_text(json.dumps(partial), encoding="utf-8")
        result = validate_zenodo(str(path))
        assert result.file_exists is True
        assert result.is_complete is False
        assert result.required_pass == 2

    def test_empty_field_not_valid(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / ".zenodo.json"
        data = {**FULL_ZENODO, "title": ""}
        path.write_text(json.dumps(data), encoding="utf-8")
        result = validate_zenodo(str(path))
        assert result.required_pass < len(ZENODO_REQUIRED_FIELDS)

    def test_invalid_json(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / ".zenodo.json"
        path.write_text("{invalid json", encoding="utf-8")
        result = validate_zenodo(str(path))
        assert result.file_exists is True
        assert result.required_pass == 0

    def test_default_path_uses_repo_root(self) -> None:
        result = validate_zenodo()
        assert result.file_exists is True


class TestBuildChecklist:
    def test_returns_12_items(self, tmp_path: pathlib.Path) -> None:
        items = build_checklist(tmp_path)
        assert len(items) == 12

    def test_all_false_in_empty_dir(self, tmp_path: pathlib.Path) -> None:
        items = build_checklist(tmp_path)
        for item in items:
            assert item.completed is False

    def test_detects_zenodo_json(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / ".zenodo.json").write_text("{}", encoding="utf-8")
        items = build_checklist(tmp_path)
        zenodo_item = next(i for i in items if i.item_id == "zenodo_metadata")
        assert zenodo_item.completed is True

    def test_detects_license(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
        items = build_checklist(tmp_path)
        license_item = next(i for i in items if i.item_id == "license_check")
        assert license_item.completed is True

    def test_detects_docs_dir(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "docs").mkdir()
        items = build_checklist(tmp_path)
        docs_item = next(i for i in items if i.item_id == "docs_freeze")
        assert docs_item.completed is True

    def test_detects_changelog(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "CHANGELOG.md").write_text("# Changelog", encoding="utf-8")
        items = build_checklist(tmp_path)
        cl_item = next(i for i in items if i.item_id == "changelog")
        assert cl_item.completed is True

    def test_detects_doi_badge(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "README.md").write_text("[![DOI](https://zenodo.org/badge/...)]", encoding="utf-8")
        items = build_checklist(tmp_path)
        doi_item = next(i for i in items if i.item_id == "readme_doi")
        assert doi_item.completed is True

    def test_no_doi_badge(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "README.md").write_text("# README", encoding="utf-8")
        items = build_checklist(tmp_path)
        doi_item = next(i for i in items if i.item_id == "readme_doi")
        assert doi_item.completed is False


class TestBuildStrategy:
    def test_readiness_pct_empty(self, tmp_path: pathlib.Path) -> None:
        strategy = build_strategy(
            zenodo_path=str(tmp_path / "nonexistent.json"),
            repo_root=tmp_path,
        )
        assert strategy.readiness_pct == 0.0

    def test_readiness_pct_partial(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / ".zenodo.json").write_text(json.dumps(FULL_ZENODO), encoding="utf-8")
        (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        strategy = build_strategy(
            zenodo_path=str(tmp_path / ".zenodo.json"),
            repo_root=tmp_path,
        )
        assert strategy.readiness_pct > 0.0
        assert strategy.required_done > 0

    def test_as_dict(self, tmp_path: pathlib.Path) -> None:
        strategy = build_strategy(
            zenodo_path=str(tmp_path / "nonexistent.json"),
            repo_root=tmp_path,
        )
        d = strategy.as_dict()
        assert "zenodo" in d
        assert "swh" in d
        assert "checklist" in d
        assert "readiness_pct" in d
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)

    def test_frozen(self, tmp_path: pathlib.Path) -> None:
        strategy = build_strategy(
            zenodo_path=str(tmp_path / "nonexistent.json"),
            repo_root=tmp_path,
        )
        with pytest.raises(AttributeError):
            strategy.required_done = 99  # type: ignore[misc]

    def test_default_strategy(self) -> None:
        strategy = build_strategy()
        assert strategy.readiness_pct > 0.0
        assert strategy.zenodo.file_exists is True


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "archive_strategy.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_validate(self) -> None:
        result = self._run("--validate")
        assert result.returncode == 0
        assert "Zenodo" in result.stdout

    def test_validate_json(self) -> None:
        result = self._run("--validate", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "file_exists" in data

    def test_swh(self) -> None:
        result = self._run("--swh")
        assert result.returncode == 0
        assert "Software Heritage" in result.stdout

    def test_swh_json(self) -> None:
        result = self._run("--swh", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "origin_url" in data

    def test_checklist(self) -> None:
        result = self._run("--checklist")
        assert result.returncode == 0

    def test_checklist_json(self) -> None:
        result = self._run("--checklist", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 12

    def test_report(self) -> None:
        result = self._run("--report")
        assert result.returncode == 0

    def test_report_json(self) -> None:
        result = self._run("--report", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "readiness_pct" in data

    def test_no_args(self) -> None:
        result = self._run()
        assert result.returncode != 0
