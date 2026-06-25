"""GENESIS Phase 395 -- 교육 자산 레지스트리 테스트.

검증 항목:
- AssetEntry / VerificationResult / RegistryReport frozen
- AssetEntry __post_init__ 유효성 검증
- ASSET_REGISTRY / VALID_TYPES 레지스트리 무결성
- list_assets / get_asset / list_by_type / verify_assets
- CLI: --list, --asset, --by-type, --verify, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from types import MappingProxyType

import pytest

from simulation.education_asset_registry import (
    ASSET_REGISTRY,
    TYPE_NAMES_KO,
    VALID_TYPES,
    AssetEntry,
    RegistryReport,
    VerificationResult,
    _ASSET_INDEX,
    get_asset,
    list_assets,
    list_by_type,
    verify_assets,
)


class TestAssetEntry:
    def test_frozen(self) -> None:
        a = AssetEntry("t1", 382, "module", "path.py", "desc", 10)
        with pytest.raises(AttributeError):
            a.phase = 383  # type: ignore[misc]

    def test_fields(self) -> None:
        a = AssetEntry("t1", 390, "document", "docs/x.md", "desc", 0)
        assert a.asset_id == "t1"
        assert a.phase == 390
        assert a.asset_type == "document"
        assert a.test_count == 0

    def test_as_dict(self) -> None:
        d = AssetEntry("t1", 301, "data", "config/x.yaml", "desc", 5).as_dict()
        assert d["asset_id"] == "t1"
        assert d["phase"] == 301

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid asset_type"):
            AssetEntry("t1", 382, "invalid", "x.py", "desc", 0)

    def test_phase_too_low_raises(self) -> None:
        with pytest.raises(ValueError, match="Phase must be 301-400"):
            AssetEntry("t1", 300, "module", "x.py", "desc", 0)

    def test_phase_too_high_raises(self) -> None:
        with pytest.raises(ValueError, match="Phase must be 301-400"):
            AssetEntry("t1", 401, "module", "x.py", "desc", 0)


class TestVerificationResult:
    def test_frozen(self) -> None:
        v = VerificationResult("t1", "x.py", True)
        with pytest.raises(AttributeError):
            v.exists = False  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = VerificationResult("t1", "x.py", False).as_dict()
        assert d["exists"] is False


class TestRegistryReport:
    def test_frozen(self) -> None:
        r = RegistryReport(10, 8, 2, 80.0, MappingProxyType({}), ())
        with pytest.raises(AttributeError):
            r.coverage_pct = 90.0  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = RegistryReport(5, 3, 2, 60.0, MappingProxyType({"module": 3}), ()).as_dict()
        assert d["total_assets"] == 5
        assert d["coverage_pct"] == 60.0
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)

    def test_by_type_immutable(self) -> None:
        r = RegistryReport(5, 3, 2, 60.0, MappingProxyType({"module": 3}), ())
        with pytest.raises(TypeError):
            r.by_type["module"] = 999  # type: ignore[index]


class TestRegistries:
    def test_valid_types_is_tuple(self) -> None:
        assert isinstance(VALID_TYPES, tuple)

    def test_valid_types_count(self) -> None:
        assert len(VALID_TYPES) == 3

    def test_asset_registry_is_tuple(self) -> None:
        assert isinstance(ASSET_REGISTRY, tuple)

    def test_asset_registry_count(self) -> None:
        assert len(ASSET_REGISTRY) == 16

    def test_asset_registry_unique_ids(self) -> None:
        ids = [a.asset_id for a in ASSET_REGISTRY]
        assert len(ids) == len(set(ids))

    def test_asset_index_matches_registry(self) -> None:
        assert len(_ASSET_INDEX) == len(ASSET_REGISTRY)

    def test_asset_registry_valid_types(self) -> None:
        for a in ASSET_REGISTRY:
            assert a.asset_type in VALID_TYPES

    def test_asset_registry_valid_phases(self) -> None:
        for a in ASSET_REGISTRY:
            assert 301 <= a.phase <= 400

    def test_type_names_ko_complete(self) -> None:
        for t in VALID_TYPES:
            assert t in TYPE_NAMES_KO


class TestListAssets:
    def test_returns_list(self) -> None:
        data = list_assets()
        assert isinstance(data, list)
        assert len(data) == 16

    def test_has_keys(self) -> None:
        d = list_assets()[0]
        assert "asset_id" in d
        assert "phase" in d
        assert "asset_type" in d

    def test_json_serializable(self) -> None:
        text = json.dumps(list_assets(), ensure_ascii=False)
        assert isinstance(text, str)


class TestGetAsset:
    def test_valid(self) -> None:
        a = get_asset("practice_assignments")
        assert a.phase == 382

    def test_all_assets(self) -> None:
        for entry in ASSET_REGISTRY:
            a = get_asset(entry.asset_id)
            assert a.asset_id == entry.asset_id

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown asset"):
            get_asset("nonexistent")


class TestListByType:
    def test_module(self) -> None:
        data = list_by_type("module")
        assert all(d["asset_type"] == "module" for d in data)
        assert len(data) > 0

    def test_document(self) -> None:
        data = list_by_type("document")
        assert all(d["asset_type"] == "document" for d in data)

    def test_data(self) -> None:
        data = list_by_type("data")
        assert all(d["asset_type"] == "data" for d in data)

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown type"):
            list_by_type("invalid")


class TestVerifyAssets:
    def test_returns_report(self) -> None:
        report = verify_assets()
        assert isinstance(report, RegistryReport)

    def test_coverage_range(self) -> None:
        report = verify_assets()
        assert 0 <= report.coverage_pct <= 100

    def test_counts_consistent(self) -> None:
        report = verify_assets()
        assert report.verified_count + report.missing_count == report.total_assets

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(verify_assets().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = verify_assets(tmp_path)
        assert report.verified_count == 0
        assert report.missing_count == report.total_assets

    def test_partial_repo(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "simulation").mkdir()
        (tmp_path / "simulation" / "practice_assignments.py").touch()
        report = verify_assets(tmp_path)
        assert report.verified_count >= 1


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "education_asset_registry.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_list(self) -> None:
        r = self._run("--list")
        assert r.returncode == 0

    def test_list_json(self) -> None:
        r = self._run("--list", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 16

    def test_asset(self) -> None:
        r = self._run("--asset", "practice_assignments")
        assert r.returncode == 0

    def test_asset_json(self) -> None:
        r = self._run("--asset", "demo_experience", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["asset_id"] == "demo_experience"

    def test_asset_invalid(self) -> None:
        r = self._run("--asset", "nonexistent")
        assert r.returncode != 0

    def test_by_type(self) -> None:
        r = self._run("--by-type", "module")
        assert r.returncode == 0

    def test_by_type_json(self) -> None:
        r = self._run("--by-type", "document", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert all(d["asset_type"] == "document" for d in data)

    def test_by_type_invalid(self) -> None:
        r = self._run("--by-type", "invalid")
        assert r.returncode != 0

    def test_verify(self) -> None:
        r = self._run("--verify")
        assert r.returncode == 0

    def test_verify_json(self) -> None:
        r = self._run("--verify", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total_assets" in data

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
