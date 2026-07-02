"""GENESIS Phase 330 -- 학술 인용 추적 (CITATION.cff 검증).

CFF 1.2.0 명세 기반으로 CITATION.cff 파일을 검증하고,
BibTeX / APA 인용 문자열을 생성합니다.

CLI:
    python simulation/citation_validator.py --validate
    python simulation/citation_validator.py --bibtex
    python simulation/citation_validator.py --apa
    python simulation/citation_validator.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CFF = _REPO_ROOT / "CITATION.cff"

REQUIRED_FIELDS: tuple[str, ...] = (
    "cff-version", "title", "message", "type", "authors",
)

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# 주요 SPDX 라이선스 식별자 (간소화 목록)
_SPDX_IDS: frozenset[str] = frozenset((
    "MIT", "Apache-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
    "GPL-3.0-only", "GPL-3.0-or-later", "BSD-2-Clause",
    "BSD-3-Clause", "LGPL-2.1-only", "LGPL-2.1-or-later",
    "LGPL-3.0-only", "LGPL-3.0-or-later", "MPL-2.0",
    "ISC", "Unlicense", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0",
    "AGPL-3.0-only", "AGPL-3.0-or-later", "BSL-1.0", "Zlib",
))


@dataclass(frozen=True)
class CitationField:
    """CFF 필드 검증 결과."""

    name: str
    required: bool
    present: bool
    valid: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "required": self.required,
            "present": self.present,
            "valid": self.valid,
        }


@dataclass(frozen=True)
class CitationReport:
    """CFF 검증 보고서."""

    fields: tuple[CitationField, ...]
    is_valid: bool
    missing_required: tuple[str, ...]
    format_errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "fields": [f.as_dict() for f in self.fields],
            "is_valid": self.is_valid,
            "missing_required": list(self.missing_required),
            "format_errors": list(self.format_errors),
        }


def _load_cff(path: str | Path) -> dict[str, Any]:
    """YAML 파일 로드 (읽기 전용)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"CITATION.cff not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("CITATION.cff must be a YAML mapping")
    return data


def _validate_authors(authors: Any) -> tuple[bool, list[str]]:
    """저자 필드 검증 -- family-names 필수."""
    errors: list[str] = []
    if not isinstance(authors, list) or len(authors) == 0:
        return False, ["authors must be a non-empty list"]
    for i, author in enumerate(authors):
        if not isinstance(author, dict):
            errors.append(f"authors[{i}] is not a mapping")
            continue
        if "family-names" not in author:
            errors.append(f"authors[{i}] missing family-names")
    is_valid = len(errors) == 0
    return is_valid, errors


def _validate_version(version: Any) -> tuple[bool, list[str]]:
    """버전 필드 semver 형식 검증."""
    if not isinstance(version, str):
        return False, [f"version must be a string, got {type(version).__name__}"]
    if not _SEMVER_RE.match(version):
        return False, [f"version '{version}' is not semver (X.Y.Z)"]
    return True, []


def _validate_license(license_id: Any) -> tuple[bool, list[str]]:
    """라이선스 SPDX 식별자 검증."""
    if not isinstance(license_id, str):
        return False, [f"license must be a string, got {type(license_id).__name__}"]
    if license_id not in _SPDX_IDS:
        return False, [f"license '{license_id}' is not a recognized SPDX identifier"]
    return True, []


def validate_citation_cff(path: str | Path = _DEFAULT_CFF) -> CitationReport:
    """CITATION.cff 를 CFF 1.2.0 명세에 따라 검증."""
    data = _load_cff(path)

    fields: list[CitationField] = []
    format_errors: list[str] = []
    missing_required: list[str] = []

    # 필수 필드 검사
    for field_name in REQUIRED_FIELDS:
        present = field_name in data
        valid = present
        if not present:
            missing_required.append(field_name)
        elif field_name == "authors":
            author_valid, author_errs = _validate_authors(data[field_name])
            valid = author_valid
            format_errors.extend(author_errs)
        fields.append(CitationField(field_name, True, present, valid))

    # 선택 필드 검사
    if "version" in data:
        ver_valid, ver_errs = _validate_version(data["version"])
        fields.append(CitationField("version", False, True, ver_valid))
        format_errors.extend(ver_errs)

    if "license" in data:
        lic_valid, lic_errs = _validate_license(data["license"])
        fields.append(CitationField("license", False, True, lic_valid))
        format_errors.extend(lic_errs)

    if "date-released" in data:
        fields.append(CitationField("date-released", False, True, True))

    if "repository-code" in data:
        fields.append(CitationField("repository-code", False, True, True))

    if "keywords" in data:
        kw_valid = isinstance(data["keywords"], list)
        if not kw_valid:
            format_errors.append("keywords must be a list")
        fields.append(CitationField("keywords", False, True, kw_valid))

    is_valid = len(missing_required) == 0 and len(format_errors) == 0

    return CitationReport(
        fields=tuple(fields),
        is_valid=is_valid,
        missing_required=tuple(missing_required),
        format_errors=tuple(format_errors),
    )


def _author_to_bibtex(author: dict[str, Any]) -> str:
    """저자 dict를 BibTeX 형식 문자열로 변환."""
    family = author.get("family-names", "")
    given = author.get("given-names", "")
    if given:
        return f"{family}, {given}"
    return family


def generate_bibtex(path: str | Path = _DEFAULT_CFF) -> str:
    """CFF 파일에서 BibTeX @software 엔트리 생성."""
    data = _load_cff(path)

    authors = data.get("authors", [])
    author_strs = [_author_to_bibtex(a) for a in authors if isinstance(a, dict)]
    author_line = " and ".join(author_strs)

    title = data.get("title", "Untitled")
    year = ""
    date_released = data.get("date-released", "")
    if isinstance(date_released, str) and len(date_released) >= 4:
        year = date_released[:4]

    version = data.get("version", "")
    url = data.get("repository-code", data.get("url", ""))

    # 키 생성: 첫 저자 family-names + year
    first_family = authors[0].get("family-names", "unknown") if authors else "unknown"
    key = f"{first_family.lower()}{year}sdacs"

    lines = [
        f"@software{{{key},",
        f"  author       = {{{author_line}}},",
        f"  title        = {{{{{title}}}}},",
        f"  year         = {{{year}}},",
    ]
    if version:
        lines.append(f"  version      = {{{version}}},")
    if url:
        lines.append(f"  url          = {{{url}}},")
    lines.append("}")

    return "\n".join(lines)


def generate_apa(path: str | Path = _DEFAULT_CFF) -> str:
    """CFF 파일에서 APA 스타일 인용 문자열 생성."""
    data = _load_cff(path)

    authors = data.get("authors", [])
    apa_authors: list[str] = []
    for a in authors:
        if not isinstance(a, dict):
            continue
        family = a.get("family-names", "")
        given = a.get("given-names", "")
        initials = ". ".join(c[0] for c in given.split() if c) + "." if given else ""
        apa_authors.append(f"{family}, {initials}" if initials else family)

    author_str = ", ".join(apa_authors) if apa_authors else "Unknown"

    date_released = data.get("date-released", "")
    year = ""
    if isinstance(date_released, str) and len(date_released) >= 4:
        year = date_released[:4]

    title = data.get("title", "Untitled")
    version = data.get("version", "")
    url = data.get("repository-code", data.get("url", ""))

    version_part = f" (Version {version})" if version else ""
    url_part = f" {url}" if url else ""

    return f"{author_str} ({year}). {title}{version_part} [Computer software].{url_part}"


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 330 -- CITATION.cff 검증 및 인용 생성",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--validate", action="store_true", help="CFF 검증")
    group.add_argument("--bibtex", action="store_true", help="BibTeX 생성")
    group.add_argument("--apa", action="store_true", help="APA 인용 생성")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--path", type=str, default=None, help="CFF 파일 경로")
    args = parser.parse_args()

    cff_path = Path(args.path) if args.path else _DEFAULT_CFF

    if args.validate:
        _print_validate(cff_path, args.json)
    elif args.bibtex:
        _print_bibtex(cff_path)
    elif args.apa:
        _print_apa(cff_path)
    else:
        parser.print_help()
        sys.exit(1)


def _print_validate(path: Path, as_json: bool) -> None:
    report = validate_citation_cff(path)
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    status = "PASS" if report.is_valid else "FAIL"
    print(f"CITATION.cff validation: {status}")
    for f in report.fields:
        mark = "ok" if f.valid else ("--" if not f.present else "ERR")
        req = "*" if f.required else " "
        print(f"  [{mark}] {req} {f.name}")
    if report.missing_required:
        print(f"  Missing required: {', '.join(report.missing_required)}")
    if report.format_errors:
        for err in report.format_errors:
            print(f"  Error: {err}")


def _print_bibtex(path: Path) -> None:
    print(generate_bibtex(path))


def _print_apa(path: Path) -> None:
    print(generate_apa(path))


if __name__ == "__main__":
    _main()
