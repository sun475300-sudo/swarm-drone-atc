"""Phase 307 (GENESIS): 사고 보고 양식 자동 작성 테스트.

ARAIB 표준 발생 보고서의 등급 분류·의무보고 판정·검증·export 의 결정성을 검증한다.
"""

import json
from datetime import datetime

import pytest

from simulation.incident_report import (
    ACCIDENT,
    OCCURRENCE,
    SERIOUS_INCIDENT,
    SUBSTANTIAL_DAMAGE_KRW,
    IncidentEvent,
    Operator,
    build_report,
    classify_occurrence,
    export_json,
    export_text,
    summarize_log,
)


def _operator() -> Operator:
    return Operator(
        name="장선우",
        contact="010-1234-5678",
        organization="SDACS 캡스톤팀",
    )


def _event(**kwargs) -> IncidentEvent:
    base = dict(
        timestamp=datetime(2026, 7, 1, 14, 30, 0),
        drone_id="D07",
        event_type="gps_loss",
        lat=34.79,
        lon=126.39,
        altitude_agl_m=80.0,
        description="목포 해역 순찰 중 GPS 신호 단절",
    )
    base.update(kwargs)
    return IncidentEvent(**base)


# ── 등급 분류 ─────────────────────────────────────────────


def test_gps_loss_is_occurrence():
    assessment = classify_occurrence(_event(event_type="gps_loss"))

    assert assessment.occurrence_class == OCCURRENCE
    assert assessment.is_mandatory_report is False
    assert assessment.report_deadline_h == 72


def test_collision_without_casualty_is_serious_incident():
    assessment = classify_occurrence(_event(event_type="collision"))

    assert assessment.occurrence_class == SERIOUS_INCIDENT
    assert assessment.is_mandatory_report is True
    assert assessment.report_deadline_h == 0


def test_casualty_escalates_to_accident():
    assessment = classify_occurrence(
        _event(event_type="collision", casualties=1)
    )

    assert assessment.occurrence_class == ACCIDENT
    assert any("인명 피해" in r for r in assessment.reasons)


def test_aircraft_destroyed_is_accident():
    assessment = classify_occurrence(
        _event(event_type="forced_landing", is_aircraft_destroyed=True)
    )

    assert assessment.occurrence_class == ACCIDENT
    assert any("기체 파괴" in r for r in assessment.reasons)


def test_substantial_property_damage_is_accident():
    assessment = classify_occurrence(
        _event(event_type="near_miss", property_damage_krw=SUBSTANTIAL_DAMAGE_KRW)
    )

    assert assessment.occurrence_class == ACCIDENT


def test_damage_below_threshold_not_accident():
    assessment = classify_occurrence(
        _event(event_type="near_miss", property_damage_krw=SUBSTANTIAL_DAMAGE_KRW - 1)
    )

    assert assessment.occurrence_class == OCCURRENCE


def test_loss_of_control_unrecovered_is_serious():
    assessment = classify_occurrence(
        _event(event_type="loss_of_control", recovered=False)
    )

    assert assessment.occurrence_class == SERIOUS_INCIDENT
    assert any("미복구" in r for r in assessment.reasons)


def test_loss_of_control_recovered_is_occurrence():
    assessment = classify_occurrence(
        _event(event_type="loss_of_control", recovered=True)
    )

    assert assessment.occurrence_class == OCCURRENCE
    assert any("안전망 복구" in r for r in assessment.reasons)


def test_comm_loss_is_occurrence():
    assessment = classify_occurrence(_event(event_type="comm_loss"))

    assert assessment.occurrence_class == OCCURRENCE


# ── 보고서 생성 / 검증 ────────────────────────────────────


def test_build_report_structure_and_determinism():
    args = (_event(event_type="collision"), _operator())

    first = build_report(*args)
    second = build_report(*args)

    assert first == second  # 결정성
    assert first["form_type"] == "araib_occurrence_report"
    assert first["report_no"] == "ARAIB-20260701-143000-D07"
    assert first["assessment"]["occurrence_class"] == SERIOUS_INCIDENT


def test_unknown_event_type_raises():
    with pytest.raises(ValueError, match="이벤트 유형"):
        build_report(_event(event_type="meteor_strike"), _operator())


def test_negative_casualties_raises():
    with pytest.raises(ValueError, match="인명 피해"):
        build_report(_event(casualties=-1), _operator())


def test_missing_operator_contact_raises():
    bad_operator = Operator(name="장선우", contact="")

    with pytest.raises(ValueError, match="연락처"):
        build_report(_event(), bad_operator)


def test_empty_drone_id_raises():
    with pytest.raises(ValueError, match="기체 ID"):
        build_report(_event(drone_id=""), _operator())


# ── 로그 집계 ─────────────────────────────────────────────


def test_summarize_log_counts_by_class():
    events = [
        _event(event_type="gps_loss"),
        _event(event_type="collision"),
        _event(event_type="collision", casualties=2),
        _event(event_type="comm_loss"),
    ]

    summary = summarize_log(events)

    assert summary["total"] == 4
    assert summary["by_class"][ACCIDENT] == 1
    assert summary["by_class"][SERIOUS_INCIDENT] == 1
    assert summary["by_class"][OCCURRENCE] == 2
    assert summary["mandatory_reports"] == 2


def test_summarize_empty_log():
    summary = summarize_log([])

    assert summary["total"] == 0
    assert summary["mandatory_reports"] == 0


# ── export ────────────────────────────────────────────────


def test_export_json_roundtrip():
    report = build_report(_event(event_type="collision"), _operator())

    parsed = json.loads(export_json(report))

    assert parsed == report


def test_export_text_contains_key_fields():
    report = build_report(
        _event(event_type="collision", casualties=1), _operator()
    )

    text = export_text(report)

    assert "ARAIB" in text
    assert "장선우" in text
    assert "발생 등급: 사고" in text
    assert "의무보고:  대상" in text
    assert "인지 즉시" in text


def test_export_text_occurrence_shows_deadline_hours():
    report = build_report(_event(event_type="gps_loss"), _operator())

    text = export_text(report)

    assert "72시간 이내" in text
