"""GENESIS Phase 314 -- 감항 인증 준비 체크리스트.

DO-178C DAL-D 수준에서 SDACS 소프트웨어의 감항 인증 준비 상태를
자동 점검합니다. Phase 305 DO-178C 갭 분석 문서를 기반으로
6개 프로세스 영역 × 20개 항목의 산출물 존재를 파일시스템에서 확인합니다.

CLI:
    python simulation/airworthiness_checklist.py --check
    python simulation/airworthiness_checklist.py --category PLANNING
    python simulation/airworthiness_checklist.py --categories
    python simulation/airworthiness_checklist.py --json
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

PROCESS_CATEGORIES: tuple[str, ...] = (
    "PLANNING",
    "REQUIREMENTS",
    "DESIGN",
    "CODING",
    "VERIFICATION",
    "CM",
)

CATEGORY_NAMES: dict[str, str] = {
    "PLANNING": "소프트웨어 계획 (DO-178C §4)",
    "REQUIREMENTS": "소프트웨어 요구사항 (§5.1-5.2)",
    "DESIGN": "소프트웨어 설계 (§5.3)",
    "CODING": "소프트웨어 코딩 (§5.4)",
    "VERIFICATION": "소프트웨어 검증 (§6)",
    "CM": "형상관리 (§7)",
}

_EXCLUDE_DIRS = frozenset((
    "__pycache__", ".mypy_cache", "node_modules", ".git", ".pytest_cache", ".claude",
))

AIRWORTHINESS_ITEMS: tuple[tuple[str, str, str, str, tuple[tuple[str, ...], ...]], ...] = (
    ("AW-001", "PLANNING", "소프트웨어 개발 계획 (SDP)", "DAL-D",
     (("**/CLAUDE.md",), ("**/ROADMAP.md",))),
    ("AW-002", "PLANNING", "소프트웨어 검증 계획 (SVP)", "DAL-D",
     (("**/pyproject.toml",), ("**/conftest*",))),
    ("AW-003", "PLANNING", "소프트웨어 형상관리 계획 (SCMP)", "DAL-D",
     (("**/.gitignore",), ("**/.github/**/*",))),
    ("AW-004", "REQUIREMENTS", "고수준 요구사항 (HLR) 문서화", "DAL-D",
     (("**/docs/**/*.md",),)),
    ("AW-005", "REQUIREMENTS", "안전 요구사항 식별", "DAL-D",
     (("**/safety*",), ("**/risk*",))),
    ("AW-006", "REQUIREMENTS", "파생 요구사항 추적", "DAL-D",
     (("**/ROADMAP*",), ("**/STATUS*",))),
    ("AW-007", "DESIGN", "아키텍처 설계 문서", "DAL-D",
     (("**/docs/**/architecture*", "**/docs/**/design*"),)),
    ("AW-008", "DESIGN", "인터페이스 정의", "DAL-D",
     (("**/api/**",), ("**/docs/**/api*",))),
    ("AW-009", "DESIGN", "데이터 흐름 설계", "DAL-D",
     (("**/docs/**/flow*", "**/docs/**/data*"),)),
    ("AW-010", "CODING", "코딩 표준 정의 및 준수", "DAL-D",
     (("**/pyproject.toml",), ("**/.ruff.toml", "**/setup.cfg", "**/.editorconfig"))),
    ("AW-011", "CODING", "소스-요구사항 추적성", "DAL-D",
     (("**/simulation/**/*.py",), ("**/tests/**/*.py",))),
    ("AW-012", "CODING", "정적 분석 도구 적용", "DAL-D",
     (("**/pyproject.toml",), ("**/.github/**/*.yml", "**/.github/**/*.yaml"))),
    ("AW-013", "VERIFICATION", "요구사항 기반 테스트", "DAL-D",
     (("**/tests/test_*.py",),)),
    ("AW-014", "VERIFICATION", "구조적 커버리지 분석", "DAL-D",
     (("**/pyproject.toml",), ("**/.github/**/ci*",))),
    ("AW-015", "VERIFICATION", "테스트 결과 기록", "DAL-D",
     (("**/results/**/*",), ("**/.github/**/*",))),
    ("AW-016", "VERIFICATION", "DO-178C 갭 분석", "DAL-D",
     (("**/DO178*",),)),
    ("AW-017", "CM", "기선(Baseline) 관리", "DAL-D",
     (("**/.gitignore",),)),
    ("AW-018", "CM", "변경 이력 추적", "DAL-D",
     (("**/CHANGELOG*", "**/ACTION_LOG*"),)),
    ("AW-019", "CM", "문제 보고 체계", "DAL-D",
     (("**/.github/ISSUE_TEMPLATE/**/*",),)),
    ("AW-020", "CM", "릴리스 관리 절차", "DAL-D",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"),)),
)


@dataclass(frozen=True)
class AirworthinessResult:
    """개별 감항 항목 점검 결과."""

    code: str
    category: str
    requirement: str
    dal_level: str
    status: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "requirement": self.requirement,
            "dal_level": self.dal_level,
            "status": self.status,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class AirworthinessReport:
    """감항 인증 준비 보고서."""

    results: tuple[AirworthinessResult, ...]
    total: int
    compliant: int
    partial: int
    non_compliant: int
    compliance_rate: float
    verdict: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "results": [r.as_dict() for r in self.results],
            "total": self.total,
            "compliant": self.compliant,
            "partial": self.partial,
            "non_compliant": self.non_compliant,
            "compliance_rate": round(self.compliance_rate, 4),
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
    all_evidence: list[str] = []
    matched_groups = 0
    for group in pattern_groups:
        files = _glob_any(root, group)
        if files:
            matched_groups += 1
            all_evidence.extend(f for f in files if f not in all_evidence)

    evidence = tuple(sorted(all_evidence))
    if matched_groups == len(pattern_groups):
        return "COMPLIANT", evidence
    if matched_groups > 0:
        return "PARTIAL", evidence
    return "NON_COMPLIANT", evidence


def check_airworthiness(
    repo_root: pathlib.Path | None = None,
) -> AirworthinessReport:
    """감항 인증 준비 상태 점검."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    results: list[AirworthinessResult] = []
    for code, category, requirement, dal, patterns in AIRWORTHINESS_ITEMS:
        status, evidence = _detect_status(root, patterns)
        results.append(AirworthinessResult(
            code, category, requirement, dal, status, evidence,
        ))

    compliant = sum(1 for r in results if r.status == "COMPLIANT")
    partial = sum(1 for r in results if r.status == "PARTIAL")
    non_compliant = sum(1 for r in results if r.status == "NON_COMPLIANT")
    total = len(results)

    rate = (compliant + partial * 0.5) / max(total, 1)

    if rate >= 0.8:
        verdict = "인증 준비 완료"
    elif rate >= 0.5:
        verdict = "부분 준비"
    else:
        verdict = "준비 미흡"

    return AirworthinessReport(
        results=tuple(results),
        total=total,
        compliant=compliant,
        partial=partial,
        non_compliant=non_compliant,
        compliance_rate=rate,
        verdict=verdict,
    )


def get_process_report(
    category: str, repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """특정 프로세스 영역 점검 결과."""
    cat = category.upper()
    if cat not in PROCESS_CATEGORIES:
        raise ValueError(f"유효하지 않은 프로세스: {cat}")

    report = check_airworthiness(repo_root)
    cat_results = [r for r in report.results if r.category == cat]
    compliant = sum(1 for r in cat_results if r.status == "COMPLIANT")
    partial = sum(1 for r in cat_results if r.status == "PARTIAL")
    total = len(cat_results)
    non_compliant = total - compliant - partial
    rate = (compliant + partial * 0.5) / max(total, 1)

    return {
        "category": cat,
        "category_name": CATEGORY_NAMES[cat],
        "total": total,
        "compliant": compliant,
        "partial": partial,
        "non_compliant": non_compliant,
        "compliance_rate": round(rate, 4),
        "results": [r.as_dict() for r in cat_results],
    }


def list_processes() -> list[dict[str, Any]]:
    """프로세스 영역 목록."""
    return [
        {"code": c, "name": CATEGORY_NAMES[c]}
        for c in PROCESS_CATEGORIES
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 314 -- 감항 인증 준비 체크리스트",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="전체 점검")
    group.add_argument("--category", type=str, help="프로세스별 점검")
    group.add_argument("--categories", action="store_true", help="프로세스 목록")
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
    report = check_airworthiness()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=" * 60)
    print("  감항 인증 준비 체크리스트 (DO-178C DAL-D)")
    print("=" * 60)
    for r in report.results:
        mark = {"COMPLIANT": "✓", "PARTIAL": "△", "NON_COMPLIANT": "✗"}[r.status]
        print(f"  [{mark}] {r.code} [{r.dal_level}] {r.requirement}")
        if r.evidence:
            print(f"      증거: {', '.join(r.evidence[:3])}")
    print("-" * 60)
    print(f"  적합: {report.compliant} | 부분: {report.partial} | 미적합: {report.non_compliant}")
    print(f"  적합률: {report.compliance_rate:.1%} | 판정: {report.verdict}")
    print("=" * 60)


def _print_category(category: str, as_json: bool) -> None:
    try:
        result = get_process_report(category)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"프로세스: {result['category_name']} ({result['category']})")
    for r in result["results"]:
        print(f"  [{r['status']}] {r['code']} {r['requirement']}")


def _print_categories(as_json: bool) -> None:
    procs = list_processes()
    if as_json:
        print(json.dumps(procs, ensure_ascii=False, indent=2))
        return
    for p in procs:
        print(f"  {p['code']}: {p['name']}")


if __name__ == "__main__":
    _main()
