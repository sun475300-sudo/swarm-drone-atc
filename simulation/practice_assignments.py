"""GENESIS Phase 382 — 학부 실습 과제 10종 (드론 관제 시스템 설계 과목).

Phase 381 교육 모드(5단계 튜토리얼)에서 익힌 개념을 학생이 직접 실험·분석하는
과제 세트다. 각 과제는 시나리오 정의·채점 기준·합격 임계값을 갖추며, SDACS
시뮬레이터를 도구로 활용한다.

과제 구조
---------
- ``Assignment`` 데이터클래스: 과제 메타(제목·설명·카테고리·난이도·목표 학습성과)
- ``Criterion`` 데이터클래스: 채점 기준 하나(이름·배점·합격 임계·측정 방법)
- ``Submission`` 데이터클래스: 학생 제출(과제 ID·측정값 dict)
- ``grade(submission) -> GradeResult``: 결정적 채점(총점·합격 여부·항목별 점수)
- ``ASSIGNMENTS``: 10종 과제 레지스트리 (불변)

채점은 기준별 달성률(값/임계, 최대 1.0) × 배점을 합산한다.
부울 기준(달성 여부)은 달성 시 배점 전액, 미달 시 0.

정직 공시: 이 과제 세트는 교수자 재량으로 조정 가능한 *제안*이며,
특정 대학·학과의 공식 커리큘럼이 아니다. 채점 로직은 결정적이나
시뮬레이션 KPI 측정은 시드·파라미터에 의존한다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/practice_assignments.py --list       # 과제 목록
    python simulation/practice_assignments.py --detail 1   # 과제 1 상세
    python simulation/practice_assignments.py --rubric 1   # 과제 1 채점 기준표
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class Criterion:
    """채점 기준 하나."""

    name: str
    description: str
    max_points: float
    threshold: float
    is_boolean: bool = False
    is_lower_better: bool = False

    def __post_init__(self) -> None:
        if self.max_points <= 0:
            raise ValueError(f"max_points must be positive: {self.max_points}")
        if not self.is_boolean and self.threshold <= 0:
            raise ValueError(f"threshold must be positive: {self.threshold}")


@dataclass(frozen=True)
class Assignment:
    """실습 과제 정의."""

    assignment_id: int
    title: str
    description: str
    category: str
    difficulty: str
    week: int
    learning_outcomes: tuple[str, ...]
    criteria: tuple[Criterion, ...]
    sim_command_hint: str = ""

    @property
    def total_points(self) -> float:
        return sum(c.max_points for c in self.criteria)


@dataclass(frozen=True)
class CriterionScore:
    """채점 기준별 점수."""

    criterion_name: str
    raw_value: float
    achieved_ratio: float
    points_earned: float
    max_points: float
    passed: bool


@dataclass(frozen=True)
class GradeResult:
    """채점 결과."""

    assignment_id: int
    scores: tuple[CriterionScore, ...]
    total_earned: float
    total_possible: float
    percentage: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "total_earned": round(self.total_earned, 2),
            "total_possible": round(self.total_possible, 2),
            "percentage": round(self.percentage, 1),
            "passed": self.passed,
            "criteria": [
                {
                    "name": s.criterion_name,
                    "raw_value": s.raw_value,
                    "achieved_ratio": round(s.achieved_ratio, 3),
                    "points_earned": round(s.points_earned, 2),
                    "max_points": s.max_points,
                    "passed": s.passed,
                }
                for s in self.scores
            ],
        }


@dataclass(frozen=True)
class Submission:
    """학생 제출."""

    assignment_id: int
    measurements: MappingProxyType[str, float]

    def __init__(self, assignment_id: int, measurements: dict[str, float]) -> None:
        object.__setattr__(self, "assignment_id", assignment_id)
        for key, val in measurements.items():
            if not math.isfinite(val):
                raise ValueError(f"measurement '{key}' must be finite, got {val}")
            if val < 0:
                raise ValueError(f"measurement '{key}' must be non-negative, got {val}")
        object.__setattr__(self, "measurements", MappingProxyType(dict(measurements)))


PASS_PERCENTAGE: float = 60.0

# ── 10종 과제 레지스트리 ────────────────────────────────────────────
ASSIGNMENTS: tuple[Assignment, ...] = (
    Assignment(
        assignment_id=1,
        title="기본 시뮬레이션 실행 및 KPI 측정",
        description=(
            "SDACS 시뮬레이터를 기본 설정(20대, 60초)으로 실행하고 "
            "충돌 수·근접경고 수·충돌해결률을 기록한다."
        ),
        category="시뮬레이션 기초",
        difficulty="입문",
        week=2,
        learning_outcomes=("PO2", "PO5"),
        criteria=(
            Criterion("collision_count", "충돌 수 20 이하", 30.0, 20.0, is_lower_better=True),
            Criterion("resolution_rate", "충돌해결률 95% 이상", 40.0, 0.95),
            Criterion("report_submitted", "결과 보고서 제출", 30.0, 1.0, is_boolean=True),
        ),
        sim_command_hint="python main.py simulate --duration 60 --drones 20",
    ),
    Assignment(
        assignment_id=2,
        title="드론 규모별 성능 비교 실험",
        description=(
            "20·50·100대 규모에서 각각 시뮬레이션을 수행하고 "
            "충돌해결률·경로효율·처리량을 비교 분석한다."
        ),
        category="실험 설계",
        difficulty="기초",
        week=4,
        learning_outcomes=("PO1", "PO2", "PO4"),
        criteria=(
            Criterion("scenarios_run", "3가지 규모 실행 완료", 20.0, 3.0),
            Criterion("resolution_rate_min", "최소 충돌해결률 90%", 30.0, 0.90),
            Criterion("analysis_depth", "비교 분석 항목 3개 이상", 30.0, 3.0),
            Criterion("chart_included", "비교 차트 포함", 20.0, 1.0, is_boolean=True),
        ),
        sim_command_hint="python main.py simulate --drones {20,50,100}",
    ),
    Assignment(
        assignment_id=3,
        title="APF 파라미터 튜닝 실험",
        description=(
            "APF 인력/척력 파라미터를 변경하며 충돌 회피 성능 변화를 관찰한다. "
            "FIRAS 장 강도·유효 범위를 조절하여 최적 조합을 찾는다."
        ),
        category="알고리즘 이해",
        difficulty="중급",
        week=6,
        learning_outcomes=("PO1", "PO4", "PO5"),
        criteria=(
            Criterion("param_sets_tested", "파라미터 조합 5세트 이상", 25.0, 5.0),
            Criterion("best_resolution_rate", "최적 조합 해결률 97%+", 35.0, 0.97),
            Criterion("sensitivity_analysis", "민감도 분석 수행", 20.0, 1.0, is_boolean=True),
            Criterion("conclusion_quality", "결론 타당성 (교수 평가)", 20.0, 0.6),
        ),
        sim_command_hint="config/default_simulation.yaml 수정 후 시뮬 반복",
    ),
    Assignment(
        assignment_id=4,
        title="시나리오 설계 및 검증",
        description=(
            "config/scenario_params/ 형식에 맞춰 새로운 시나리오(도심 배송 등)를 "
            "직접 설계하고, 시뮬레이션으로 검증한다."
        ),
        category="시나리오 설계",
        difficulty="중급",
        week=7,
        learning_outcomes=("PO4", "PO5", "PO6"),
        criteria=(
            Criterion("scenario_valid", "시나리오 스키마 적합", 25.0, 1.0, is_boolean=True),
            Criterion("nfz_defined", "NFZ 1개 이상 정의", 15.0, 1.0),
            Criterion("drone_count", "드론 30대 이상 운용", 20.0, 30.0),
            Criterion("safety_kpi_met", "안전 KPI 충족", 40.0, 0.90),
        ),
        sim_command_hint="python main.py scenario custom_scenario",
    ),
    Assignment(
        assignment_id=5,
        title="Monte Carlo 통계 검증",
        description=(
            "단일 시나리오에 대해 Monte Carlo 스윕(최소 50시드)을 수행하고 "
            "95% 신뢰구간을 산출하여 결과의 통계적 유의성을 평가한다."
        ),
        category="통계 분석",
        difficulty="중급",
        week=8,
        learning_outcomes=("PO1", "PO2"),
        criteria=(
            Criterion("seeds_run", "시드 50개 이상 실행", 20.0, 50.0),
            Criterion("ci_computed", "95% 신뢰구간 산출", 30.0, 1.0, is_boolean=True),
            Criterion("mean_resolution", "평균 해결률 93%+", 30.0, 0.93),
            Criterion("variance_reported", "분산·표준편차 보고", 20.0, 1.0, is_boolean=True),
        ),
        sim_command_hint="python main.py monte-carlo --mode quick",
    ),
    Assignment(
        assignment_id=6,
        title="5계층 안전망 Ablation 실험",
        description=(
            "APF·CBS 계층을 각각 비활성화한 Ablation 실험을 수행하여 "
            "각 안전 계층의 기여도를 정량적으로 분석한다."
        ),
        category="안전 공학",
        difficulty="고급",
        week=10,
        learning_outcomes=("PO4", "PO6"),
        criteria=(
            Criterion("ablation_configs", "Ablation 구성 4종 실행", 25.0, 4.0),
            Criterion("degradation_measured", "성능 저하율 측정", 30.0, 1.0, is_boolean=True),
            Criterion("layer_ranking", "계층별 기여도 순위 도출", 25.0, 1.0, is_boolean=True),
            Criterion("safety_insight", "안전 설계 시사점 도출", 20.0, 1.0, is_boolean=True),
        ),
        sim_command_hint="python scripts/ablation_study.py --seeds 10",
    ),
    Assignment(
        assignment_id=7,
        title="기상 조건별 성능 분석",
        description=(
            "무풍·약풍·강풍(10+ m/s) 조건에서 시뮬레이션을 수행하고 "
            "APF_PARAMS_WINDY 자동 전환 효과를 분석한다."
        ),
        category="환경 시뮬레이션",
        difficulty="중급",
        week=9,
        learning_outcomes=("PO2", "PO6"),
        criteria=(
            Criterion("wind_conditions", "3가지 기상 조건 실행", 25.0, 3.0),
            Criterion("windy_mode_observed", "강풍 모드 전환 관찰", 25.0, 1.0, is_boolean=True),
            Criterion("performance_comparison", "조건별 KPI 비교표", 30.0, 1.0, is_boolean=True),
            Criterion("recommendation", "운용 권고사항 도출", 20.0, 1.0, is_boolean=True),
        ),
        sim_command_hint="python main.py scenario strong_wind",
    ),
    Assignment(
        assignment_id=8,
        title="SORA 위험도 평가 실습",
        description=(
            "JARUS SORA 2.0 절차에 따라 자신이 설계한 시나리오의 "
            "SAIL(Specific Assurance and Integrity Level)을 산정한다."
        ),
        category="규제 준수",
        difficulty="고급",
        week=11,
        learning_outcomes=("PO6", "PO10"),
        criteria=(
            Criterion("sora_completed", "SORA 평가서 작성 완료", 30.0, 1.0, is_boolean=True),
            Criterion("sail_computed", "SAIL 등급 산출", 25.0, 1.0, is_boolean=True),
            Criterion("mitigation_identified", "경감 조치 2개 이상 식별", 25.0, 2.0),
            Criterion("regulation_referenced", "관련 법규 인용", 20.0, 1.0, is_boolean=True),
        ),
        sim_command_hint="시뮬레이터 soraAssess() API 활용",
    ),
    Assignment(
        assignment_id=9,
        title="웹 시뮬레이터 시나리오 시연",
        description=(
            "swarm_3d_simulator.html에서 자신의 시나리오를 로드하고 "
            "3D 시각화로 관제 과정을 시연한다. CPA 예측선·어드바이저리를 해석한다."
        ),
        category="시각화·발표",
        difficulty="기초",
        week=12,
        learning_outcomes=("PO5", "PO7"),
        criteria=(
            Criterion("demo_executed", "라이브 시연 수행", 30.0, 1.0, is_boolean=True),
            Criterion("cpa_explained", "CPA 예측선 해석", 25.0, 1.0, is_boolean=True),
            Criterion("advisory_explained", "어드바이저리 유형 설명", 25.0, 1.0, is_boolean=True),
            Criterion("qa_response", "질의응답 대응", 20.0, 0.6),
        ),
        sim_command_hint="브라우저에서 simulator.html 열기",
    ),
    Assignment(
        assignment_id=10,
        title="종합 프로젝트 — 맞춤형 관제 시스템 제안",
        description=(
            "특정 응용 분야(농업 방제·의료 배송·산불 감시 등)를 선택하여 "
            "SDACS 기반 맞춤형 관제 시스템을 제안하고, 시뮬레이션으로 "
            "타당성을 검증하는 종합 보고서를 작성한다."
        ),
        category="종합 설계",
        difficulty="고급",
        week=14,
        learning_outcomes=("PO1", "PO2", "PO4", "PO5", "PO6", "PO10"),
        criteria=(
            Criterion("domain_analysis", "응용 분야 요구사항 분석", 15.0, 1.0, is_boolean=True),
            Criterion("system_design", "시스템 설계 문서", 20.0, 1.0, is_boolean=True),
            Criterion("simulation_results", "시뮬레이션 검증 결과", 25.0, 0.90),
            Criterion("report_quality", "보고서 완성도 (교수 평가)", 20.0, 0.6),
            Criterion("originality", "독창성·기여도", 20.0, 0.6),
        ),
        sim_command_hint="자유 (시나리오·코드 수정 허용)",
    ),
)

_ASSIGNMENT_MAP: MappingProxyType[int, Assignment] = MappingProxyType(
    {a.assignment_id: a for a in ASSIGNMENTS}
)


def get_assignment(assignment_id: int) -> Assignment:
    """과제 ID로 조회."""
    if assignment_id not in _ASSIGNMENT_MAP:
        raise ValueError(
            f"Unknown assignment_id={assignment_id}. "
            f"Valid: {sorted(_ASSIGNMENT_MAP)}"
        )
    return _ASSIGNMENT_MAP[assignment_id]


def list_assignments() -> list[dict[str, Any]]:
    """전체 과제 목록 반환 (요약)."""
    return [
        {
            "id": a.assignment_id,
            "title": a.title,
            "category": a.category,
            "difficulty": a.difficulty,
            "week": a.week,
            "total_points": a.total_points,
            "criteria_count": len(a.criteria),
        }
        for a in ASSIGNMENTS
    ]


def _score_criterion(criterion: Criterion, value: float) -> CriterionScore:
    """단일 기준 채점."""
    if criterion.is_boolean:
        passed = value >= 1.0
        ratio = 1.0 if passed else 0.0
    elif criterion.is_lower_better:
        ratio = min(criterion.threshold / value, 1.0) if value > 0 else 1.0
        passed = value <= criterion.threshold
    else:
        ratio = min(value / criterion.threshold, 1.0) if criterion.threshold > 0 else 0.0
        passed = value >= criterion.threshold
    earned = ratio * criterion.max_points
    return CriterionScore(
        criterion_name=criterion.name,
        raw_value=value,
        achieved_ratio=ratio,
        points_earned=earned,
        max_points=criterion.max_points,
        passed=passed,
    )


def grade(submission: Submission) -> GradeResult:
    """학생 제출을 결정적으로 채점한다."""
    assignment = get_assignment(submission.assignment_id)
    scores: list[CriterionScore] = []
    for criterion in assignment.criteria:
        value = submission.measurements.get(criterion.name, 0.0)
        scores.append(_score_criterion(criterion, value))
    total_earned = sum(s.points_earned for s in scores)
    total_possible = assignment.total_points
    pct = (total_earned / total_possible * 100.0) if total_possible > 0 else 0.0
    return GradeResult(
        assignment_id=submission.assignment_id,
        scores=tuple(scores),
        total_earned=total_earned,
        total_possible=total_possible,
        percentage=pct,
        passed=pct >= PASS_PERCENTAGE,
    )


def rubric_text(assignment_id: int) -> str:
    """과제 채점 기준표를 텍스트로 반환."""
    a = get_assignment(assignment_id)
    lines = [
        f"과제 {a.assignment_id}: {a.title}",
        f"카테고리: {a.category} | 난이도: {a.difficulty} | 주차: {a.week}주",
        f"학습성과: {', '.join(a.learning_outcomes)}",
        f"합격 기준: {PASS_PERCENTAGE}% 이상",
        "",
        "채점 기준표:",
        f"{'기준':<30} {'배점':>6} {'임계값':>10} {'유형':>8}",
        "-" * 58,
    ]
    for c in a.criteria:
        kind = "부울" if c.is_boolean else ("역비율" if c.is_lower_better else "비율")
        threshold_str = "달성" if c.is_boolean else str(c.threshold)
        lines.append(f"{c.name:<30} {c.max_points:>6.0f} {threshold_str:>10} {kind:>8}")
    lines.append(f"{'합계':<30} {a.total_points:>6.0f}")
    if a.sim_command_hint:
        lines.append(f"\n실행 힌트: {a.sim_command_hint}")
    return "\n".join(lines)


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="GENESIS Phase 382 -- 실습 과제 10종")
    parser.add_argument("--list", action="store_true", help="과제 목록")
    parser.add_argument("--detail", type=int, metavar="ID", help="과제 상세")
    parser.add_argument("--rubric", type=int, metavar="ID", help="채점 기준표")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.list:
        data = list_assignments()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"{'ID':>3} {'주차':>4} {'난이도':<6} {'배점':>5} {'제목'}")
            print("-" * 60)
            for a in data:
                print(
                    f"{a['id']:>3} {a['week']:>4} {a['difficulty']:<6} "
                    f"{a['total_points']:>5.0f} {a['title']}"
                )
    elif args.detail is not None:
        try:
            a = get_assignment(args.detail)
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps({
                "id": a.assignment_id,
                "title": a.title,
                "description": a.description,
                "category": a.category,
                "difficulty": a.difficulty,
                "week": a.week,
                "learning_outcomes": list(a.learning_outcomes),
                "total_points": a.total_points,
                "sim_command_hint": a.sim_command_hint,
            }, ensure_ascii=False, indent=2))
        else:
            print(f"과제 {a.assignment_id}: {a.title}")
            print(f"  설명: {a.description}")
            print(f"  카테고리: {a.category} | 난이도: {a.difficulty} | 주차: {a.week}주")
            print(f"  학습성과: {', '.join(a.learning_outcomes)}")
            print(f"  총 배점: {a.total_points}점")
            if a.sim_command_hint:
                print(f"  실행 힌트: {a.sim_command_hint}")
    elif args.rubric is not None:
        try:
            print(rubric_text(args.rubric))
        except ValueError as exc:
            parser.error(str(exc))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()
