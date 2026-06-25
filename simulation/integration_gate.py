"""GENESIS Phase 399 -- 최종 통합 게이트.

Phase 393-398의 6개 하위 시스템을 통합 점검하여
Phase 400 Legacy 선언 진입 가능 여부를 판정합니다.

하위 시스템:
- Phase 393 maturity_assessment → 프로젝트 성숙도
- Phase 394 handover_checklist → 인수인계 준비도
- Phase 395 education_asset_registry → 교육 자산 커버리지
- Phase 396 genesis_report → GENESIS 트랙 종합
- Phase 397 ecosystem_sustainability → 생태계 자생력
- Phase 398 asset_publication_checklist → 공개 준비도

CLI:
    python simulation/integration_gate.py --gate
    python simulation/integration_gate.py --summary
    python simulation/integration_gate.py --json
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

from simulation.asset_publication_checklist import check_publication  # noqa: E402
from simulation.ecosystem_sustainability import assess_sustainability  # noqa: E402
from simulation.education_asset_registry import verify_assets  # noqa: E402
from simulation.genesis_report import generate_report  # noqa: E402
from simulation.handover_checklist import check_handover  # noqa: E402
from simulation.maturity_assessment import assess  # noqa: E402

GATE_THRESHOLD: float = 60.0


@dataclass(frozen=True)
class SubsystemGate:
    """하위 시스템 게이트 결과."""

    name: str
    module: str
    score: float
    grade: str
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "module": self.module,
            "score": self.score,
            "grade": self.grade,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class IntegrationGateReport:
    """통합 게이트 보고서."""

    subsystems: tuple[SubsystemGate, ...]
    total_subsystems: int
    all_passed: int
    overall_score: float
    overall_grade: str
    gate_passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_subsystems": self.total_subsystems,
            "all_passed": self.all_passed,
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "gate_passed": self.gate_passed,
            "subsystems": [s.as_dict() for s in self.subsystems],
        }


SUBSYSTEM_DEFS: tuple[tuple[str, str], ...] = (
    ("maturity", "maturity_assessment"),
    ("handover", "handover_checklist"),
    ("education_assets", "education_asset_registry"),
    ("genesis_report", "genesis_report"),
    ("sustainability", "ecosystem_sustainability"),
    ("publication", "asset_publication_checklist"),
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


def _collect_subsystem(
    name: str,
    module: str,
    root: pathlib.Path,
) -> SubsystemGate:
    """하위 시스템별 점수 수집."""
    try:
        if name == "maturity":
            result = assess(root)
            score = result.overall_score
        elif name == "handover":
            result = check_handover(root)
            score = result.overall_pct
        elif name == "education_assets":
            result = verify_assets(root)
            score = result.coverage_pct
        elif name == "genesis_report":
            result = generate_report(root)
            score = result.completion_pct
        elif name == "sustainability":
            result = assess_sustainability(root)
            score = result.overall_score
        elif name == "publication":
            result = check_publication(root)
            score = result.overall_score
        else:
            raise ValueError(f"Unknown subsystem: {name}")
    except Exception as exc:
        raise RuntimeError(f"{name} failed: {exc}") from exc

    grade = _grade_from_score(score)
    return SubsystemGate(
        name=name,
        module=module,
        score=round(score, 1),
        grade=grade,
        passed=score >= GATE_THRESHOLD,
    )


def run_gate(
    repo_root: pathlib.Path | None = None,
) -> IntegrationGateReport:
    """통합 게이트 실행."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    gates: list[SubsystemGate] = []
    for name, module in SUBSYSTEM_DEFS:
        gates.append(_collect_subsystem(name, module, root))

    total = len(gates)
    passed = sum(1 for g in gates if g.passed)
    avg_score = round(sum(g.score for g in gates) / total, 1) if total > 0 else 0.0
    grade = _grade_from_score(avg_score)

    return IntegrationGateReport(
        subsystems=tuple(gates),
        total_subsystems=total,
        all_passed=passed,
        overall_score=avg_score,
        overall_grade=grade,
        gate_passed=passed == total and avg_score >= GATE_THRESHOLD,
    )


def get_summary(
    repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """간단 요약."""
    report = run_gate(repo_root)
    return {
        "gate_passed": report.gate_passed,
        "overall_score": report.overall_score,
        "overall_grade": report.overall_grade,
        "subsystem_grades": {
            s.name: s.grade for s in report.subsystems
        },
    }


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 399 -- 최종 통합 게이트",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gate", action="store_true", help="통합 게이트 실행")
    group.add_argument("--summary", action="store_true", help="간단 요약")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.gate:
        _print_gate(args.json)
    elif args.summary:
        _print_summary(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_gate(as_json: bool) -> None:
    report = run_gate()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=== GENESIS 최종 통합 게이트 ===")
    print(f"  종합 점수: {report.overall_score}% (등급: {report.overall_grade})")
    gate_str = "통과" if report.gate_passed else "미통과"
    print(f"  게이트: {gate_str} ({report.all_passed}/{report.total_subsystems} 하위시스템 통과)")
    print()
    for s in report.subsystems:
        filled = max(0, min(10, int(s.score / 10)))
        bar = "█" * filled + "░" * (10 - filled)
        marker = "+" if s.passed else "-"
        print(f"  {marker} {s.name:<20} {bar} {s.score}% ({s.grade})")


def _print_summary(as_json: bool) -> None:
    summary = get_summary()
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print("=== 통합 게이트 요약 ===")
    gate_str = "통과" if summary["gate_passed"] else "미통과"
    print(f"  게이트: {gate_str}")
    print(f"  점수: {summary['overall_score']}% ({summary['overall_grade']})")
    for name, grade in summary["subsystem_grades"].items():
        print(f"    {name}: {grade}")


if __name__ == "__main__":
    _main()
