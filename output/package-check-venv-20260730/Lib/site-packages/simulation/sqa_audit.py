"""GENESIS Phase 317 -- SQA 감사 로그 (DO-178C §8).

DO-178C §8 소프트웨어 품질 보증(SQA) 목표 대비 SDACS 프로젝트의
프로세스 준수 상태를 자동 점검합니다.

5개 SQA 목표 × 15개 점검 항목의 증거를 파일시스템에서 확인합니다.

CLI:
    python simulation/sqa_audit.py --audit
    python simulation/sqa_audit.py --objective SQA_PLANNING
    python simulation/sqa_audit.py --objectives
    python simulation/sqa_audit.py --json
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

SQA_OBJECTIVES: tuple[str, ...] = (
    "SQA_PLANNING",
    "PROCESS_COMPLIANCE",
    "TRANSITION_CRITERIA",
    "STANDARDS_CONFORMANCE",
    "PROBLEM_REPORTING",
)

OBJECTIVE_NAMES: dict[str, str] = {
    "SQA_PLANNING": "SQA 계획 (DO-178C §8.1)",
    "PROCESS_COMPLIANCE": "프로세스 준수 (§8.2)",
    "TRANSITION_CRITERIA": "전이 기준 (§8.3)",
    "STANDARDS_CONFORMANCE": "표준 적합성 (§8.4)",
    "PROBLEM_REPORTING": "문제 보고 및 시정 조치 (§8.5)",
}

_EXCLUDE_DIRS = frozenset((
    "__pycache__", ".mypy_cache", "node_modules", ".git", ".pytest_cache", ".claude",
))

SQA_CHECKS: tuple[tuple[str, str, str, tuple[tuple[str, ...], ...]], ...] = (
    ("SQ-001", "SQA_PLANNING", "SQA 계획 문서",
     (("**/CLAUDE.md",), ("**/ROADMAP.md",))),
    ("SQ-002", "SQA_PLANNING", "품질 목표 정의",
     (("**/pyproject.toml",), ("**/docs/**/*.md",))),
    ("SQ-003", "SQA_PLANNING", "검토 일정 및 절차",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"),)),
    ("SQ-004", "PROCESS_COMPLIANCE", "코드 리뷰 프로세스",
     (("**/.github/**/*.yml", "**/.github/**/*.yaml"), ("**/CONTRIBUTING*",))),
    ("SQ-005", "PROCESS_COMPLIANCE", "테스트 프로세스 실행",
     (("**/tests/test_*.py",), ("**/pyproject.toml",))),
    ("SQ-006", "PROCESS_COMPLIANCE", "정적 분석 실행",
     (("**/pyproject.toml",), ("**/.ruff.toml",))),
    ("SQ-007", "TRANSITION_CRITERIA", "요구사항 → 설계 추적",
     (("**/docs/**/*.md",), ("**/simulation/**/*.py",))),
    ("SQ-008", "TRANSITION_CRITERIA", "설계 → 코드 추적",
     (("**/simulation/**/*.py",), ("**/tests/test_*.py",))),
    ("SQ-009", "TRANSITION_CRITERIA", "코드 → 검증 추적",
     (("**/tests/test_*.py",), ("**/conftest*",))),
    ("SQ-010", "STANDARDS_CONFORMANCE", "코딩 표준 도구 설정",
     (("**/pyproject.toml",), ("**/.ruff.toml", "**/setup.cfg", "**/.editorconfig"))),
    ("SQ-011", "STANDARDS_CONFORMANCE", "타입 검사 설정",
     (("**/pyproject.toml", "**/mypy.ini", "**/.mypy.ini"),)),
    ("SQ-012", "STANDARDS_CONFORMANCE", "테스트 커버리지 설정",
     (("**/pyproject.toml", "**/.coveragerc", "**/tox.ini"),)),
    ("SQ-013", "PROBLEM_REPORTING", "이슈 추적 체계",
     (("**/.github/ISSUE_TEMPLATE/**/*", "**/.github/ISSUE_TEMPLATE.md"),
      ("**/CONTRIBUTING*",))),
    ("SQ-014", "PROBLEM_REPORTING", "변경 이력 관리",
     (("**/CHANGELOG*", "**/ACTION_LOG*"),)),
    ("SQ-015", "PROBLEM_REPORTING", "CI/CD 자동 검증",
     (("**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"),)),
)


@dataclass(frozen=True)
class SqaFinding:
    """개별 SQA 점검 결과."""

    code: str
    objective: str
    check_name: str
    status: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "objective": self.objective,
            "check_name": self.check_name,
            "status": self.status,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class SqaReport:
    """SQA 감사 보고서."""

    findings: tuple[SqaFinding, ...]
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


def run_sqa_audit(
    repo_root: pathlib.Path | None = None,
) -> SqaReport:
    """SQA 감사 실행."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    findings: list[SqaFinding] = []
    for code, objective, check_name, patterns in SQA_CHECKS:
        status, evidence = _detect_status(root, patterns)
        findings.append(SqaFinding(code, objective, check_name, status, evidence))

    met = sum(1 for f in findings if f.status == "MET")
    partial = sum(1 for f in findings if f.status == "PARTIAL")
    not_met = sum(1 for f in findings if f.status == "NOT_MET")
    total = len(findings)

    rate = (met + partial * 0.5) / max(total, 1)

    if rate >= 0.8:
        verdict = "SQA 준수"
    elif rate >= 0.5:
        verdict = "부분 준수"
    else:
        verdict = "미준수"

    return SqaReport(
        findings=tuple(findings),
        total=total,
        met=met,
        partial=partial,
        not_met=not_met,
        compliance_rate=rate,
        verdict=verdict,
    )


def get_objective_report(
    objective: str, repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """특정 SQA 목표 점검 결과."""
    obj = objective.upper()
    if obj not in SQA_OBJECTIVES:
        raise ValueError(f"유효하지 않은 목표: {obj}")

    report = run_sqa_audit(repo_root)
    obj_findings = [f for f in report.findings if f.objective == obj]
    met = sum(1 for f in obj_findings if f.status == "MET")
    partial = sum(1 for f in obj_findings if f.status == "PARTIAL")
    total = len(obj_findings)
    not_met = total - met - partial
    rate = (met + partial * 0.5) / max(total, 1)

    return {
        "objective": obj,
        "objective_name": OBJECTIVE_NAMES[obj],
        "total": total,
        "met": met,
        "partial": partial,
        "not_met": not_met,
        "compliance_rate": round(rate, 4),
        "findings": [f.as_dict() for f in obj_findings],
    }


def list_objectives() -> list[dict[str, Any]]:
    """SQA 목표 목록."""
    return [
        {"code": o, "name": OBJECTIVE_NAMES[o]}
        for o in SQA_OBJECTIVES
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 317 -- SQA 감사 로그 (DO-178C §8)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--audit", action="store_true", help="전체 감사")
    group.add_argument("--objective", type=str, help="목표별 감사")
    group.add_argument("--objectives", action="store_true", help="목표 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.audit:
        _print_audit(args.json)
    elif args.objective:
        _print_objective(args.objective, args.json)
    elif args.objectives:
        _print_objectives(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_audit(as_json: bool) -> None:
    report = run_sqa_audit()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=" * 60)
    print("  SQA 감사 로그 (DO-178C §8)")
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


def _print_objective(objective: str, as_json: bool) -> None:
    try:
        result = get_objective_report(objective)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"목표: {result['objective_name']} ({result['objective']})")
    for f in result["findings"]:
        print(f"  [{f['status']}] {f['code']} {f['check_name']}")


def _print_objectives(as_json: bool) -> None:
    objs = list_objectives()
    if as_json:
        print(json.dumps(objs, ensure_ascii=False, indent=2))
        return
    for o in objs:
        print(f"  {o['code']}: {o['name']}")


if __name__ == "__main__":
    _main()
