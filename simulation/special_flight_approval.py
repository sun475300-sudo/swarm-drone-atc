"""Phase 310 (GENESIS): 야간·비가시(BVLOS) 특별비행승인 안전기준 검증.

한국 「항공안전법 시행규칙」 제312조의2(무인비행장치 특별비행승인) 및 국토교통부
「드론 특별비행을 위한 안전기준 및 승인절차 고시」에 따른 야간/비가시권 비행의
안전기준 충족 여부를 시뮬레이션 운용계획으로부터 결정적으로 검증한다.

`flight_plan_filing.py`(Phase 303)가 "특별비행승인이 *필요한가*"를 판정한다면,
본 모듈은 "특별비행승인 안전기준을 *충족하는가*"를 항목별로 검증한다. 외부 API
호출 없이 입력 검증 + 항목별 적합 판정 + JSON/텍스트 export 만 수행한다.

안전기준 분류:
  - 공통(야간·비가시 공통): 충돌방지등·통신두절 자동귀환·지오펜스·자동비행종료·자격/보험
  - 야간: 항법등·이착륙장 조명·야간 식별장비·시각보조원
  - 비가시: 탐지및회피(또는 시각보조원)·통신 이중화·위성항법 이중화·비상착륙지점
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

SAFETY_STANDARD = "국토교통부 「드론 특별비행을 위한 안전기준 및 승인절차 고시」"


@dataclass(frozen=True)
class SafetyEquipment:
    """기체에 탑재/구비된 안전 장비·기능."""

    anti_collision_light: bool = False  # 충돌방지등(가시거리 3 km)
    nav_lights: bool = False  # 항법등(위치등)
    autonomous_flight_termination: bool = False  # 자동 비행종료/비상착륙
    return_to_home: bool = False  # 통신두절 시 자동 귀환(RTH)
    detect_and_avoid: bool = False  # 탐지 및 회피(DAA)
    dual_comms_link: bool = False  # 통신 링크 이중화
    dual_gnss: bool = False  # 위성항법 이중화
    geofence: bool = False  # 지오펜스
    ir_camera: bool = False  # 야간 식별 장비(적외선/EO)
    takeoff_landing_lighting: bool = False  # 이착륙장 조명


@dataclass(frozen=True)
class OperationPlan:
    """특별비행 운용계획."""

    is_night: bool = False  # 야간(일몰 후~일출 전) 비행
    is_bvlos: bool = False  # 비가시권(BVLOS) 비행
    ground_observers: int = 0  # 시각보조원 수
    emergency_landing_sites: int = 0  # 사전 설정 비상착륙 지점 수
    pilot_certified: bool = False  # 조종자 자격 보유
    insured: bool = False  # 책임보험 가입
    flight_distance_km: float = 0.0  # 최대 비행 거리


@dataclass(frozen=True)
class RequirementResult:
    """단일 안전기준 항목의 검증 결과."""

    code: str
    description: str
    satisfied: bool
    category: str  # "공통" | "야간" | "비가시"


@dataclass(frozen=True)
class ApprovalAssessment:
    """특별비행승인 안전기준 종합 판정."""

    approvable: bool
    requirements: tuple[RequirementResult, ...]
    deficiencies: tuple[str, ...]


def _validate(plan: OperationPlan) -> list[str]:
    """운용계획 입력값을 검증하고 오류 목록을 반환한다(시스템 경계 검증)."""
    errors: list[str] = []
    if plan.ground_observers < 0:
        errors.append("시각보조원 수는 음수일 수 없음")
    if plan.emergency_landing_sites < 0:
        errors.append("비상착륙 지점 수는 음수일 수 없음")
    if plan.flight_distance_km < 0:
        errors.append("비행 거리는 음수일 수 없음")
    return errors


def _common_requirements(
    plan: OperationPlan, equip: SafetyEquipment
) -> list[RequirementResult]:
    """야간·비가시 공통 안전기준 항목을 평가한다."""
    return [
        RequirementResult(
            "SA-C1", "충돌방지등 구비", equip.anti_collision_light, "공통"
        ),
        RequirementResult(
            "SA-C2", "통신두절 시 자동 귀환(RTH)", equip.return_to_home, "공통"
        ),
        RequirementResult("SA-C3", "지오펜스 설정", equip.geofence, "공통"),
        RequirementResult(
            "SA-C4",
            "자동 비행종료/비상착륙 기능",
            equip.autonomous_flight_termination,
            "공통",
        ),
        RequirementResult(
            "SA-C5",
            "조종자 자격 및 책임보험",
            plan.pilot_certified and plan.insured,
            "공통",
        ),
    ]


def _night_requirements(
    plan: OperationPlan, equip: SafetyEquipment
) -> list[RequirementResult]:
    """야간 비행 안전기준 항목을 평가한다."""
    return [
        RequirementResult("SA-N1", "항법등(위치등) 점등", equip.nav_lights, "야간"),
        RequirementResult(
            "SA-N2", "이착륙장 조명", equip.takeoff_landing_lighting, "야간"
        ),
        RequirementResult(
            "SA-N3", "야간 식별 장비(적외선/EO)", equip.ir_camera, "야간"
        ),
        RequirementResult(
            "SA-N4",
            "시각보조원 1명 이상 배치",
            plan.ground_observers >= 1,
            "야간",
        ),
    ]


def _bvlos_requirements(
    plan: OperationPlan, equip: SafetyEquipment
) -> list[RequirementResult]:
    """비가시권 비행 안전기준 항목을 평가한다."""
    return [
        RequirementResult(
            "SA-B1",
            "탐지 및 회피(DAA) 또는 시각보조원 배치",
            equip.detect_and_avoid or plan.ground_observers >= 1,
            "비가시",
        ),
        RequirementResult(
            "SA-B2", "통신 링크 이중화", equip.dual_comms_link, "비가시"
        ),
        RequirementResult("SA-B3", "위성항법 이중화", equip.dual_gnss, "비가시"),
        RequirementResult(
            "SA-B4",
            "비상착륙 지점 1개소 이상 사전 설정",
            plan.emergency_landing_sites >= 1,
            "비가시",
        ),
    ]


def assess_special_flight(
    plan: OperationPlan, equip: SafetyEquipment
) -> ApprovalAssessment:
    """특별비행승인 안전기준 충족 여부를 항목별로 결정적으로 판정한다.

    야간/비가시 어느 쪽도 아니면 특별비행 대상이 아니므로 승인 불가로 판정한다.
    적용되는 모든 안전기준 항목이 충족될 때에만 ``approvable`` 이 참이 된다.
    """
    errors = _validate(plan)
    if errors:
        raise ValueError("특별비행 운용계획 검증 실패: " + "; ".join(errors))

    if not (plan.is_night or plan.is_bvlos):
        return ApprovalAssessment(
            approvable=False,
            requirements=(),
            deficiencies=("특별비행(야간/비가시) 대상이 아님",),
        )

    requirements = list(_common_requirements(plan, equip))
    if plan.is_night:
        requirements += _night_requirements(plan, equip)
    if plan.is_bvlos:
        requirements += _bvlos_requirements(plan, equip)

    deficiencies = tuple(
        f"[{r.code}] {r.description} 미충족"
        for r in requirements
        if not r.satisfied
    )
    return ApprovalAssessment(
        approvable=not deficiencies,
        requirements=tuple(requirements),
        deficiencies=deficiencies,
    )


def build_report(plan: OperationPlan, equip: SafetyEquipment) -> dict[str, Any]:
    """특별비행승인 안전기준 검증 보고서 데이터를 결정적으로 구성한다."""
    assessment = assess_special_flight(plan, equip)
    flight_types = []
    if plan.is_night:
        flight_types.append("야간")
    if plan.is_bvlos:
        flight_types.append("비가시")

    return {
        "standard": SAFETY_STANDARD,
        "flight_types": flight_types,
        "operation": {
            "ground_observers": plan.ground_observers,
            "emergency_landing_sites": plan.emergency_landing_sites,
            "pilot_certified": plan.pilot_certified,
            "insured": plan.insured,
            "flight_distance_km": round(plan.flight_distance_km, 2),
        },
        "requirements": [
            {
                "code": r.code,
                "description": r.description,
                "category": r.category,
                "satisfied": r.satisfied,
            }
            for r in assessment.requirements
        ],
        "assessment": {
            "approvable": assessment.approvable,
            "satisfied_count": sum(
                1 for r in assessment.requirements if r.satisfied
            ),
            "total_count": len(assessment.requirements),
            "deficiencies": list(assessment.deficiencies),
        },
    }


def export_json(report: dict[str, Any]) -> str:
    """검증 보고서를 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def export_text(report: dict[str, Any]) -> str:
    """검증 보고서를 사람이 읽는 한국어 양식 텍스트로 변환한다."""
    op = report["operation"]
    asm = report["assessment"]
    types = " · ".join(report["flight_types"]) or "(해당 없음)"
    lines = [
        "═══ 드론 특별비행승인 안전기준 검증 보고서 ═══",
        "",
        f"근거: {report['standard']}",
        f"비행 유형: {types}",
        "",
        "[운용계획]",
        f"  시각보조원:   {op['ground_observers']} 명",
        f"  비상착륙지점: {op['emergency_landing_sites']} 개소",
        f"  조종자 자격:  {'보유' if op['pilot_certified'] else '미보유'}",
        f"  책임보험:     {'가입' if op['insured'] else '미가입'}",
        f"  최대 거리:    {op['flight_distance_km']} km",
        "",
        "[안전기준 항목]",
    ]
    for r in report["requirements"]:
        mark = "✔" if r["satisfied"] else "✘"
        lines.append(f"  {mark} [{r['code']}/{r['category']}] {r['description']}")
    lines += [
        "",
        "[판정]",
        f"  충족: {asm['satisfied_count']} / {asm['total_count']}",
        f"  승인 가능: {'예' if asm['approvable'] else '아니오'}",
    ]
    if asm["deficiencies"]:
        lines.append("  미충족 사유:")
        lines += [f"   - {d}" for d in asm["deficiencies"]]
    return "\n".join(lines)
