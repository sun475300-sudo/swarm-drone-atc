"""GENESIS Phase 396 -- GENESIS 트랙 종합 보고서.

Phase 301-400 GENESIS 트랙의 교육·인수인계·인증 산출물을 종합하여
Legacy 선언(Phase 400) 전 트랙 완성도를 정량 산정합니다.

3개 하위 시스템 통합:
- Phase 393 maturity_assessment → 프로젝트 성숙도 (A~F)
- Phase 394 handover_checklist → 인수인계 준비도 (%)
- Phase 395 education_asset_registry → 교육 자산 커버리지 (%)

CLI:
    python simulation/genesis_report.py --report
    python simulation/genesis_report.py --status
    python simulation/genesis_report.py --json
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

from simulation.education_asset_registry import verify_assets  # noqa: E402
from simulation.handover_checklist import check_handover  # noqa: E402
from simulation.maturity_assessment import assess  # noqa: E402

GENESIS_PHASES: tuple[tuple[int, str, str], ...] = (
    (301, "certification", "인증 프레임워크 기초"),
    (302, "certification", "SORA 자동 계산기"),
    (303, "certification", "RTM 요구사항 매핑"),
    (304, "certification", "안전성 분석 FMEA"),
    (305, "certification", "비행 시험 프로토콜"),
    (306, "certification", "RTM 5계층 커버리지"),
    (307, "certification", "DO-178C 적합성"),
    (308, "certification", "ADS-B 메시지 생성"),
    (309, "certification", "조종자 자격 매핑"),
    (310, "certification", "SORA GRC/ARC 갱신"),
    (311, "certification", "위험 평가 통합"),
    (322, "ecosystem", "생태계 연계 모듈"),
    (341, "field_test", "목포 해역 실좌표"),
    (342, "field_test", "환경 시나리오"),
    (362, "autonomy", "APF+RL 하이브리드 회피"),
    (364, "autonomy", "V2X 메시지 규격"),
    (367, "autonomy", "스웜 자가 치유"),
    (381, "education", "교육 모드 튜토리얼"),
    (382, "education", "실습 과제 10종"),
    (383, "education", "15주 커리큘럼"),
    (384, "education", "조종자 문제은행"),
    (385, "education", "온보딩 자동화"),
    (386, "education", "코드 고고학 가이드"),
    (390, "education", "아카이브 전략"),
    (391, "education", "고교·일반인 체험판"),
    (392, "education", "성과 요약 대시보드"),
    (393, "education", "프로젝트 성숙도 평가"),
    (394, "education", "인수인계 체크리스트"),
    (395, "education", "교육 자산 레지스트리"),
    (396, "legacy", "GENESIS 종합 보고서"),
)

TOTAL_GENESIS_PHASES = 100  # Phase 301-400
LEGACY_MIN_COMPLETION_PCT: float = 30.0

TRACK_CATEGORIES: tuple[str, ...] = (
    "certification",
    "ecosystem",
    "field_test",
    "autonomy",
    "education",
    "legacy",
)

CATEGORY_NAMES_KO: dict[str, str] = {
    "certification": "인증·규제",
    "ecosystem": "생태계",
    "field_test": "실증",
    "autonomy": "자율·AI",
    "education": "교육·인수인계",
    "legacy": "레거시 선언",
}


@dataclass(frozen=True)
class CategoryProgress:
    """카테고리별 진척."""

    category: str
    name_ko: str
    completed_count: int
    phase_ids: tuple[int, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "name_ko": self.name_ko,
            "completed_count": self.completed_count,
            "phase_ids": list(self.phase_ids),
        }


@dataclass(frozen=True)
class SubsystemScore:
    """하위 시스템 점수."""

    name: str
    score: float
    grade: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "grade": self.grade,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class GenesisReport:
    """GENESIS 트랙 종합 보고서."""

    completed_phases: int
    total_phases: int
    completion_pct: float
    categories: tuple[CategoryProgress, ...]
    subsystems: tuple[SubsystemScore, ...]
    overall_grade: str
    legacy_ready: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "completed_phases": self.completed_phases,
            "total_phases": self.total_phases,
            "completion_pct": self.completion_pct,
            "categories": [c.as_dict() for c in self.categories],
            "subsystems": [s.as_dict() for s in self.subsystems],
            "overall_grade": self.overall_grade,
            "legacy_ready": self.legacy_ready,
        }


def _grade_from_pct(pct: float) -> str:
    if pct >= 90:
        return "A"
    if pct >= 80:
        return "B"
    if pct >= 70:
        return "C"
    if pct >= 60:
        return "D"
    return "F"


def _collect_categories() -> tuple[CategoryProgress, ...]:
    results: list[CategoryProgress] = []
    for cat in TRACK_CATEGORIES:
        phases = tuple(
            p for p, c, _ in GENESIS_PHASES if c == cat
        )
        results.append(CategoryProgress(
            category=cat,
            name_ko=CATEGORY_NAMES_KO[cat],
            completed_count=len(phases),
            phase_ids=phases,
        ))
    return tuple(results)


def _assess_subsystems(
    repo_root: pathlib.Path,
) -> tuple[SubsystemScore, ...]:
    try:
        maturity = assess(repo_root)
    except Exception as exc:
        raise RuntimeError(f"maturity_assessment failed: {exc}") from exc
    maturity_pct = maturity.overall_score
    maturity_grade = maturity.grade

    try:
        handover = check_handover(repo_root)
    except Exception as exc:
        raise RuntimeError(f"handover_checklist failed: {exc}") from exc
    handover_pct = handover.overall_pct

    try:
        assets = verify_assets(repo_root)
    except Exception as exc:
        raise RuntimeError(f"education_asset_registry failed: {exc}") from exc
    asset_pct = assets.coverage_pct

    return (
        SubsystemScore(
            "maturity",
            maturity_pct,
            maturity_grade,
            f"7차원 {maturity.total_checks}항목 평가",
        ),
        SubsystemScore(
            "handover",
            handover_pct,
            _grade_from_pct(handover_pct),
            f"{handover.total_passed}/{handover.total_items} 항목 완료",
        ),
        SubsystemScore(
            "education_assets",
            asset_pct,
            _grade_from_pct(asset_pct),
            f"{assets.verified_count}/{assets.total_assets} 자산 검증",
        ),
    )


def _overall_grade(subsystems: tuple[SubsystemScore, ...]) -> str:
    if not subsystems:
        return "F"
    avg = sum(s.score for s in subsystems) / len(subsystems)
    return _grade_from_pct(avg)


def generate_report(
    repo_root: pathlib.Path | None = None,
) -> GenesisReport:
    """GENESIS 트랙 종합 보고서 생성."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    categories = _collect_categories()
    completed = len(GENESIS_PHASES)
    pct = round(completed / TOTAL_GENESIS_PHASES * 100, 1)

    subsystems = _assess_subsystems(root)
    grade = _overall_grade(subsystems)
    legacy_ready = grade in ("A", "B") and pct >= LEGACY_MIN_COMPLETION_PCT

    return GenesisReport(
        completed_phases=completed,
        total_phases=TOTAL_GENESIS_PHASES,
        completion_pct=pct,
        categories=categories,
        subsystems=subsystems,
        overall_grade=grade,
        legacy_ready=legacy_ready,
    )


def get_status(
    repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """간단 상태 요약."""
    root = repo_root or _REPO_ROOT
    report = generate_report(root)
    return {
        "completion_pct": report.completion_pct,
        "overall_grade": report.overall_grade,
        "legacy_ready": report.legacy_ready,
        "subsystem_grades": {
            s.name: s.grade for s in report.subsystems
        },
    }


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 396 -- GENESIS 트랙 종합 보고서",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--report", action="store_true", help="종합 보고서")
    group.add_argument("--status", action="store_true", help="간단 상태")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.report:
        _print_report(args.json)
    elif args.status:
        _print_status(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_report(as_json: bool) -> None:
    report = generate_report()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=== GENESIS 트랙 종합 보고서 ===")
    print(f"  Phase 진척: {report.completed_phases}/{report.total_phases} ({report.completion_pct}%)")
    print(f"  종합 등급:  {report.overall_grade}")
    print(f"  Legacy 준비: {'예' if report.legacy_ready else '아니오'}")
    print()
    print("--- 카테고리별 ---")
    for c in report.categories:
        print(f"  [{c.name_ko}] {c.completed_count}개 Phase 완료")
    print()
    print("--- 하위 시스템 ---")
    for s in report.subsystems:
        filled = max(0, min(10, int(s.score / 10)))
        bar = "█" * filled + "░" * (10 - filled)
        print(f"  {s.name:<20} {bar} {s.score}% ({s.grade}) — {s.detail}")


def _print_status(as_json: bool) -> None:
    status = get_status()
    if as_json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return
    print("=== GENESIS 상태 ===")
    print(f"  진척: {status['completion_pct']}%")
    print(f"  등급: {status['overall_grade']}")
    print(f"  Legacy: {'준비됨' if status['legacy_ready'] else '미준비'}")
    for name, grade in status["subsystem_grades"].items():
        print(f"    {name}: {grade}")


if __name__ == "__main__":
    _main()
