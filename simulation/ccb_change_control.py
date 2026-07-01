"""GENESIS Phase 318 -- CCB 변경 통제 (DO-178C §7).

DO-178C §7 형상관리(Configuration Management) 기준으로 SDACS 프로젝트의
변경 통제 체계를 자동 점검합니다. CCB(Configuration Control Board) 운영에
필요한 5개 영역 × 15개 점검 항목의 증거를 파일시스템에서 확인합니다.

CLI:
    python simulation/ccb_change_control.py --audit
    python simulation/ccb_change_control.py --area BASELINE
    python simulation/ccb_change_control.py --areas
    python simulation/ccb_change_control.py --json
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

CCB_AREAS: tuple[str, ...] = (
    "BASELINE",
    "CHANGE_REQUEST",
    "VERSION_CONTROL",
    "BUILD_RELEASE",
    "AUDIT_TRACE",
)

AREA_NAMES: dict[str, str] = {
    "BASELINE": "기선 관리 (DO-178C §7.2)",
    "CHANGE_REQUEST": "변경 요청 관리 (§7.3)",
    "VERSION_CONTROL": "버전 관리 (§7.4)",
    "BUILD_RELEASE": "빌드/릴리스 관리 (§7.5)",
    "AUDIT_TRACE": "감사 추적 (§7.6)",
}

_EXCLUDE_DIRS = frozenset((
    "__pycache__", ".mypy_cache", "node_modules", ".git", ".pytest_cache", ".claude",
))

CCB_CHECKS: tuple[tuple[str, str, str, tuple[tuple[str, ...], ...]], ...] = (
    ("CC-001", "BASELINE", "소프트웨어 기선 정의",
     (("**/.gitignore",), ("**/pyproject.toml",))),
    ("CC-002", "BASELINE", "기선 식별자 (태그/릴리스)",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"),)),
    ("CC-003", "BASELINE", "기선 문서 목록",
     (("**/ROADMAP.md",), ("**/CLAUDE.md",))),
    ("CC-004", "CHANGE_REQUEST", "변경 요청 템플릿",
     (("**/.github/ISSUE_TEMPLATE/**/*",),)),
    ("CC-005", "CHANGE_REQUEST", "PR 기반 변경 승인",
     (("**/.github/**/*.yml", "**/.github/**/*.yaml"),)),
    ("CC-006", "CHANGE_REQUEST", "변경 영향 분석 절차",
     (("**/docs/**/*.md",), ("**/ROADMAP.md",))),
    ("CC-007", "VERSION_CONTROL", "Git 버전 관리 체계",
     (("**/.gitignore",),)),
    ("CC-008", "VERSION_CONTROL", "브랜치 전략 문서",
     (("**/CONTRIBUTING*",), ("**/CLAUDE.md",))),
    ("CC-009", "VERSION_CONTROL", "커밋 메시지 규칙",
     (("**/CLAUDE.md",),)),
    ("CC-010", "BUILD_RELEASE", "CI/CD 빌드 파이프라인",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"),)),
    ("CC-011", "BUILD_RELEASE", "빌드 환경 사양",
     (("**/pyproject.toml",), ("**/requirements*.txt",))),
    ("CC-012", "BUILD_RELEASE", "릴리스 체크리스트",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"), ("**/ROADMAP.md",))),
    ("CC-013", "AUDIT_TRACE", "변경 이력 로그",
     (("**/CHANGELOG*", "**/ACTION_LOG*"),)),
    ("CC-014", "AUDIT_TRACE", "감사 추적 코드",
     (("**/simulation/audit_trail.py",),)),
    ("CC-015", "AUDIT_TRACE", "문제 보고 추적",
     (("**/.github/ISSUE_TEMPLATE/**/*",), ("**/.github/**/*.yml", "**/.github/**/*.yaml"))),
)


@dataclass(frozen=True)
class CcbFinding:
    """개별 CCB 점검 결과."""

    code: str
    area: str
    check_name: str
    status: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "area": self.area,
            "check_name": self.check_name,
            "status": self.status,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class CcbReport:
    """CCB 변경 통제 보고서."""

    findings: tuple[CcbFinding, ...]
    total: int
    met: int
    partial: int
    not_met: int
    compliance_rate: float
    verdict: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "findings": [f.as_dict() for f in self.findings],
            "total": self.total,
            "met": self.met,
            "partial": self.partial,
            "not_met": self.not_met,
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
    if not pattern_groups:
        return "NOT_MET", ()
    all_evidence: list[str] = []
    matched_groups = 0
    for group in pattern_groups:
        files = _glob_any(root, group)
        if files:
            matched_groups += 1
            all_evidence.extend(f for f in files if f not in all_evidence)

    evidence = tuple(sorted(all_evidence))
    if matched_groups == len(pattern_groups):
        return "MET", evidence
    if matched_groups > 0:
        return "PARTIAL", evidence
    return "NOT_MET", evidence


def run_ccb_audit(
    repo_root: pathlib.Path | None = None,
) -> CcbReport:
    """CCB 변경 통제 감사 실행."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    findings: list[CcbFinding] = []
    for code, area, check_name, patterns in CCB_CHECKS:
        status, evidence = _detect_status(root, patterns)
        findings.append(CcbFinding(code, area, check_name, status, evidence))

    met = sum(1 for f in findings if f.status == "MET")
    partial = sum(1 for f in findings if f.status == "PARTIAL")
    not_met = sum(1 for f in findings if f.status == "NOT_MET")
    total = len(findings)

    rate = (met + partial * 0.5) / max(total, 1)

    if rate >= 0.8:
        verdict = "변경 통제 충족"
    elif rate >= 0.5:
        verdict = "부분 충족"
    else:
        verdict = "미충족"

    return CcbReport(
        findings=tuple(findings),
        total=total,
        met=met,
        partial=partial,
        not_met=not_met,
        compliance_rate=rate,
        verdict=verdict,
    )


def get_area_report(
    area: str, repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """특정 CCB 영역 점검 결과."""
    a = area.upper()
    if a not in CCB_AREAS:
        raise ValueError(f"유효하지 않은 영역: {a}")

    report = run_ccb_audit(repo_root)
    area_findings = [f for f in report.findings if f.area == a]
    met = sum(1 for f in area_findings if f.status == "MET")
    partial = sum(1 for f in area_findings if f.status == "PARTIAL")
    total = len(area_findings)
    not_met = total - met - partial
    rate = (met + partial * 0.5) / max(total, 1)

    return {
        "area": a,
        "area_name": AREA_NAMES[a],
        "total": total,
        "met": met,
        "partial": partial,
        "not_met": not_met,
        "compliance_rate": round(rate, 4),
        "findings": [f.as_dict() for f in area_findings],
    }


def list_areas() -> list[dict[str, Any]]:
    """CCB 영역 목록."""
    return [
        {"code": a, "name": AREA_NAMES[a]}
        for a in CCB_AREAS
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 318 -- CCB 변경 통제 (DO-178C §7)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--audit", action="store_true", help="전체 감사")
    group.add_argument("--area", type=str, help="영역별 감사")
    group.add_argument("--areas", action="store_true", help="영역 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.audit:
        _print_audit(args.json)
    elif args.area:
        _print_area(args.area, args.json)
    elif args.areas:
        _print_areas(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_audit(as_json: bool) -> None:
    report = run_ccb_audit()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=" * 60)
    print("  CCB 변경 통제 감사 (DO-178C §7)")
    print("=" * 60)
    for f in report.findings:
        mark = {"MET": "✓", "PARTIAL": "△", "NOT_MET": "✗"}[f.status]
        print(f"  [{mark}] {f.code} {f.check_name}")
        if f.evidence:
            print(f"      증거: {', '.join(f.evidence[:3])}")
    print("-" * 60)
    print(f"  충족: {report.met} | 부분: {report.partial} | 미충족: {report.not_met}")
    print(f"  준수율: {report.compliance_rate:.1%} | 판정: {report.verdict}")
    print("=" * 60)


def _print_area(area: str, as_json: bool) -> None:
    try:
        result = get_area_report(area)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"영역: {result['area_name']} ({result['area']})")
    for f in result["findings"]:
        print(f"  [{f['status']}] {f['code']} {f['check_name']}")


def _print_areas(as_json: bool) -> None:
    areas = list_areas()
    if as_json:
        print(json.dumps(areas, ensure_ascii=False, indent=2))
        return
    for a in areas:
        print(f"  {a['code']}: {a['name']}")


if __name__ == "__main__":
    _main()
