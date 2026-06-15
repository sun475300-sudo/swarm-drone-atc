"""Phase 309 (GENESIS): 조종자 자격(1~4종) ↔ 시뮬 교육 모드 매핑 테스트.

종별 분류·요건 산출·조종자 준비도 판정·export 의 결정성을 검증한다.
"""

import json

import pytest

from simulation.pilot_certification import (
    GRADE_EXEMPT,
    AssessmentResult,
    PilotProfile,
    TrainingRequirement,
    assess_pilot,
    build_report,
    classify_grade,
    export_json,
    export_text,
    requirement_for,
)

# ─── classify_grade: 경계 분류 ───────────────────────────────────────────


def test_classifies_grade1_above_25kg():
    # Arrange / Act
    grade = classify_grade(30.0)
    # Assert
    assert grade == 1


def test_classifies_grade2_between_7_and_25kg():
    assert classify_grade(10.0) == 2


def test_classifies_grade3_between_2_and_7kg():
    assert classify_grade(4.0) == 3


def test_classifies_grade4_between_250g_and_2kg():
    assert classify_grade(1.0) == 4


def test_classifies_exempt_at_or_below_250g():
    assert classify_grade(0.25) == GRADE_EXEMPT
    assert classify_grade(0.2) == GRADE_EXEMPT


def test_boundary_exactly_25kg_is_grade2_not_grade1():
    # 25 kg "초과"가 1종이므로 정확히 25 kg는 2종
    assert classify_grade(25.0) == 2


def test_boundary_exactly_7kg_is_grade3():
    # 7 kg "초과"가 2종이므로 정확히 7 kg는 3종
    assert classify_grade(7.0) == 3


def test_boundary_exactly_2kg_is_grade4():
    # 2 kg "초과"가 3종이므로 정확히 2 kg는 4종
    assert classify_grade(2.0) == 4


def test_boundary_exactly_150kg_is_grade1():
    # 150 kg는 초경량비행장치 상한 "이하"이므로 1종 (초과하지 않음)
    assert classify_grade(150.0) == 1


def test_rejects_zero_or_negative_weight():
    with pytest.raises(ValueError):
        classify_grade(0.0)
    with pytest.raises(ValueError):
        classify_grade(-1.0)


def test_rejects_weight_above_ultralight_limit():
    with pytest.raises(ValueError):
        classify_grade(151.0)


# ─── requirement_for: 종별 요건 ─────────────────────────────────────────


def test_requirement_for_grade1_has_strictest_rules():
    req = requirement_for(1)
    assert isinstance(req, TrainingRequirement)
    assert req.flight_log_hours == 20.0
    assert req.practical_exam is True
    assert req.min_age == 14


def test_requirement_for_grade4_is_online_only():
    req = requirement_for(4)
    assert req.flight_log_hours == 0.0
    assert req.theory_exam is False
    assert req.practical_exam is False
    assert req.min_age == 10
    assert req.sim_modes == ("tutorial_basics",)


def test_higher_grade_sim_modes_superset_of_lower():
    # 상위 종은 하위 종 교육 모드를 포함해야 한다
    g4 = set(requirement_for(4).sim_modes)
    g3 = set(requirement_for(3).sim_modes)
    g2 = set(requirement_for(2).sim_modes)
    g1 = set(requirement_for(1).sim_modes)
    assert g4 <= g3 <= g2 <= g1


def test_requirement_for_unknown_grade_raises():
    with pytest.raises(ValueError):
        requirement_for(9)


# ─── assess_pilot: 준비도 판정 ───────────────────────────────────────────


def test_ready_pilot_meets_all_grade3_requirements():
    profile = PilotProfile(
        name="김조종",
        age=20,
        logged_flight_hours=6.0,
        completed_sim_modes=(
            "tutorial_basics",
            "manual_flight",
            "emergency_response",
        ),
    )
    result = assess_pilot(4.0, profile)  # 3종
    assert isinstance(result, AssessmentResult)
    assert result.required_grade == 3
    assert result.is_ready is True
    assert result.missing_sim_modes == ()
    assert result.reasons == ()


def test_underage_pilot_not_ready():
    profile = PilotProfile(name="이학생", age=12, logged_flight_hours=20.0)
    result = assess_pilot(30.0, profile)  # 1종, 만 14세 이상 필요
    assert result.age_eligible is False
    assert result.is_ready is False
    assert any("연령" in r for r in result.reasons)


def test_insufficient_flight_hours_not_ready():
    profile = PilotProfile(
        name="박초보",
        age=30,
        logged_flight_hours=2.0,
        completed_sim_modes=("tutorial_basics", "manual_flight", "emergency_response"),
    )
    result = assess_pilot(4.0, profile)  # 3종, 6시간 필요
    assert result.flight_hours_met is False
    assert result.is_ready is False


def test_missing_sim_modes_reported():
    profile = PilotProfile(
        name="최훈련",
        age=30,
        logged_flight_hours=6.0,
        completed_sim_modes=("tutorial_basics",),
    )
    result = assess_pilot(4.0, profile)  # 3종, 3개 모드 필요
    assert "manual_flight" in result.missing_sim_modes
    assert "emergency_response" in result.missing_sim_modes
    assert result.is_ready is False


def test_exempt_aircraft_always_ready():
    profile = PilotProfile(name="완구사용자", age=8)
    result = assess_pilot(0.2, profile)  # 250 g 이하, 증명 불요
    assert result.required_grade == GRADE_EXEMPT
    assert result.is_ready is True


def test_exempt_ready_regardless_of_hours_and_modes():
    # 증명 불요 기체는 비행경력·시뮬 모드 이수와 무관하게 준비 완료여야 한다
    no_experience = PilotProfile(name="신규", age=1, logged_flight_hours=0.0)
    result = assess_pilot(0.25, no_experience)  # 정확히 250 g → 증명 불요
    assert result.required_grade == GRADE_EXEMPT
    assert result.is_ready is True
    assert result.missing_sim_modes == ()


# ─── export 및 결정성 ────────────────────────────────────────────────────


def test_build_report_is_deterministic():
    profile = PilotProfile(
        name="홍길동", age=25, logged_flight_hours=12.0,
        completed_sim_modes=("tutorial_basics", "manual_flight"),
    )
    r1 = build_report(10.0, profile)
    r2 = build_report(10.0, profile)
    assert r1 == r2
    assert r1["assessment"]["required_grade"] == 2


def test_export_json_roundtrip_stable():
    profile = PilotProfile(name="홍길동", age=25, logged_flight_hours=12.0)
    report = build_report(10.0, profile)
    j1 = export_json(report)
    j2 = export_json(report)
    assert j1 == j2
    assert json.loads(j1)["form_type"] == "pilot_certification_assessment"


def test_export_text_contains_grade_label():
    profile = PilotProfile(name="홍길동", age=25, logged_flight_hours=12.0)
    report = build_report(30.0, profile)
    text = export_text(report)
    assert "1종" in text
    assert "조종자 증명 자격 판정" in text
