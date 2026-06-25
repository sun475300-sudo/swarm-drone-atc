"""GENESIS Phase 319 -- 테스트 절차서 (DO-178C §6).

DO-178C §6 검증 프로세스 기준으로 SDACS 프로젝트의 테스트 절차서
체계를 자동 점검합니다. 5개 검증 단계 × 15개 점검 항목의 증거를
파일시스템에서 확인합니다.

CLI:
    python simulation/test_procedures.py --audit
    python simulation/test_procedures.py --phase TEST_PLANNING
    python simulation/test_procedures.py --phases
    python simulation/test_procedures.py --json
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

VERIF_PHASES: tuple[str, ...] = (
    "TEST_PLANNING",
    "TEST_DESIGN",
    "TEST_EXECUTION",
    "COVERAGE_ANALYSIS",
    "REVIEW_REPORTING",
)

PHASE_NAMES: dict[str, str] = {
    "TEST_PLANNING": "테스트 계획 (DO-178C §6.1)",
    "TEST_DESIGN": "테스트 설계 (§6.2)",
    "TEST_EXECUTION": "테스트 실행 (§6.3)",
    "COVERAGE_ANALYSIS": "커버리지 분석 (§6.4)",
    "REVIEW_REPORTING": "검토 및 보고 (§6.5)",
}

_EXCLUDE_DIRS = frozenset((
    "__pycache__", ".mypy_cache", "node_modules", ".git", ".pytest_cache", ".claude",
))

PROC_CHECKS: tuple[tuple[str, str, str, tuple[tuple[str, ...], ...]], ...] = (
    ("TP-001", "TEST_PLANNING", "테스트 전략 정의",
     (("**/pyproject.toml",), ("**/conftest*",))),
    ("TP-002", "TEST_PLANNING", "테스트 도구 선정",
     (("**/pyproject.toml",),)),
    ("TP-003", "TEST_PLANNING", "테스트 환경 정의",
     (("**/pyproject.toml",), ("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"))),
    ("TP-004", "TEST_DESIGN", "단위 테스트 설계",
     (("**/tests/test_*.py",),)),
    ("TP-005", "TEST_DESIGN", "통합 테스트 설계",
     (("**/tests/test_*.py",), ("**/conftest*",))),
    ("TP-006", "TEST_DESIGN", "시나리오 기반 테스트",
     (("**/config/scenario_params/*.yaml",),)),
    ("TP-007", "TEST_EXECUTION", "자동화 테스트 실행",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"),)),
    ("TP-008", "TEST_EXECUTION", "테스트 결과 기록",
     (("**/results/**/*",),)),
    ("TP-009", "TEST_EXECUTION", "회귀 테스트 체계",
     (("**/tests/test_*.py",), ("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"))),
    ("TP-010", "COVERAGE_ANALYSIS", "코드 커버리지 설정",
     (("**/pyproject.toml",),)),
    ("TP-011", "COVERAGE_ANALYSIS", "커버리지 임계값 정의",
     (("**/pyproject.toml",),)),
    ("TP-012", "COVERAGE_ANALYSIS", "커버리지 리포트 생성",
     (("**/pyproject.toml",), ("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"))),
    ("TP-013", "REVIEW_REPORTING", "테스트 검토 절차",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"),)),
    ("TP-014", "REVIEW_REPORTING", "결함 추적 체계",
     (("**/.github/ISSUE_TEMPLATE/**/*", "**/.github/ISSUE_TEMPLATE.md"),
      ("**/CONTRIBUTING*",))),
    ("TP-015", "REVIEW_REPORTING", "검증 완료 기준",
     (("**/pyproject.toml",), ("**/ROADMAP.md",))),
)


@dataclass(frozen=True)
class ProcFinding:
    """개별 테스트 절차 점검 결과."""

    code: str
    phase: str
    check_name: str
    status: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "phase": self.phase,
            "check_name": self.check_name,
            "status": self.status,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class ProcReport:
    """테스트 절차서 보고서."""

    findings: tuple[ProcFinding, ...]
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


def run_proc_audit(
    repo_root: pathlib.Path | None = None,
) -> ProcReport:
    """테스트 절차서 감사 실행."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    findings: list[ProcFinding] = []
    for code, phase, check_name, patterns in PROC_CHECKS:
        status, evidence = _detect_status(root, patterns)
        findings.append(ProcFinding(code, phase, check_name, status, evidence))

    met = sum(1 for f in findings if f.status == "MET")
    partial = sum(1 for f in findings if f.status == "PARTIAL")
    not_met = sum(1 for f in findings if f.status == "NOT_MET")
    total = len(findings)

    rate = (met + partial * 0.5) / max(total, 1)

    if rate >= 0.8:
        verdict = "검증 절차 충족"
    elif rate >= 0.5:
        verdict = "부분 충족"
    else:
        verdict = "미충족"

    return ProcReport(
        findings=tuple(findings),
        total=total,
        met=met,
        partial=partial,
        not_met=not_met,
        compliance_rate=rate,
        verdict=verdict,
    )


def get_phase_report(
    phase: str, repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """특정 검증 단계 점검 결과."""
    ph = phase.upper()
    if ph not in VERIF_PHASES:
        raise ValueError(f"유효하지 않은 단계: {ph}")

    report = run_proc_audit(repo_root)
    ph_findings = [f for f in report.findings if f.phase == ph]
    met = sum(1 for f in ph_findings if f.status == "MET")
    partial = sum(1 for f in ph_findings if f.status == "PARTIAL")
    total = len(ph_findings)
    not_met = total - met - partial
    rate = (met + partial * 0.5) / max(total, 1)

    return {
        "phase": ph,
        "phase_name": PHASE_NAMES[ph],
        "total": total,
        "met": met,
        "partial": partial,
        "not_met": not_met,
        "compliance_rate": round(rate, 4),
        "findings": [f.as_dict() for f in ph_findings],
    }


def list_phases() -> list[dict[str, Any]]:
    """검증 단계 목록."""
    return [
        {"code": p, "name": PHASE_NAMES[p]}
        for p in VERIF_PHASES
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 319 -- 테스트 절차서 (DO-178C §6)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--audit", action="store_true", help="전체 감사")
    group.add_argument("--phase", type=str, help="단계별 감사")
    group.add_argument("--phases", action="store_true", help="단계 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.audit:
        _print_audit(args.json)
    elif args.phase:
        _print_phase(args.phase, args.json)
    elif args.phases:
        _print_phases(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_audit(as_json: bool) -> None:
    report = run_proc_audit()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=" * 60)
    print("  테스트 절차서 감사 (DO-178C §6)")
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


def _print_phase(phase: str, as_json: bool) -> None:
    try:
        result = get_phase_report(phase)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"단계: {result['phase_name']} ({result['phase']})")
    for f in result["findings"]:
        print(f"  [{f['status']}] {f['code']} {f['check_name']}")


def _print_phases(as_json: bool) -> None:
    phases = list_phases()
    if as_json:
        print(json.dumps(phases, ensure_ascii=False, indent=2))
        return
    for p in phases:
        print(f"  {p['code']}: {p['name']}")


if __name__ == "__main__":
    _main()
