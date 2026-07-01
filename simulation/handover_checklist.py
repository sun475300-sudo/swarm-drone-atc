"""GENESIS Phase 394 -- 인수인계 체크리스트.

후임 기수·유지보수자를 위한 프로젝트 인수인계 체크리스트.
5개 카테고리(환경·문서·계정·데이터·지식전수)의 25개 항목을
파일시스템 기반으로 자동 판정합니다.

CLI:
    python simulation/handover_checklist.py --check
    python simulation/handover_checklist.py --category environment
    python simulation/handover_checklist.py --categories
    python simulation/handover_checklist.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

VALID_CATEGORIES: tuple[str, ...] = (
    "environment",
    "documentation",
    "accounts",
    "data",
    "knowledge",
)

CATEGORY_NAMES_KO: dict[str, str] = {
    "environment": "환경 설정",
    "documentation": "문서 완비",
    "accounts": "계정·권한",
    "data": "데이터·자산",
    "knowledge": "지식 전수",
}


@dataclass(frozen=True)
class HandoverItem:
    """인수인계 체크 항목."""

    item_id: str
    category: str
    description: str
    auto_checkable: bool
    passed: bool
    note: str

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {self.category}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "description": self.description,
            "auto_checkable": self.auto_checkable,
            "passed": self.passed,
            "note": self.note,
        }


@dataclass(frozen=True)
class CategoryResult:
    """카테고리별 결과."""

    category: str
    name_ko: str
    items: tuple[HandoverItem, ...]
    passed_count: int
    total_count: int

    @property
    def completion_pct(self) -> float:
        if self.total_count == 0:
            return 0.0
        return round(self.passed_count / self.total_count * 100, 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "name_ko": self.name_ko,
            "passed_count": self.passed_count,
            "total_count": self.total_count,
            "completion_pct": self.completion_pct,
            "items": [i.as_dict() for i in self.items],
        }


@dataclass(frozen=True)
class HandoverReport:
    """인수인계 보고서."""

    categories: tuple[CategoryResult, ...]
    total_items: int
    total_passed: int
    overall_pct: float
    readiness: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "total_passed": self.total_passed,
            "overall_pct": self.overall_pct,
            "readiness": self.readiness,
            "categories": [c.as_dict() for c in self.categories],
        }


ITEM_DEFINITIONS: tuple[tuple[str, str, str, bool], ...] = (
    ("env_python", "environment", "Python 3.10+ 설치 확인", False),
    ("env_requirements", "environment", "requirements.txt 존재", True),
    ("env_pyproject", "environment", "pyproject.toml 존재", True),
    ("env_config", "environment", "config/ 디렉토리 존재", True),
    ("env_gitignore", "environment", ".gitignore 존재", True),
    ("doc_readme", "documentation", "README.md 존재", True),
    ("doc_claude", "documentation", "CLAUDE.md 개발 가이드 존재", True),
    ("doc_roadmap", "documentation", "ROADMAP.md 존재", True),
    ("doc_changelog", "documentation", "CHANGELOG.md 존재", True),
    ("doc_api", "documentation", "docs/ API 문서 디렉토리 존재", True),
    ("doc_license", "documentation", "LICENSE 파일 존재", True),
    ("acc_github", "accounts", "GitHub 레포 접근 권한", False),
    ("acc_ci", "accounts", "CI/CD 파이프라인 접근 권한", False),
    ("acc_deploy", "accounts", "배포 환경 접근 권한", False),
    ("acc_secrets", "accounts", "시크릿/환경변수 인계", False),
    ("data_db", "data", "데이터베이스 백업/접근", False),
    ("data_assets", "data", "정적 자산 인계", True),
    ("data_test_data", "data", "테스트 데이터 존재", True),
    ("data_config_yaml", "data", "시뮬레이션 설정 YAML 존재", True),
    ("data_results", "data", "결과/리포트 디렉토리 존재", True),
    ("know_architecture", "knowledge", "아키텍처 설명 문서", True),
    ("know_onboarding", "knowledge", "온보딩 자동화 모듈 존재", True),
    ("know_curriculum", "knowledge", "커리큘럼/교육 자료 존재", True),
    ("know_troubleshoot", "knowledge", "트러블슈팅 가이드 존재", True),
    ("know_contact", "knowledge", "이전 개발자 연락처", False),
)


def _note(ok: bool, name: str) -> str:
    return name if ok else "누락"


def _build_auto_checks(root: pathlib.Path) -> dict[str, tuple[bool, str]]:
    """자동 판정 가능한 항목의 결과 맵을 구축."""
    e = {p: (root / p).exists() for p in (
        "requirements.txt", "pyproject.toml", ".gitignore",
        "README.md", "CLAUDE.md", "ROADMAP.md", "CHANGELOG.md", "LICENSE",
        "simulation/onboarding_automation.py",
        "simulation/curriculum_slide_package.py",
        "docs/TECH_DEBT_LEDGER.md", "docs/TROUBLESHOOTING.md",
        "docs/ARCHITECTURE.md",
    )}
    d = {p: (root / p).is_dir() for p in (
        "config", "docs", "tests", "results",
        "docs/images", "static",
    )}
    has_yaml = d["config"] and any((root / "config").glob("*.yaml"))
    has_assets = d["docs/images"] or d["static"]
    has_arch = e["CLAUDE.md"] or e["docs/ARCHITECTURE.md"]
    has_trouble = e["docs/TECH_DEBT_LEDGER.md"] or e["docs/TROUBLESHOOTING.md"]

    return {
        "env_requirements": (e["requirements.txt"], _note(e["requirements.txt"], "requirements.txt")),
        "env_pyproject": (e["pyproject.toml"], _note(e["pyproject.toml"], "pyproject.toml")),
        "env_config": (d["config"], _note(d["config"], "config/")),
        "env_gitignore": (e[".gitignore"], _note(e[".gitignore"], ".gitignore")),
        "doc_readme": (e["README.md"], _note(e["README.md"], "README.md")),
        "doc_claude": (e["CLAUDE.md"], _note(e["CLAUDE.md"], "CLAUDE.md")),
        "doc_roadmap": (e["ROADMAP.md"], _note(e["ROADMAP.md"], "ROADMAP.md")),
        "doc_changelog": (e["CHANGELOG.md"], _note(e["CHANGELOG.md"], "CHANGELOG.md")),
        "doc_api": (d["docs"], _note(d["docs"], "docs/")),
        "doc_license": (e["LICENSE"], _note(e["LICENSE"], "LICENSE")),
        "data_assets": (has_assets, "정적 자산 존재" if has_assets else "누락"),
        "data_test_data": (d["tests"], _note(d["tests"], "tests/")),
        "data_config_yaml": (has_yaml, "YAML 설정 존재" if has_yaml else "누락"),
        "data_results": (d["results"], _note(d["results"], "results/")),
        "know_architecture": (has_arch, "아키텍처 문서 존재" if has_arch else "누락"),
        "know_onboarding": (e["simulation/onboarding_automation.py"], _note(e["simulation/onboarding_automation.py"], "온보딩 모듈")),
        "know_curriculum": (e["simulation/curriculum_slide_package.py"], _note(e["simulation/curriculum_slide_package.py"], "커리큘럼 모듈")),
        "know_troubleshoot": (has_trouble, "트러블슈팅 문서 존재" if has_trouble else "누락"),
    }


def _check_items(
    repo_root: pathlib.Path | None = None,
) -> tuple[HandoverItem, ...]:
    """모든 인수인계 항목 자동 판정."""
    root = repo_root or _REPO_ROOT
    auto_checks = _build_auto_checks(root)

    items: list[HandoverItem] = []
    for iid, cat, desc, auto in ITEM_DEFINITIONS:
        if auto and iid in auto_checks:
            passed, note = auto_checks[iid]
        elif not auto:
            passed, note = False, "수동 확인 필요"
        else:
            passed, note = False, "판정 불가"
        items.append(HandoverItem(iid, cat, desc, auto, passed, note))
    return tuple(items)


def _score_category(
    category: str, items: tuple[HandoverItem, ...],
) -> CategoryResult:
    """카테고리별 결과 산정."""
    cat_items = tuple(i for i in items if i.category == category)
    passed = sum(1 for i in cat_items if i.passed)
    return CategoryResult(
        category=category,
        name_ko=CATEGORY_NAMES_KO[category],
        items=cat_items,
        passed_count=passed,
        total_count=len(cat_items),
    )


def _compute_readiness(pct: float) -> str:
    if pct >= 90:
        return "준비 완료"
    if pct >= 70:
        return "거의 완료"
    if pct >= 50:
        return "진행 중"
    return "미준비"


def check_handover(
    repo_root: pathlib.Path | None = None,
) -> HandoverReport:
    """인수인계 체크리스트 실행."""
    items = _check_items(repo_root)

    cat_results: list[CategoryResult] = []
    for cat in VALID_CATEGORIES:
        cat_results.append(_score_category(cat, items))

    total = len(items)
    passed = sum(1 for i in items if i.passed)
    pct = round(passed / total * 100, 1) if total > 0 else 0.0

    return HandoverReport(
        categories=tuple(cat_results),
        total_items=total,
        total_passed=passed,
        overall_pct=pct,
        readiness=_compute_readiness(pct),
    )


def get_category(
    category: str,
    repo_root: pathlib.Path | None = None,
) -> CategoryResult:
    """특정 카테고리 결과 조회."""
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Unknown category: {category}. "
            f"Valid: {', '.join(VALID_CATEGORIES)}"
        )
    items = _check_items(repo_root)
    return _score_category(category, items)


def list_categories() -> list[dict[str, str]]:
    """사용 가능한 카테고리 목록."""
    return [
        {"category": c, "name_ko": CATEGORY_NAMES_KO[c]}
        for c in VALID_CATEGORIES
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 394 -- 인수인계 체크리스트",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="전체 체크")
    group.add_argument("--category", type=str, help="특정 카테고리")
    group.add_argument("--categories", action="store_true", help="카테고리 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.check:
        _print_check(args.json)
    elif args.category:
        _print_category(args.category, args.json)
    elif args.categories:
        _print_categories(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_check(as_json: bool) -> None:
    report = check_handover()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=== SDACS 인수인계 체크리스트 ===")
    print(f"  상태: {report.readiness}")
    print(f"  완료: {report.total_passed}/{report.total_items} ({report.overall_pct}%)")
    print()
    for c in report.categories:
        filled = max(0, min(10, int(c.completion_pct / 10)))
        bar = "█" * filled + "░" * (10 - filled)
        print(f"  [{c.name_ko}] {bar} {c.completion_pct}%")
        for i in c.items:
            marker = "+" if i.passed else "-"
            auto = "" if i.auto_checkable else " (수동)"
            print(f"    {marker} {i.description}{auto}")


def _print_category(category: str, as_json: bool) -> None:
    try:
        c = get_category(category)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(c.as_dict(), ensure_ascii=False, indent=2))
        return
    print(f"=== {c.name_ko} ===")
    print(f"  완료: {c.passed_count}/{c.total_count} ({c.completion_pct}%)")
    print()
    for i in c.items:
        marker = "+" if i.passed else "-"
        print(f"  {marker} {i.description}: {i.note}")


def _print_categories(as_json: bool) -> None:
    data = list_categories()
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("=== 인수인계 카테고리 ===")
    for d in data:
        print(f"  {d['category']}: {d['name_ko']}")


if __name__ == "__main__":
    _main()
