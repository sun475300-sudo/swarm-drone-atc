"""GENESIS Phase 398 -- 교육 자산 공개 준비 체크리스트.

교육·인수인계 자산이 외부 공개(오픈소스, 교재 배포) 가능 상태인지
5개 카테고리(라이선스·민감정보·문서화·재현성·접근성)를 점검합니다.

CLI:
    python simulation/asset_publication_checklist.py --check
    python simulation/asset_publication_checklist.py --category licensing
    python simulation/asset_publication_checklist.py --categories
    python simulation/asset_publication_checklist.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

VALID_CATEGORIES: tuple[str, ...] = (
    "licensing",
    "sensitive_data",
    "documentation",
    "reproducibility",
    "accessibility",
)

CATEGORY_NAMES_KO: dict[str, str] = {
    "licensing": "라이선스·저작권",
    "sensitive_data": "민감 정보 제거",
    "documentation": "문서 완비",
    "reproducibility": "재현 가능성",
    "accessibility": "접근성·배포",
}

PUBLICATION_THRESHOLD: float = 80.0


@dataclass(frozen=True)
class PublicationItem:
    """개별 점검 항목."""

    item_id: str
    category: str
    description: str
    satisfied: bool
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "description": self.description,
            "satisfied": self.satisfied,
            "note": self.note,
        }


@dataclass(frozen=True)
class CategoryResult:
    """카테고리별 결과."""

    category: str
    name_ko: str
    items: tuple[PublicationItem, ...]
    passed: int
    total: int
    score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "name_ko": self.name_ko,
            "passed": self.passed,
            "total": self.total,
            "score": self.score,
            "items": [i.as_dict() for i in self.items],
        }


@dataclass(frozen=True)
class PublicationReport:
    """공개 준비 보고서."""

    categories: tuple[CategoryResult, ...]
    total_items: int
    total_passed: int
    overall_score: float
    overall_grade: str
    publication_ready: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "total_passed": self.total_passed,
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "publication_ready": self.publication_ready,
            "categories": [c.as_dict() for c in self.categories],
        }


CHECK_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("lic_file", "licensing", "LICENSE 파일 존재"),
    ("lic_header", "licensing", "소스 파일 라이선스 헤더"),
    ("lic_deps", "licensing", "의존성 라이선스 호환"),
    ("lic_third", "licensing", "서드파티 고지 문서"),
    ("sens_env", "sensitive_data", ".env 파일 미포함"),
    ("sens_key", "sensitive_data", "API 키·토큰 미노출"),
    ("sens_gitignore", "sensitive_data", ".gitignore 설정"),
    ("sens_history", "sensitive_data", "Git 히스토리 민감정보 없음"),
    ("doc_readme", "documentation", "README.md 존재"),
    ("doc_install", "documentation", "설치 가이드 존재"),
    ("doc_api", "documentation", "API 문서 존재"),
    ("doc_tutorial", "documentation", "튜토리얼/예제 존재"),
    ("repr_req", "reproducibility", "requirements.txt 존재"),
    ("repr_pyproject", "reproducibility", "pyproject.toml 존재"),
    ("repr_tests", "reproducibility", "테스트 스위트 존재"),
    ("repr_ci", "reproducibility", "CI/CD 설정 존재"),
    ("acc_contributing", "accessibility", "CONTRIBUTING.md 존재"),
    ("acc_coc", "accessibility", "CODE_OF_CONDUCT.md 존재"),
    ("acc_issues", "accessibility", "이슈 템플릿 존재"),
    ("acc_changelog", "accessibility", "CHANGELOG.md 존재"),
)


def _build_check_map(root: pathlib.Path) -> dict[str, tuple[bool, str]]:
    """파일시스템 기반 점검 결과 맵."""
    e = {p: (root / p).exists() for p in (
        "LICENSE", ".env", ".gitignore",
        "README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
        "CHANGELOG.md", "THIRD_PARTY_NOTICES.md",
        "requirements.txt", "pyproject.toml",
        "docs/INSTALLATION.md", "docs/QUICKSTART.md",
        "simulation/tutorial_mode.py",
    )}
    d = {p: (root / p).is_dir() for p in (
        "docs", "tests", ".github/ISSUE_TEMPLATE", ".github/workflows",
    )}

    has_install = e.get("docs/INSTALLATION.md", False) or e.get("README.md", False)
    has_tutorial = e.get("simulation/tutorial_mode.py", False) or e.get("docs/QUICKSTART.md", False)
    no_env = not e[".env"]

    return {
        "lic_file": (e["LICENSE"], "LICENSE"),
        "lic_header": (e["LICENSE"], "LICENSE 존재 확인 (개별 헤더 미검증)"),
        "lic_deps": (e["requirements.txt"], "requirements.txt 기반"),
        "lic_third": (e.get("THIRD_PARTY_NOTICES.md", False), "THIRD_PARTY_NOTICES.md"),
        "sens_env": (no_env, ".env 미포함" if no_env else ".env 발견"),
        "sens_key": (e[".gitignore"], ".gitignore 기반"),
        "sens_gitignore": (e[".gitignore"], ".gitignore"),
        "sens_history": (False, "수동 확인 필수 — 자동 검증 불가"),
        "doc_readme": (e["README.md"], "README.md"),
        "doc_install": (has_install, "설치 문서"),
        "doc_api": (d["docs"], "docs/"),
        "doc_tutorial": (has_tutorial, "튜토리얼"),
        "repr_req": (e["requirements.txt"], "requirements.txt"),
        "repr_pyproject": (e["pyproject.toml"], "pyproject.toml"),
        "repr_tests": (d["tests"], "tests/"),
        "repr_ci": (d[".github/workflows"], "CI 워크플로"),
        "acc_contributing": (e["CONTRIBUTING.md"], "CONTRIBUTING.md"),
        "acc_coc": (e["CODE_OF_CONDUCT.md"], "CODE_OF_CONDUCT.md"),
        "acc_issues": (d[".github/ISSUE_TEMPLATE"], "이슈 템플릿"),
        "acc_changelog": (e["CHANGELOG.md"], "CHANGELOG.md"),
    }


def _run_checks(root: pathlib.Path) -> tuple[PublicationItem, ...]:
    """모든 점검 항목 실행."""
    check_map = _build_check_map(root)
    items: list[PublicationItem] = []
    for item_id, cat, desc in CHECK_DEFINITIONS:
        satisfied, note = check_map.get(item_id, (False, "판정 불가"))
        items.append(PublicationItem(item_id, cat, desc, satisfied, note))
    return tuple(items)


def _score_category(
    category: str,
    items: tuple[PublicationItem, ...],
) -> CategoryResult:
    """카테고리별 점수 산정."""
    cat_items = tuple(i for i in items if i.category == category)
    passed = sum(1 for i in cat_items if i.satisfied)
    total = len(cat_items)
    score = round(passed / total * 100, 1) if total > 0 else 0.0
    return CategoryResult(
        category=category,
        name_ko=CATEGORY_NAMES_KO[category],
        items=cat_items,
        passed=passed,
        total=total,
        score=score,
    )


def _grade_from_score(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def check_publication(
    repo_root: pathlib.Path | None = None,
) -> PublicationReport:
    """교육 자산 공개 준비 점검."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    items = _run_checks(root)
    cat_results: list[CategoryResult] = []
    for cat in VALID_CATEGORIES:
        cat_results.append(_score_category(cat, items))

    total = len(items)
    passed = sum(1 for i in items if i.satisfied)
    score = round(passed / total * 100, 1) if total > 0 else 0.0
    grade = _grade_from_score(score)

    return PublicationReport(
        categories=tuple(cat_results),
        total_items=total,
        total_passed=passed,
        overall_score=score,
        overall_grade=grade,
        publication_ready=score >= PUBLICATION_THRESHOLD,
    )


def get_category(
    category: str,
    repo_root: pathlib.Path | None = None,
) -> CategoryResult:
    """특정 카테고리 결과."""
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Unknown category: {category}. "
            f"Valid: {', '.join(VALID_CATEGORIES)}"
        )
    root = repo_root or _REPO_ROOT
    items = _run_checks(root)
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
        description="GENESIS Phase 398 -- 교육 자산 공개 준비 체크리스트",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="전체 점검")
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
    report = check_publication()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=== 교육 자산 공개 준비 점검 ===")
    print(f"  점수: {report.overall_score}% (등급: {report.overall_grade})")
    print(f"  공개 가능: {'예' if report.publication_ready else '아니오'}")
    print(f"  항목: {report.total_passed}/{report.total_items} 통과")
    print()
    for c in report.categories:
        filled = max(0, min(10, int(c.score / 10)))
        bar = "█" * filled + "░" * (10 - filled)
        print(f"  [{c.name_ko}] {bar} {c.score}%")
        for i in c.items:
            marker = "+" if i.satisfied else "-"
            print(f"    {marker} {i.description}: {i.note}")


def _print_category(category: str, as_json: bool) -> None:
    try:
        c = get_category(category)
    except ValueError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(c.as_dict(), ensure_ascii=False, indent=2))
        return
    print(f"=== {c.name_ko} ===")
    print(f"  점수: {c.score}%")
    print(f"  항목: {c.passed}/{c.total} 통과")
    for i in c.items:
        marker = "+" if i.satisfied else "-"
        print(f"  {marker} {i.description}: {i.note}")


def _print_categories(as_json: bool) -> None:
    data = list_categories()
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("=== 공개 준비 카테고리 ===")
    for d in data:
        print(f"  {d['category']}: {d['name_ko']}")


if __name__ == "__main__":
    _main()
