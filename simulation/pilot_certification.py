"""Phase 309 (GENESIS): 조종자 자격(1~4종) 요건 ↔ 시뮬 교육 모드 매핑.

한국 「항공안전법 시행규칙」 제306조(초경량비행장치 조종자 증명)에 따른 무인멀티콥터
조종자 증명 종별(1~4종)을 기체 최대이륙중량(MTOW)으로부터 결정적으로 분류하고,
종별 교육·시험 요건을 SDACS 시뮬레이터의 단계별 교육 모드(Phase 381)에 매핑한다.
외부 API 호출 없이 분류 + 요건 산출 + 조종자 준비도 판정 + JSON/텍스트 export 만
수행한다 (production 등급의 결정적 구현).

분류 기준 (무인멀티콥터 최대이륙중량):
  - 1종: 25 kg 초과 (자체중량 150 kg 이하)
  - 2종: 7 kg 초과 ~ 25 kg 이하
  - 3종: 2 kg 초과 ~ 7 kg 이하
  - 4종: 250 g 초과 ~ 2 kg 이하
  - 증명 불요: 250 g 이하 (완구용)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# 종별 분류 임계 최대이륙중량(MTOW, kg) — 각 값 "초과" 시 상위 종으로 분류
GRADE1_MIN_MTOW_KG = 25.0
GRADE2_MIN_MTOW_KG = 7.0
GRADE3_MIN_MTOW_KG = 2.0
GRADE4_MIN_MTOW_KG = 0.25
# 초경량비행장치(무인멀티콥터) 자체중량 상한 — 초과 시 항공기 범주
ULTRALIGHT_MAX_WEIGHT_KG = 150.0

# 증명 불요(완구용) 종 코드
GRADE_EXEMPT = 0


@dataclass(frozen=True)
class TrainingRequirement:
    """종별 교육·시험·시뮬 교육 모드 요건."""

    grade: int
    grade_label: str
    online_theory: bool  # 온라인 학과교육 이수
    theory_exam: bool  # 학과시험
    flight_log_hours: float  # 필요 비행경력(시간)
    practical_exam: bool  # 실기시험(국가)
    practical_eval: bool  # 실기평가(전문교육기관)
    min_age: int  # 응시 최소 연령(만)
    sim_modes: tuple[str, ...]  # 매핑되는 시뮬레이터 교육 모드


# 종별 요건 정의 (한국교통안전공단 기준). 상위 종은 하위 모드를 포함.
_REQUIREMENTS: dict[int, TrainingRequirement] = {
    1: TrainingRequirement(
        grade=1,
        grade_label="1종",
        online_theory=True,
        theory_exam=True,
        flight_log_hours=20.0,
        practical_exam=True,
        practical_eval=False,
        min_age=14,
        sim_modes=(
            "tutorial_basics",
            "manual_flight",
            "emergency_response",
            "bvlos_ops",
            "swarm_supervision",
        ),
    ),
    2: TrainingRequirement(
        grade=2,
        grade_label="2종",
        online_theory=True,
        theory_exam=True,
        flight_log_hours=10.0,
        practical_exam=False,
        practical_eval=True,
        min_age=14,
        sim_modes=(
            "tutorial_basics",
            "manual_flight",
            "emergency_response",
            "bvlos_ops",
        ),
    ),
    3: TrainingRequirement(
        grade=3,
        grade_label="3종",
        online_theory=True,
        theory_exam=True,
        flight_log_hours=6.0,
        practical_exam=False,
        practical_eval=False,
        min_age=14,
        sim_modes=(
            "tutorial_basics",
            "manual_flight",
            "emergency_response",
        ),
    ),
    4: TrainingRequirement(
        grade=4,
        grade_label="4종",
        online_theory=True,
        theory_exam=False,
        flight_log_hours=0.0,
        practical_exam=False,
        practical_eval=False,
        min_age=10,
        sim_modes=("tutorial_basics",),
    ),
    GRADE_EXEMPT: TrainingRequirement(
        grade=GRADE_EXEMPT,
        grade_label="증명 불요",
        online_theory=False,
        theory_exam=False,
        flight_log_hours=0.0,
        practical_exam=False,
        practical_eval=False,
        min_age=0,
        sim_modes=(),
    ),
}


@dataclass(frozen=True)
class PilotProfile:
    """조종자 자격 준비 현황."""

    name: str
    age: int
    logged_flight_hours: float = 0.0
    completed_sim_modes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssessmentResult:
    """기체 중량 기준 필요 종별과 조종자 준비도 판정 결과."""

    required_grade: int
    grade_label: str
    age_eligible: bool
    flight_hours_met: bool
    missing_sim_modes: tuple[str, ...]
    is_ready: bool
    reasons: tuple[str, ...] = ()


def classify_grade(mtow_kg: float) -> int:
    """최대이륙중량(kg)으로부터 필요한 조종자 증명 종별을 결정적으로 분류한다.

    250 g 이하는 증명 불요(``GRADE_EXEMPT``)를 반환한다. 0 이하이거나 초경량비행장치
    상한(150 kg)을 초과하면 ``ValueError`` 를 발생시킨다(시스템 경계 입력 검증).
    """
    if mtow_kg <= 0:
        raise ValueError("최대이륙중량은 0보다 커야 함")
    if mtow_kg > ULTRALIGHT_MAX_WEIGHT_KG:
        raise ValueError(
            f"최대이륙중량 {mtow_kg} kg가 초경량비행장치 상한 "
            f"{ULTRALIGHT_MAX_WEIGHT_KG} kg를 초과 (항공기 범주)"
        )
    if mtow_kg > GRADE1_MIN_MTOW_KG:
        return 1
    if mtow_kg > GRADE2_MIN_MTOW_KG:
        return 2
    if mtow_kg > GRADE3_MIN_MTOW_KG:
        return 3
    if mtow_kg > GRADE4_MIN_MTOW_KG:
        return 4
    return GRADE_EXEMPT


def requirement_for(grade: int) -> TrainingRequirement:
    """종별 코드(0~4)에 해당하는 교육·시험 요건을 반환한다."""
    if grade not in _REQUIREMENTS:
        raise ValueError(f"알 수 없는 종별 코드: {grade}")
    return _REQUIREMENTS[grade]


def assess_pilot(mtow_kg: float, profile: PilotProfile) -> AssessmentResult:
    """기체 중량으로 필요 종별을 정하고 조종자의 준비도를 결정적으로 판정한다."""
    grade = classify_grade(mtow_kg)
    req = requirement_for(grade)
    reasons: list[str] = []

    age_eligible = profile.age >= req.min_age
    if not age_eligible:
        reasons.append(
            f"연령 미달: 만 {profile.age}세 (요건 만 {req.min_age}세 이상)"
        )

    flight_hours_met = profile.logged_flight_hours >= req.flight_log_hours
    if not flight_hours_met:
        reasons.append(
            f"비행경력 부족: {profile.logged_flight_hours:.1f} h "
            f"(요건 {req.flight_log_hours:.1f} h)"
        )

    completed = set(profile.completed_sim_modes)
    missing = tuple(m for m in req.sim_modes if m not in completed)
    if missing:
        reasons.append("미이수 시뮬 교육 모드: " + ", ".join(missing))

    is_ready = age_eligible and flight_hours_met and not missing

    return AssessmentResult(
        required_grade=grade,
        grade_label=req.grade_label,
        age_eligible=age_eligible,
        flight_hours_met=flight_hours_met,
        missing_sim_modes=missing,
        is_ready=is_ready,
        reasons=tuple(reasons),
    )


def build_report(mtow_kg: float, profile: PilotProfile) -> dict[str, Any]:
    """조종자 자격 판정 리포트 데이터를 결정적으로 구성한다."""
    result = assess_pilot(mtow_kg, profile)
    req = requirement_for(result.required_grade)
    return {
        "form_type": "pilot_certification_assessment",
        "aircraft": {"mtow_kg": round(mtow_kg, 3)},
        "pilot": {
            "name": profile.name,
            "age": profile.age,
            "logged_flight_hours": round(profile.logged_flight_hours, 2),
            "completed_sim_modes": list(profile.completed_sim_modes),
        },
        "requirement": {
            "grade": req.grade,
            "grade_label": req.grade_label,
            "online_theory": req.online_theory,
            "theory_exam": req.theory_exam,
            "flight_log_hours": req.flight_log_hours,
            "practical_exam": req.practical_exam,
            "practical_eval": req.practical_eval,
            "min_age": req.min_age,
            "sim_modes": list(req.sim_modes),
        },
        "assessment": {
            "required_grade": result.required_grade,
            "grade_label": result.grade_label,
            "age_eligible": result.age_eligible,
            "flight_hours_met": result.flight_hours_met,
            "missing_sim_modes": list(result.missing_sim_modes),
            "is_ready": result.is_ready,
            "reasons": list(result.reasons),
        },
    }


def export_json(report: dict[str, Any]) -> str:
    """리포트 데이터를 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def export_text(report: dict[str, Any]) -> str:
    """리포트 데이터를 사람이 읽는 한국어 양식 텍스트로 변환한다."""
    ac = report["aircraft"]
    p = report["pilot"]
    r = report["requirement"]
    a = report["assessment"]
    lines = [
        "═══ 조종자 증명 자격 판정 ═══",
        "",
        f"[기체] 최대이륙중량 {ac['mtow_kg']} kg → 필요 증명: {r['grade_label']}",
        "",
        "[조종자]",
        f"  성명:     {p['name']}",
        f"  연령:     만 {p['age']}세",
        f"  비행경력: {p['logged_flight_hours']} h",
        "",
        f"[{r['grade_label']} 요건]",
        f"  온라인 학과교육: {'필요' if r['online_theory'] else '불요'}",
        f"  학과시험:       {'필요' if r['theory_exam'] else '불요'}",
        f"  비행경력:       {r['flight_log_hours']} h",
        f"  실기시험:       {'필요' if r['practical_exam'] else '불요'}",
        f"  실기평가:       {'필요' if r['practical_eval'] else '불요'}",
        f"  최소연령:       만 {r['min_age']}세",
        f"  시뮬 교육 모드: {', '.join(r['sim_modes']) or '(없음)'}",
        "",
        "[판정]",
        f"  연령 충족:   {'예' if a['age_eligible'] else '아니오'}",
        f"  경력 충족:   {'예' if a['flight_hours_met'] else '아니오'}",
        f"  준비 완료:   {'예' if a['is_ready'] else '아니오'}",
    ]
    if a["missing_sim_modes"]:
        lines.append("  미이수 모드: " + ", ".join(a["missing_sim_modes"]))
    if a["reasons"]:
        lines.append("  사유:")
        lines += [f"   - {x}" for x in a["reasons"]]
    return "\n".join(lines)
