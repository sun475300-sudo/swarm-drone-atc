"""GENESIS Phase 315 -- DO-178C 도구 자격 평가 (TQL-5).

DO-178C §12.2 기준 SDACS 개발 도구의 자격 수준(Tool Qualification Level)을
자동 평가합니다. TQL-5(가장 낮은 자격 수준)를 기준으로 도구 존재·설정·
실행 증거를 파일시스템에서 확인합니다.

4개 도구 카테고리 × 12개 도구의 설치/설정 증거를 스캔합니다.

CLI:
    python simulation/tool_qualification.py --assess
    python simulation/tool_qualification.py --category VERIFICATION
    python simulation/tool_qualification.py --categories
    python simulation/tool_qualification.py --json
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

TOOL_CATEGORIES: tuple[str, ...] = (
    "VERIFICATION",
    "CODING_STANDARD",
    "STATIC_ANALYSIS",
    "BUILD_CI",
)

CATEGORY_NAMES: dict[str, str] = {
    "VERIFICATION": "검증 도구 (DO-178C §6)",
    "CODING_STANDARD": "코딩 표준 도구 (§5.4)",
    "STATIC_ANALYSIS": "정적 분석 도구 (§6.3)",
    "BUILD_CI": "빌드/CI 도구 (§7)",
}

_EXCLUDE_DIRS = frozenset((
    "__pycache__", ".mypy_cache", "node_modules", ".git", ".pytest_cache", ".claude",
))

TOOLS: tuple[tuple[str, str, str, str, tuple[tuple[str, ...], ...]], ...] = (
    ("TQ-001", "VERIFICATION", "pytest", "TQL-5",
     (("**/pyproject.toml",), ("**/tests/test_*.py",))),
    ("TQ-002", "VERIFICATION", "pytest-cov (커버리지)", "TQL-5",
     (("**/pyproject.toml",),)),
    ("TQ-003", "VERIFICATION", "hypothesis (속성 기반 테스트)", "TQL-5",
     (("**/pyproject.toml",), ("**/tests/**/*hypothesis*", "**/tests/**/*property*"))),
    ("TQ-004", "CODING_STANDARD", "ruff format (코드 포매터)", "TQL-5",
     (("**/pyproject.toml",), ("**/.ruff.toml",))),
    ("TQ-005", "CODING_STANDARD", "isort (임포트 정렬, ruff 통합)", "TQL-5",
     (("**/pyproject.toml",),)),
    ("TQ-006", "CODING_STANDARD", "ruff (린터)", "TQL-5",
     (("**/pyproject.toml",),)),
    ("TQ-007", "STATIC_ANALYSIS", "mypy (타입 검사)", "TQL-5",
     (("**/pyproject.toml",), ("**/.github/**/ci*",))),
    ("TQ-008", "STATIC_ANALYSIS", "ruff (정적 분석, pylint 대체)", "TQL-5",
     (("**/pyproject.toml",), ("**/.ruff.toml",))),
    ("TQ-009", "STATIC_ANALYSIS", "보안 정적 분석", "TQL-5",
     (("**/pyproject.toml",), ("**/.github/**/*.yml", "**/.github/**/*.yaml"))),
    ("TQ-010", "BUILD_CI", "GitHub Actions CI", "TQL-5",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"),)),
    ("TQ-011", "BUILD_CI", "pip/setuptools (패키지 관리)", "TQL-5",
     (("**/pyproject.toml",), ("**/requirements*.txt",))),
    ("TQ-012", "BUILD_CI", "pre-commit (커밋 전 검사)", "TQL-5",
     (("**/.pre-commit-config.yaml",),)),
)


@dataclass(frozen=True)
class ToolQualResult:
    """개별 도구 자격 평가 결과."""

    code: str
    category: str
    tool_name: str
    tql_level: str
    status: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "tool_name": self.tool_name,
            "tql_level": self.tql_level,
            "status": self.status,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class ToolQualReport:
    """도구 자격 평가 보고서."""

    results: tuple[ToolQualResult, ...]
    total: int
    qualified: int
    partial: int
    not_qualified: int
    qualification_rate: float
    verdict: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "results": [r.as_dict() for r in self.results],
            "total": self.total,
            "qualified": self.qualified,
            "partial": self.partial,
            "not_qualified": self.not_qualified,
            "qualification_rate": round(self.qualification_rate, 4),
            "verdict": self.verdict,
        }


def _glob_any(root: pathlib.Path, patterns: tuple[str, ...]) -> tuple[str, ...]:
    """패턴 매치 파일 반환 (비소스 디렉토리 제외)."""
    found: list[str] = []
    for pat in patterns:
        if ".." in pathlib.PurePosixPath(pat).parts:
            raise ValueError(f"Pattern escapes root: {pat!r}")
        for p in root.glob(pat):
            if not p.is_file():
                continue
            parts = p.relative_to(root).parts
            if _EXCLUDE_DIRS.intersection(parts):
                continue
            rel = p.relative_to(root).as_posix()
            if rel not in found:
                found.append(rel)
    return tuple(sorted(found))


def _detect_status(
    root: pathlib.Path, pattern_groups: tuple[tuple[str, ...], ...],
) -> tuple[str, tuple[str, ...]]:
    """패턴 그룹 매치 결과로 상태 결정."""
    if not pattern_groups:
        return "NOT_QUALIFIED", ()
    all_evidence: list[str] = []
    matched_groups = 0
    for group in pattern_groups:
        files = _glob_any(root, group)
        if files:
            matched_groups += 1
            all_evidence.extend(f for f in files if f not in all_evidence)

    evidence = tuple(sorted(all_evidence))
    if matched_groups == len(pattern_groups):
        return "QUALIFIED", evidence
    if matched_groups > 0:
        return "PARTIAL", evidence
    return "NOT_QUALIFIED", evidence


def assess_tools(
    repo_root: pathlib.Path | None = None,
) -> ToolQualReport:
    """도구 자격 평가 실행."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    results: list[ToolQualResult] = []
    for code, category, tool_name, tql, patterns in TOOLS:
        status, evidence = _detect_status(root, patterns)
        results.append(ToolQualResult(
            code, category, tool_name, tql, status, evidence,
        ))

    qualified = sum(1 for r in results if r.status == "QUALIFIED")
    partial = sum(1 for r in results if r.status == "PARTIAL")
    not_qualified = sum(1 for r in results if r.status == "NOT_QUALIFIED")
    total = len(results)

    rate = (qualified + partial * 0.5) / max(total, 1)

    if rate >= 0.8:
        verdict = "도구 자격 충족"
    elif rate >= 0.5:
        verdict = "부분 충족"
    else:
        verdict = "미충족"

    return ToolQualReport(
        results=tuple(results),
        total=total,
        qualified=qualified,
        partial=partial,
        not_qualified=not_qualified,
        qualification_rate=rate,
        verdict=verdict,
    )


def get_category_report(
    category: str, repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """특정 카테고리 도구 자격 평가 결과."""
    cat = category.upper()
    if cat not in TOOL_CATEGORIES:
        raise ValueError(f"유효하지 않은 카테고리: {cat}")

    report = assess_tools(repo_root)
    cat_results = [r for r in report.results if r.category == cat]
    qualified = sum(1 for r in cat_results if r.status == "QUALIFIED")
    partial = sum(1 for r in cat_results if r.status == "PARTIAL")
    total = len(cat_results)
    not_qualified = total - qualified - partial
    rate = (qualified + partial * 0.5) / max(total, 1)

    return {
        "category": cat,
        "category_name": CATEGORY_NAMES[cat],
        "total": total,
        "qualified": qualified,
        "partial": partial,
        "not_qualified": not_qualified,
        "qualification_rate": round(rate, 4),
        "results": [r.as_dict() for r in cat_results],
    }


def list_categories() -> list[dict[str, Any]]:
    """도구 카테고리 목록."""
    return [
        {"code": c, "name": CATEGORY_NAMES[c]}
        for c in TOOL_CATEGORIES
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 315 -- DO-178C 도구 자격 평가 (TQL-5)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--assess", action="store_true", help="전체 평가")
    group.add_argument("--category", type=str, help="카테고리별 평가")
    group.add_argument("--categories", action="store_true", help="카테고리 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.assess:
        _print_assess(args.json)
    elif args.category:
        _print_category(args.category, args.json)
    elif args.categories:
        _print_categories(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_assess(as_json: bool) -> None:
    report = assess_tools()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=" * 60)
    print("  DO-178C 도구 자격 평가 (TQL-5)")
    print("=" * 60)
    for r in report.results:
        mark = {"QUALIFIED": "✓", "PARTIAL": "△", "NOT_QUALIFIED": "✗"}[r.status]
        print(f"  [{mark}] {r.code} [{r.tql_level}] {r.tool_name}")
        if r.evidence:
            print(f"      증거: {', '.join(r.evidence[:3])}")
    print("-" * 60)
    print(f"  적합: {report.qualified} | 부분: {report.partial} | 미적합: {report.not_qualified}")
    print(f"  적합률: {report.qualification_rate:.1%} | 판정: {report.verdict}")
    print("=" * 60)


def _print_category(category: str, as_json: bool) -> None:
    try:
        result = get_category_report(category)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"카테고리: {result['category_name']} ({result['category']})")
    for r in result["results"]:
        print(f"  [{r['status']}] {r['code']} {r['tool_name']}")


def _print_categories(as_json: bool) -> None:
    cats = list_categories()
    if as_json:
        print(json.dumps(cats, ensure_ascii=False, indent=2))
        return
    for c in cats:
        print(f"  {c['code']}: {c['name']}")


if __name__ == "__main__":
    _main()
