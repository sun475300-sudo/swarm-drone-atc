"""Phase 310 (GENESIS): 야간·비가시 특별비행승인 안전기준 검증 테스트.

특별비행 안전기준의 항목별 판정·종합 승인 판정·검증·export 결정성을 검증한다.
"""

import json

import pytest

from simulation.special_flight_approval import (
    SAFETY_STANDARD,
    ApprovalAssessment,
    OperationPlan,
    SafetyEquipment,
    assess_special_flight,
    build_report,
    export_json,
    export_text,
)


def _full_equipment() -> SafetyEquipment:
    """모든 안전 장비를 구비한 기체."""
    return SafetyEquipment(
        anti_collision_light=True,
        nav_lights=True,
        autonomous_flight_termination=True,
        return_to_home=True,
        detect_and_avoid=True,
        dual_comms_link=True,
        dual_gnss=True,
        geofence=True,
        ir_camera=True,
        takeoff_landing_lighting=True,
    )


def _full_night_plan() -> OperationPlan:
    return OperationPlan(
        is_night=True,
        ground_observers=1,
        pilot_certified=True,
        insured=True,
        flight_distance_km=0.5,
    )


def _full_bvlos_plan() -> OperationPlan:
    return OperationPlan(
        is_bvlos=True,
        ground_observers=1,
        emergency_landing_sites=2,
        pilot_certified=True,
        insured=True,
        flight_distance_km=5.0,
    )


# ── 종합 판정 ──────────────────────────────────────────────────────────


def test_night_with_full_equipment_is_approvable():
    result = assess_special_flight(_full_night_plan(), _full_equipment())
    assert result.approvable is True
    assert result.deficiencies == ()


def test_bvlos_with_full_equipment_is_approvable():
    result = assess_special_flight(_full_bvlos_plan(), _full_equipment())
    assert result.approvable is True


def test_night_and_bvlos_combined_includes_all_categories():
    plan = OperationPlan(
        is_night=True,
        is_bvlos=True,
        ground_observers=1,
        emergency_landing_sites=1,
        pilot_certified=True,
        insured=True,
    )
    result = assess_special_flight(plan, _full_equipment())
    categories = {r.category for r in result.requirements}
    assert categories == {"공통", "야간", "비가시"}
    assert result.approvable is True


def test_neither_night_nor_bvlos_is_not_special_flight():
    plan = OperationPlan(pilot_certified=True, insured=True)
    result = assess_special_flight(plan, _full_equipment())
    assert result.approvable is False
    assert result.requirements == ()
    assert "특별비행" in result.deficiencies[0]


# ── 공통 안전기준 항목별 미충족 ────────────────────────────────────────


@pytest.mark.parametrize(
    "field",
    [
        "anti_collision_light",
        "return_to_home",
        "geofence",
        "autonomous_flight_termination",
    ],
)
def test_missing_common_equipment_blocks_approval(field):
    equip = _full_equipment()
    equip = SafetyEquipment(**{**equip.__dict__, field: False})
    result = assess_special_flight(_full_night_plan(), equip)
    assert result.approvable is False
    assert any("공통" == r.category and not r.satisfied for r in result.requirements)


def test_missing_certification_or_insurance_blocks_approval():
    plan = OperationPlan(
        is_night=True, ground_observers=1, pilot_certified=True, insured=False
    )
    result = assess_special_flight(plan, _full_equipment())
    assert result.approvable is False
    assert any(r.code == "SA-C5" and not r.satisfied for r in result.requirements)


# ── 야간 안전기준 ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "field", ["nav_lights", "takeoff_landing_lighting", "ir_camera"]
)
def test_missing_night_equipment_blocks_approval(field):
    equip = SafetyEquipment(**{**_full_equipment().__dict__, field: False})
    result = assess_special_flight(_full_night_plan(), equip)
    assert result.approvable is False


def test_night_requires_ground_observer():
    plan = OperationPlan(
        is_night=True, ground_observers=0, pilot_certified=True, insured=True
    )
    result = assess_special_flight(plan, _full_equipment())
    assert result.approvable is False
    assert any(r.code == "SA-N4" and not r.satisfied for r in result.requirements)


def test_night_only_does_not_include_bvlos_requirements():
    result = assess_special_flight(_full_night_plan(), _full_equipment())
    codes = {r.code for r in result.requirements}
    assert not any(c.startswith("SA-B") for c in codes)


# ── 비가시 안전기준 ────────────────────────────────────────────────────


def test_bvlos_daa_satisfies_without_observer():
    plan = OperationPlan(
        is_bvlos=True,
        ground_observers=0,
        emergency_landing_sites=1,
        pilot_certified=True,
        insured=True,
    )
    result = assess_special_flight(plan, _full_equipment())
    sa_b1 = next(r for r in result.requirements if r.code == "SA-B1")
    assert sa_b1.satisfied is True
    assert result.approvable is True


def test_bvlos_observer_satisfies_without_daa():
    equip = SafetyEquipment(**{**_full_equipment().__dict__, "detect_and_avoid": False})
    plan = OperationPlan(
        is_bvlos=True,
        ground_observers=1,
        emergency_landing_sites=1,
        pilot_certified=True,
        insured=True,
    )
    result = assess_special_flight(plan, equip)
    sa_b1 = next(r for r in result.requirements if r.code == "SA-B1")
    assert sa_b1.satisfied is True


def test_bvlos_without_daa_or_observer_fails():
    equip = SafetyEquipment(**{**_full_equipment().__dict__, "detect_and_avoid": False})
    plan = OperationPlan(
        is_bvlos=True,
        ground_observers=0,
        emergency_landing_sites=1,
        pilot_certified=True,
        insured=True,
    )
    result = assess_special_flight(plan, equip)
    assert result.approvable is False
    assert any(r.code == "SA-B1" and not r.satisfied for r in result.requirements)


def test_bvlos_requires_emergency_landing_site():
    plan = OperationPlan(
        is_bvlos=True,
        ground_observers=1,
        emergency_landing_sites=0,
        pilot_certified=True,
        insured=True,
    )
    result = assess_special_flight(plan, _full_equipment())
    assert any(r.code == "SA-B4" and not r.satisfied for r in result.requirements)


# ── 입력 검증 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ground_observers": -1},
        {"emergency_landing_sites": -1},
        {"flight_distance_km": -0.1},
    ],
)
def test_invalid_plan_raises(kwargs):
    plan = OperationPlan(is_night=True, **kwargs)
    with pytest.raises(ValueError):
        assess_special_flight(plan, _full_equipment())


# ── 보고서 / export ────────────────────────────────────────────────────


def test_build_report_counts_and_standard():
    report = build_report(_full_night_plan(), _full_equipment())
    assert report["standard"] == SAFETY_STANDARD
    assert report["flight_types"] == ["야간"]
    asm = report["assessment"]
    assert asm["approvable"] is True
    assert asm["satisfied_count"] == asm["total_count"]


def test_export_json_is_deterministic_and_parsable():
    report = build_report(_full_bvlos_plan(), _full_equipment())
    a = export_json(report)
    b = export_json(report)
    assert a == b
    parsed = json.loads(a)
    assert parsed["assessment"]["approvable"] is True


def test_export_text_lists_deficiencies():
    plan = OperationPlan(
        is_night=True, ground_observers=0, pilot_certified=True, insured=True
    )
    report = build_report(plan, _full_equipment())
    text = export_text(report)
    assert "특별비행승인 안전기준 검증 보고서" in text
    assert "SA-N4" in text
    assert "승인 가능: 아니오" in text


def test_assessment_is_immutable_dataclass():
    result = assess_special_flight(_full_night_plan(), _full_equipment())
    assert isinstance(result, ApprovalAssessment)
    with pytest.raises(Exception):
        result.approvable = False  # type: ignore[misc]
