"""GENESIS Phase 390 -- 아카이브 전략 (Zenodo + Software Heritage).

졸업 후 프로젝트 보존을 위한 아카이브 전략 모듈.
Zenodo 메타데이터 검증 · Software Heritage 등재 준비 · 졸업 아카이브 체크리스트.

구성 요소
---------
1. **ZenodoValidation**: `.zenodo.json` 필드 검증 결과
2. **SwhSaveRequest**: Software Heritage save-now 요청 정보
3. **ArchiveChecklist**: 졸업 아카이브 체크리스트 항목
4. **ArchiveStrategy**: 전체 전략 보고서

설계 원칙
---------
- frozen dataclass, 결정적, 부수효과 0
- Phase 489 (archive_redundancy.py)와 보완 관계: 489=이중화 판정, 390=전략·체크리스트
- `.zenodo.json` 파일만 읽기 (쓰지 않음)

CLI:
    python simulation/archive_strategy.py --validate        # Zenodo 메타데이터 검증
    python simulation/archive_strategy.py --swh             # SWH 등재 정보
    python simulation/archive_strategy.py --checklist       # 졸업 아카이브 체크리스트
    python simulation/archive_strategy.py --report          # 전체 보고서
    python simulation/archive_strategy.py --json            # JSON 출력
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

ZENODO_REQUIRED_FIELDS: tuple[str, ...] = (
    "title", "description", "creators", "upload_type",
    "access_right", "license", "keywords",
)

ZENODO_RECOMMENDED_FIELDS: tuple[str, ...] = (
    "communities", "language", "related_identifiers", "notes",
)

_SWH_FALLBACK_URL = "https://github.com/sun475300-sudo/swarm-drone-atc"
SWH_SAVE_API = "https://archive.softwareheritage.org/api/1/origin/save/git/url/"


def _detect_origin_url() -> str:
    """git remote origin URL을 감지, 실패 시 폴백."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
            cwd=str(_REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            url = result.stdout.strip()
            if url.endswith(".git"):
                url = url[:-4]
            if url.startswith("git@github.com:"):
                url = "https://github.com/" + url[15:]
            return url
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return _SWH_FALLBACK_URL


SWH_ORIGIN_URL: str = _detect_origin_url()


@dataclass(frozen=True)
class FieldCheck:
    """필드 검증 결과."""

    field: str
    required: bool
    present: bool
    valid: bool
    message: str


@dataclass(frozen=True)
class ZenodoValidation:
    """Zenodo 메타데이터 검증 보고서."""

    file_exists: bool
    checks: tuple[FieldCheck, ...]
    required_pass: int
    required_total: int
    recommended_pass: int
    recommended_total: int

    @property
    def is_complete(self) -> bool:
        return self.required_pass == self.required_total

    def as_dict(self) -> dict[str, Any]:
        return {
            "file_exists": self.file_exists,
            "required_pass": self.required_pass,
            "required_total": self.required_total,
            "recommended_pass": self.recommended_pass,
            "recommended_total": self.recommended_total,
            "is_complete": self.is_complete,
            "checks": [
                {
                    "field": c.field, "required": c.required,
                    "present": c.present, "valid": c.valid,
                    "message": c.message,
                }
                for c in self.checks
            ],
        }


@dataclass(frozen=True)
class SwhSaveRequest:
    """Software Heritage save-now 요청 정보."""

    origin_url: str
    visit_type: str
    api_endpoint: str
    curl_command: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "origin_url": self.origin_url,
            "visit_type": self.visit_type,
            "api_endpoint": self.api_endpoint,
            "curl_command": self.curl_command,
        }


ARCHIVE_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("zenodo_metadata", "Zenodo 메타데이터(.zenodo.json) 작성", "필수"),
    ("zenodo_upload", "GitHub Release 태그 → Zenodo 자동 아카이브 연동", "필수"),
    ("swh_save", "Software Heritage save-now 요청 실행", "필수"),
    ("github_release", "GitHub Release 생성 (v1.0.0 태그)", "필수"),
    ("readme_doi", "README.md에 Zenodo DOI 배지 추가", "권장"),
    ("citation_file", "CITATION.cff 파일 생성", "권장"),
    ("codemeta", "codemeta.json 메타데이터 생성", "권장"),
    ("license_check", "LICENSE 파일 존재 확인 (MIT)", "필수"),
    ("gitignore_clean", ".gitignore에 불필요 파일 제외 확인", "권장"),
    ("docs_freeze", "문서 스냅샷 (docs/ 완결성 확인)", "필수"),
    ("test_pass", "전체 테스트 스위트 통과 확인", "필수"),
    ("changelog", "CHANGELOG.md 최종 버전 기록", "권장"),
)


@dataclass(frozen=True)
class ArchiveCheckItem:
    """아카이브 체크리스트 항목."""

    item_id: str
    description: str
    priority: str
    completed: bool


@dataclass(frozen=True)
class ArchiveStrategy:
    """전체 아카이브 전략 보고서."""

    zenodo: ZenodoValidation
    swh: SwhSaveRequest
    checklist: tuple[ArchiveCheckItem, ...]
    required_done: int
    required_total: int
    recommended_done: int
    recommended_total: int

    @property
    def readiness_pct(self) -> float:
        total = self.required_total + self.recommended_total
        if total == 0:
            return 0.0
        done = self.required_done + self.recommended_done
        return round(done / total * 100, 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "zenodo": self.zenodo.as_dict(),
            "swh": self.swh.as_dict(),
            "checklist": [
                {
                    "id": c.item_id, "description": c.description,
                    "priority": c.priority, "completed": c.completed,
                }
                for c in self.checklist
            ],
            "required_done": self.required_done,
            "required_total": self.required_total,
            "recommended_done": self.recommended_done,
            "recommended_total": self.recommended_total,
            "readiness_pct": self.readiness_pct,
        }


def validate_zenodo(zenodo_path: str | None = None) -> ZenodoValidation:
    """`.zenodo.json` 메타데이터 검증."""
    path = pathlib.Path(zenodo_path) if zenodo_path else _REPO_ROOT / ".zenodo.json"

    if not path.exists():
        checks = tuple(
            FieldCheck(f, f in ZENODO_REQUIRED_FIELDS, False, False, "파일 없음")
            for f in (*ZENODO_REQUIRED_FIELDS, *ZENODO_RECOMMENDED_FIELDS)
        )
        return ZenodoValidation(
            file_exists=False, checks=checks,
            required_pass=0, required_total=len(ZENODO_REQUIRED_FIELDS),
            recommended_pass=0, recommended_total=len(ZENODO_RECOMMENDED_FIELDS),
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        checks = tuple(
            FieldCheck(f, f in ZENODO_REQUIRED_FIELDS, False, False, "파싱 오류")
            for f in (*ZENODO_REQUIRED_FIELDS, *ZENODO_RECOMMENDED_FIELDS)
        )
        return ZenodoValidation(
            file_exists=True, checks=checks,
            required_pass=0, required_total=len(ZENODO_REQUIRED_FIELDS),
            recommended_pass=0, recommended_total=len(ZENODO_RECOMMENDED_FIELDS),
        )

    field_checks: list[FieldCheck] = []
    req_pass = 0
    rec_pass = 0

    for field in ZENODO_REQUIRED_FIELDS:
        present = field in data
        valid = present and bool(data[field])
        msg = "OK" if valid else ("비어있음" if present else "누락")
        field_checks.append(FieldCheck(field, True, present, valid, msg))
        if valid:
            req_pass += 1

    for field in ZENODO_RECOMMENDED_FIELDS:
        present = field in data
        valid = present and bool(data[field])
        msg = "OK" if valid else ("비어있음" if present else "누락 (권장)")
        field_checks.append(FieldCheck(field, False, present, valid, msg))
        if valid:
            rec_pass += 1

    return ZenodoValidation(
        file_exists=True,
        checks=tuple(field_checks),
        required_pass=req_pass,
        required_total=len(ZENODO_REQUIRED_FIELDS),
        recommended_pass=rec_pass,
        recommended_total=len(ZENODO_RECOMMENDED_FIELDS),
    )


def build_swh_request(origin_url: str = SWH_ORIGIN_URL) -> SwhSaveRequest:
    """Software Heritage save-now 요청 정보 생성."""
    json_body = json.dumps(
        {"origin_url": origin_url, "visit_type": "git"},
        ensure_ascii=False,
    )
    return SwhSaveRequest(
        origin_url=origin_url,
        visit_type="git",
        api_endpoint=SWH_SAVE_API,
        curl_command=(
            f"curl -X POST \"{SWH_SAVE_API}\" "
            f"-H \"Content-Type: application/json\" "
            f"-d '{json_body}'"
        ),
    )


def build_checklist(repo_root: pathlib.Path | None = None) -> tuple[ArchiveCheckItem, ...]:
    """졸업 아카이브 체크리스트 생성 (현재 상태 자동 판정)."""
    root = repo_root or _REPO_ROOT

    auto_checks: dict[str, bool] = {
        "zenodo_metadata": (root / ".zenodo.json").exists(),
        "license_check": (root / "LICENSE").exists(),
        "docs_freeze": (root / "docs").is_dir(),
        "changelog": (root / "CHANGELOG.md").exists(),
        "citation_file": (root / "CITATION.cff").exists(),
        "codemeta": (root / "codemeta.json").exists(),
        "gitignore_clean": (root / ".gitignore").exists(),
        "readme_doi": _readme_has_doi_badge(root / "README.md"),
    }

    items: list[ArchiveCheckItem] = []
    for item_id, desc, priority in ARCHIVE_ITEMS:
        completed = auto_checks.get(item_id, False)
        items.append(ArchiveCheckItem(item_id, desc, priority, completed))

    return tuple(items)


def _readme_has_doi_badge(readme_path: pathlib.Path) -> bool:
    """README에 DOI 배지가 있는지 확인."""
    if not readme_path.exists():
        return False
    try:
        content = readme_path.read_text(encoding="utf-8")
        return "doi.org" in content.lower() or "zenodo" in content.lower()
    except OSError:
        return False


def build_strategy(
    zenodo_path: str | None = None,
    repo_root: pathlib.Path | None = None,
) -> ArchiveStrategy:
    """전체 아카이브 전략 보고서 생성."""
    zenodo = validate_zenodo(zenodo_path)
    swh = build_swh_request()
    checklist = build_checklist(repo_root)

    req_done = sum(1 for c in checklist if c.priority == "필수" and c.completed)
    req_total = sum(1 for c in checklist if c.priority == "필수")
    rec_done = sum(1 for c in checklist if c.priority == "권장" and c.completed)
    rec_total = sum(1 for c in checklist if c.priority == "권장")

    return ArchiveStrategy(
        zenodo=zenodo, swh=swh, checklist=checklist,
        required_done=req_done, required_total=req_total,
        recommended_done=rec_done, recommended_total=rec_total,
    )


# -- CLI --

def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="GENESIS Phase 390 -- 아카이브 전략")
    parser.add_argument("--validate", action="store_true", help="Zenodo 메타데이터 검증")
    parser.add_argument("--swh", action="store_true", help="Software Heritage 등재 정보")
    parser.add_argument("--checklist", action="store_true", help="졸업 아카이브 체크리스트")
    parser.add_argument("--report", action="store_true", help="전체 보고서")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.validate:
        result = validate_zenodo()
        if args.json:
            print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        else:
            status = "완료" if result.is_complete else "미완료"
            print(f"=== Zenodo 메타데이터 검증 ({status}) ===")
            print(f"  파일 존재: {'예' if result.file_exists else '아니오'}")
            print(f"  필수 필드: {result.required_pass}/{result.required_total}")
            print(f"  권장 필드: {result.recommended_pass}/{result.recommended_total}")
            print()
            for c in result.checks:
                marker = "+" if c.valid else "-"
                req = "필수" if c.required else "권장"
                print(f"  {marker} [{req}] {c.field}: {c.message}")

    elif args.swh:
        result = build_swh_request()
        if args.json:
            print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        else:
            print("=== Software Heritage Save-Now ===")
            print(f"  Origin URL: {result.origin_url}")
            print(f"  Visit Type: {result.visit_type}")
            print(f"  API: {result.api_endpoint}")
            print("\n  실행 명령:")
            print(f"    {result.curl_command}")

    elif args.checklist:
        items = build_checklist()
        if args.json:
            print(json.dumps([
                {"id": c.item_id, "description": c.description,
                 "priority": c.priority, "completed": c.completed}
                for c in items
            ], ensure_ascii=False, indent=2))
        else:
            print("=== 졸업 아카이브 체크리스트 ===")
            for c in items:
                marker = "+" if c.completed else "o"
                print(f"  {marker} [{c.priority}] {c.description}")

    elif args.report:
        strategy = build_strategy()
        if args.json:
            print(json.dumps(strategy.as_dict(), ensure_ascii=False, indent=2))
        else:
            print("=== 아카이브 전략 보고서 ===")
            print(f"  준비도: {strategy.readiness_pct}%")
            print(f"  필수 항목: {strategy.required_done}/{strategy.required_total}")
            print(f"  권장 항목: {strategy.recommended_done}/{strategy.recommended_total}")
            print()
            z = strategy.zenodo
            zs = "완료" if z.is_complete else "미완료"
            print(f"  [Zenodo] 메타데이터: {zs} ({z.required_pass}/{z.required_total})")
            print(f"  [SWH] Origin: {strategy.swh.origin_url}")
            print()
            print("  체크리스트:")
            for c in strategy.checklist:
                marker = "+" if c.completed else "o"
                print(f"    {marker} [{c.priority}] {c.description}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()
