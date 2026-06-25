"""GENESIS Phase 400 -- SDACS Legacy 선언.

GENESIS 트랙(Phase 301-400)의 정점.
Phase 399 통합 게이트 결과를 기반으로 SDACS 프로젝트의
Legacy 선언문을 생성합니다.

CLI:
    python simulation/legacy_declaration.py --declare
    python simulation/legacy_declaration.py --certificate
    python simulation/legacy_declaration.py --json
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

from simulation.integration_gate import run_gate  # noqa: E402

DECLARATION_DATE = "2026-06-25"
PROJECT_NAME = "SDACS"
PROJECT_VERSION = "1.0.0"
PROJECT_FULL_NAME = "Swarm Drone Airspace Control System"


@dataclass(frozen=True)
class SubsystemSummary:
    """하위 시스템 요약."""

    name: str
    score: float
    grade: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "grade": self.grade,
            "status": self.status,
        }


@dataclass(frozen=True)
class LegacyDeclaration:
    """Legacy 선언문."""

    project_name: str
    project_full_name: str
    version: str
    declaration_date: str
    subsystem_health_avg: float
    overall_grade: str
    gate_passed: bool
    subsystem_summary: tuple[SubsystemSummary, ...]
    declaration_text: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_full_name": self.project_full_name,
            "version": self.version,
            "declaration_date": self.declaration_date,
            "subsystem_health_avg": self.subsystem_health_avg,
            "overall_grade": self.overall_grade,
            "gate_passed": self.gate_passed,
            "subsystem_summary": [s.as_dict() for s in self.subsystem_summary],
            "declaration_text": self.declaration_text,
        }


DECLARATION_TEMPLATE = """\
========================================
  SDACS Legacy Declaration / 레거시 선언
========================================

프로젝트: {project_full_name} ({project_name})
버전:     {version}
선언일:   {declaration_date}
종합 등급: {overall_grade}
게이트:   {gate_status}

--- 하위 시스템 ---
{subsystem_lines}

--- 선언 ---
{body}

========================================
"""

DECLARATION_BODY_PASSED = """\
본 프로젝트는 GENESIS 트랙(Phase 301-400)의 교육·인수인계·인증·
생태계 평가를 완료하고, 최종 통합 게이트를 통과하였습니다.

이로써 SDACS는 다음을 달성하였음을 선언합니다:
  1. 프로젝트 성숙도 자가 평가 완료 (Phase 393)
  2. 인수인계 체크리스트 정립 (Phase 394)
  3. 교육 자산 16종 체계적 등록 (Phase 395)
  4. GENESIS 종합 보고서 생성 (Phase 396)
  5. 생태계 자생력 평가 완료 (Phase 397)
  6. 교육 자산 공개 준비 점검 (Phase 398)
  7. 최종 통합 게이트 점검 (Phase 399)

SDACS는 원저자 부재 시에도 독립적으로 유지·발전 가능한
생태계 기반을 갖추었으며, 이를 Legacy로 선언합니다."""

DECLARATION_BODY_CONDITIONAL = """\
본 프로젝트는 GENESIS 트랙(Phase 301-400)의 평가를 완료하였으나,
일부 하위 시스템이 게이트 기준을 충족하지 못하였습니다.

조건부 Legacy 선언:
SDACS는 핵심 기반을 갖추었으나, 아래 항목의 개선이 권장됩니다.
완전한 Legacy 지위는 모든 하위 시스템이 게이트를 통과한 후 부여됩니다."""


def generate_declaration(
    repo_root: pathlib.Path | None = None,
) -> LegacyDeclaration:
    """Legacy 선언문 생성."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    gate_report = run_gate(root)

    summaries: list[SubsystemSummary] = []
    for s in gate_report.subsystems:
        status = "통과" if s.passed else "미통과"
        summaries.append(SubsystemSummary(s.name, s.score, s.grade, status))

    body = DECLARATION_BODY_PASSED if gate_report.gate_passed else DECLARATION_BODY_CONDITIONAL

    return LegacyDeclaration(
        project_name=PROJECT_NAME,
        project_full_name=PROJECT_FULL_NAME,
        version=PROJECT_VERSION,
        declaration_date=DECLARATION_DATE,
        subsystem_health_avg=gate_report.overall_score,
        overall_grade=gate_report.overall_grade,
        gate_passed=gate_report.gate_passed,
        subsystem_summary=tuple(summaries),
        declaration_text=body,
    )


def render_declaration(decl: LegacyDeclaration) -> str:
    """선언문 텍스트 렌더링."""
    lines: list[str] = []
    for s in decl.subsystem_summary:
        filled = max(0, min(10, int(s.score / 10)))
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"  {s.name:<20} {bar} {s.score:.1f}% ({s.grade}) [{s.status}]")

    gate_status = "통과" if decl.gate_passed else "조건부"
    return DECLARATION_TEMPLATE.format(
        project_full_name=decl.project_full_name,
        project_name=decl.project_name,
        version=decl.version,
        declaration_date=decl.declaration_date,
        overall_grade=decl.overall_grade,
        gate_status=gate_status,
        subsystem_lines="\n".join(lines),
        body=decl.declaration_text,
    )


def generate_certificate(
    decl: LegacyDeclaration | None = None,
    repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Legacy 인증서 데이터."""
    if decl is None:
        decl = generate_declaration(repo_root)
    return {
        "certificate_type": "SDACS Legacy Declaration",
        "project": decl.project_name,
        "version": decl.version,
        "date": decl.declaration_date,
        "grade": decl.overall_grade,
        "gate_passed": decl.gate_passed,
        "status": "Full Legacy" if decl.gate_passed else "Conditional Legacy",
        "subsystems": {
            s.name: {"score": s.score, "grade": s.grade, "status": s.status}
            for s in decl.subsystem_summary
        },
    }


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 400 -- SDACS Legacy 선언",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--declare", action="store_true", help="Legacy 선언문")
    group.add_argument("--certificate", action="store_true", help="Legacy 인증서")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.declare:
        _print_declare(args.json)
    elif args.certificate:
        _print_certificate(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_declare(as_json: bool) -> None:
    decl = generate_declaration()
    if as_json:
        print(json.dumps(decl.as_dict(), ensure_ascii=False, indent=2))
        return
    print(render_declaration(decl))


def _print_certificate(as_json: bool) -> None:
    cert = generate_certificate()
    if as_json:
        print(json.dumps(cert, ensure_ascii=False, indent=2))
        return
    print("=== SDACS Legacy 인증서 ===")
    print(f"  프로젝트: {cert['project']} v{cert['version']}")
    print(f"  날짜:     {cert['date']}")
    print(f"  등급:     {cert['grade']}")
    print(f"  상태:     {cert['status']}")
    for name, info in cert["subsystems"].items():
        print(f"    {name}: {info['score']}% ({info['grade']}) [{info['status']}]")


if __name__ == "__main__":
    _main()
