"""GENESIS Phase 330 -- citation_validator 검증 테스트.

CITATION.cff 검증 모듈의 단위/통합 테스트 (20+개).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from simulation.citation_validator import (
    REQUIRED_FIELDS,
    CitationField,
    CitationReport,
    _validate_authors,
    _validate_license,
    _validate_version,
    generate_apa,
    generate_bibtex,
    validate_citation_cff,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _write_cff(tmp_path: Path, data: dict) -> Path:
    """헬퍼: CFF YAML 파일 작성."""
    p = tmp_path / "CITATION.cff"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture()
def valid_cff_data() -> dict:
    return {
        "cff-version": "1.2.0",
        "title": "SDACS -- Swarm Drone Airspace Control System",
        "message": "If you use this software, please cite it as below.",
        "type": "software",
        "authors": [
            {"given-names": "Sunwoo", "family-names": "Lee",
             "affiliation": "Mokpo National University"},
        ],
        "version": "1.5.0",
        "license": "MIT",
        "date-released": "2026-06-26",
        "repository-code": "https://github.com/sun475300-sudo/swarm-drone-atc",
        "keywords": ["drone", "swarm", "ATC"],
    }


@pytest.fixture()
def valid_cff(tmp_path: Path, valid_cff_data: dict) -> Path:
    return _write_cff(tmp_path, valid_cff_data)


# ---------------------------------------------------------------------------
# 1-2: CitationField 데이터클래스 테스트
# ---------------------------------------------------------------------------

class TestCitationField:
    def test_frozen(self) -> None:
        field = CitationField("title", True, True, True)
        with pytest.raises(AttributeError):
            field.name = "changed"  # type: ignore[misc]

    def test_as_dict(self) -> None:
        field = CitationField("license", False, True, True)
        d = field.as_dict()
        assert d == {"name": "license", "required": False, "present": True, "valid": True}


# ---------------------------------------------------------------------------
# 3-5: CitationReport 데이터클래스 테스트
# ---------------------------------------------------------------------------

class TestCitationReport:
    def test_frozen(self) -> None:
        report = CitationReport((), True, (), ())
        with pytest.raises(AttributeError):
            report.is_valid = False  # type: ignore[misc]

    def test_as_dict_empty(self) -> None:
        report = CitationReport((), True, (), ())
        d = report.as_dict()
        assert d["is_valid"] is True
        assert d["fields"] == []
        assert d["missing_required"] == []
        assert d["format_errors"] == []

    def test_as_dict_with_errors(self) -> None:
        f = CitationField("title", True, False, False)
        report = CitationReport((f,), False, ("title",), ("bad format",))
        d = report.as_dict()
        assert d["is_valid"] is False
        assert d["missing_required"] == ["title"]
        assert d["format_errors"] == ["bad format"]


# ---------------------------------------------------------------------------
# 6-16: validate_citation_cff 테스트
# ---------------------------------------------------------------------------

class TestValidateCff:
    def test_valid_cff_passes(self, valid_cff: Path) -> None:
        report = validate_citation_cff(valid_cff)
        assert report.is_valid is True
        assert len(report.missing_required) == 0
        assert len(report.format_errors) == 0

    def test_missing_title(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {k: v for k, v in valid_cff_data.items() if k != "title"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert report.is_valid is False
        assert "title" in report.missing_required

    def test_missing_cff_version(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {k: v for k, v in valid_cff_data.items() if k != "cff-version"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert "cff-version" in report.missing_required

    def test_missing_message(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {k: v for k, v in valid_cff_data.items() if k != "message"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert "message" in report.missing_required

    def test_missing_type(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {k: v for k, v in valid_cff_data.items() if k != "type"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert "type" in report.missing_required

    def test_missing_authors(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {k: v for k, v in valid_cff_data.items() if k != "authors"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert "authors" in report.missing_required

    def test_missing_multiple_required(self, tmp_path: Path) -> None:
        data = {"version": "1.0.0"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert report.is_valid is False
        assert len(report.missing_required) == len(REQUIRED_FIELDS)

    def test_author_missing_family_names(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {**valid_cff_data, "authors": [{"given-names": "Sunwoo"}]}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert report.is_valid is False
        assert any("family-names" in e for e in report.format_errors)

    def test_author_empty_list(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {**valid_cff_data, "authors": []}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert report.is_valid is False

    def test_invalid_version_format(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {**valid_cff_data, "version": "v1.5"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert report.is_valid is False
        assert any("semver" in e for e in report.format_errors)

    def test_invalid_license(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {**valid_cff_data, "license": "INVALID-LIC"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert report.is_valid is False
        assert any("SPDX" in e for e in report.format_errors)

    def test_invalid_keywords_type(self, tmp_path: Path, valid_cff_data: dict) -> None:
        data = {**valid_cff_data, "keywords": "not-a-list"}
        p = _write_cff(tmp_path, data)
        report = validate_citation_cff(p)
        assert report.is_valid is False

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_citation_cff(tmp_path / "nonexistent.cff")

    def test_invalid_yaml_content(self, tmp_path: Path) -> None:
        p = tmp_path / "CITATION.cff"
        p.write_text("just a string", encoding="utf-8")
        with pytest.raises(ValueError, match="YAML mapping"):
            validate_citation_cff(p)

    def test_fields_count(self, valid_cff: Path) -> None:
        """유효 CFF에서 필수 + 선택 필드 모두 보고."""
        report = validate_citation_cff(valid_cff)
        field_names = {f.name for f in report.fields}
        assert len(report.fields) >= len(REQUIRED_FIELDS)
        for req in REQUIRED_FIELDS:
            assert req in field_names


# ---------------------------------------------------------------------------
# 17-19: _validate_* 내부 함수 테스트
# ---------------------------------------------------------------------------

class TestValidateAuthors:
    def test_valid_authors(self) -> None:
        ok, errs = _validate_authors([{"family-names": "Lee", "given-names": "Sunwoo"}])
        assert ok is True
        assert errs == []

    def test_not_a_list(self) -> None:
        ok, errs = _validate_authors("not a list")
        assert ok is False

    def test_author_not_mapping(self) -> None:
        ok, errs = _validate_authors(["string author"])
        assert ok is False


class TestValidateVersion:
    def test_valid_semver(self) -> None:
        ok, _ = _validate_version("1.5.0")
        assert ok is True

    def test_invalid_semver(self) -> None:
        ok, _ = _validate_version("1.5")
        assert ok is False

    def test_non_string(self) -> None:
        ok, _ = _validate_version(1.5)
        assert ok is False


class TestValidateLicense:
    def test_valid_spdx(self) -> None:
        ok, _ = _validate_license("MIT")
        assert ok is True

    def test_invalid_spdx(self) -> None:
        ok, _ = _validate_license("FAKE")
        assert ok is False


# ---------------------------------------------------------------------------
# 20-26: generate_bibtex 테스트
# ---------------------------------------------------------------------------

class TestGenerateBibtex:
    def test_bibtex_contains_software(self, valid_cff: Path) -> None:
        bib = generate_bibtex(valid_cff)
        assert "@software{" in bib

    def test_bibtex_author(self, valid_cff: Path) -> None:
        bib = generate_bibtex(valid_cff)
        assert "Lee, Sunwoo" in bib

    def test_bibtex_title(self, valid_cff: Path) -> None:
        bib = generate_bibtex(valid_cff)
        assert "SDACS" in bib

    def test_bibtex_year(self, valid_cff: Path) -> None:
        bib = generate_bibtex(valid_cff)
        assert "2026" in bib

    def test_bibtex_version(self, valid_cff: Path) -> None:
        bib = generate_bibtex(valid_cff)
        assert "1.5.0" in bib

    def test_bibtex_url(self, valid_cff: Path) -> None:
        bib = generate_bibtex(valid_cff)
        assert "github.com" in bib

    def test_bibtex_key_format(self, valid_cff: Path) -> None:
        bib = generate_bibtex(valid_cff)
        assert bib.startswith("@software{lee2026sdacs")


# ---------------------------------------------------------------------------
# 27-31: generate_apa 테스트
# ---------------------------------------------------------------------------

class TestGenerateApa:
    def test_apa_author(self, valid_cff: Path) -> None:
        apa = generate_apa(valid_cff)
        assert "Lee, S." in apa

    def test_apa_year(self, valid_cff: Path) -> None:
        apa = generate_apa(valid_cff)
        assert "(2026)" in apa

    def test_apa_title(self, valid_cff: Path) -> None:
        apa = generate_apa(valid_cff)
        assert "SDACS" in apa

    def test_apa_version(self, valid_cff: Path) -> None:
        apa = generate_apa(valid_cff)
        assert "(Version 1.5.0)" in apa

    def test_apa_computer_software(self, valid_cff: Path) -> None:
        apa = generate_apa(valid_cff)
        assert "[Computer software]" in apa


# ---------------------------------------------------------------------------
# 32-34: CLI 테스트
# ---------------------------------------------------------------------------

class TestCli:
    def test_validate_cli(self, valid_cff: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.citation_validator",
             "--validate", "--json", "--path", str(valid_cff)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["is_valid"] is True

    def test_bibtex_cli(self, valid_cff: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.citation_validator",
             "--bibtex", "--path", str(valid_cff)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0
        assert "@software{" in result.stdout

    def test_apa_cli(self, valid_cff: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.citation_validator",
             "--apa", "--path", str(valid_cff)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0
        assert "Lee, S." in result.stdout
