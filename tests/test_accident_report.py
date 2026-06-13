"""GENESIS Phase 307 — 사고 보고 양식(항철위/ARAIB 표준) 자동 작성 테스트.

근거: 항공안전법 §134(사고 보고) + 항공·철도 사고조사에 관한 법률.
시뮬레이션 장애 주입 로그(INJ Phase 6)를 표준 사고 보고 양식으로 변환.
"""
from __future__ import annotations

import pytest

from src.certification.accident_report import (
    EventType,
    IncidentEvent,
    Severity,
    Weather,
    build_accident_report,
    classify_severity,
    from_sim_log,
)


def _event(**overrides) -> IncidentEvent:
    base = dict(
        timestamp="2026-07-01T10:15:30",
        lat=37.5665,
        lon=126.9780,
        altitude_m=80.0,
        aircraft_id="SDACS-07",
        model="SDACS-Q4",
        event_type=EventType.MOTOR_FAIL,
        flight_phase="ENROUTE",
        deaths=0,
        injuries=0,
        property_damage_krw=0,
        weather=Weather(wind_mps=4.0, visibility_m=8000.0),
        narrative="순항 중 모터 1기 출력 저하.",
    )
    return IncidentEvent(**{**base, **overrides})


# ── 심각도 분류 ────────────────────────────────────────────

def test_death_classified_as_accident():
    event = _event(deaths=1, event_type=EventType.COLLISION)

    assert classify_severity(event) is Severity.ACCIDENT


def test_serious_injury_classified_as_accident():
    event = _event(injuries=1, event_type=EventType.COLLISION)

    assert classify_severity(event) is Severity.ACCIDENT


def test_collision_without_casualty_is_serious_incident():
    event = _event(event_type=EventType.COLLISION, deaths=0, injuries=0)

    assert classify_severity(event) is Severity.SERIOUS_INCIDENT


def test_minor_battery_event_is_incident():
    event = _event(event_type=EventType.BATTERY_CRITICAL)

    assert classify_severity(event) is Severity.INCIDENT


def test_high_property_damage_escalates_to_serious_incident():
    event = _event(event_type=EventType.GPS_LOSS, property_damage_krw=20_000_000)

    assert classify_severity(event) is Severity.SERIOUS_INCIDENT


def test_property_damage_at_threshold_stays_incident():
    # 1천만원 "초과"가 기준 — 정확히 1천만원은 경미한 사고.
    event = _event(event_type=EventType.GPS_LOSS, property_damage_krw=10_000_000)

    assert classify_severity(event) is Severity.INCIDENT


def test_nfz_violation_is_serious_incident():
    event = _event(event_type=EventType.NFZ_VIOLATION)

    assert classify_severity(event) is Severity.SERIOUS_INCIDENT


# ── 보고서 생성 ────────────────────────────────────────────

def test_report_contains_required_sections():
    report = build_accident_report(_event(deaths=1, event_type=EventType.COLLISION))
    form = report.to_dict()

    assert form["구분"] == Severity.ACCIDENT.value
    assert "발생개요" in form
    assert "기체정보" in form
    assert "피해상황" in form
    assert "기상" in form
    assert form["기체정보"]["신고부호"] == "SDACS-07"


def test_report_text_includes_araib_header():
    text = build_accident_report(_event()).to_text()

    assert "항공·철도사고조사위원회" in text
    assert "SDACS-07" in text


def test_accident_flags_immediate_report_obligation():
    report = build_accident_report(_event(deaths=1, event_type=EventType.COLLISION))

    assert report.immediate_report_required is True


def test_serious_incident_flags_immediate_report():
    # §134 ① — 준사고도 즉시 보고 대상 (사상자 없는 고가 손상).
    event = _event(event_type=EventType.MOTOR_FAIL, property_damage_krw=15_000_000)

    assert build_accident_report(event).immediate_report_required is True


def test_incident_does_not_flag_immediate_report():
    report = build_accident_report(_event(event_type=EventType.BATTERY_CRITICAL))

    assert report.immediate_report_required is False


def test_to_dict_is_json_serializable():
    import json

    report = build_accident_report(_event())
    dumped = json.dumps(report.to_dict(), ensure_ascii=False)

    assert "SDACS-Q4" in dumped


# ── 입력 검증 ─────────────────────────────────────────────

def test_negative_deaths_rejected():
    with pytest.raises(ValueError):
        _event(deaths=-1)


def test_visibility_negative_rejected():
    with pytest.raises(ValueError):
        Weather(wind_mps=2.0, visibility_m=-1.0)


def test_latitude_out_of_range_rejected():
    with pytest.raises(ValueError):
        _event(lat=999.0)


# ── 시뮬 로그 변환 ─────────────────────────────────────────

def test_from_sim_log_maps_records_to_events():
    log = [
        {
            "timestamp": "2026-07-01T10:00:00",
            "lat": 37.5,
            "lon": 127.0,
            "altitude_m": 60.0,
            "aircraft_id": "SDACS-01",
            "model": "SDACS-Q4",
            "event_type": "collision",
            "flight_phase": "ENROUTE",
        },
        {
            "timestamp": "2026-07-01T10:05:00",
            "lat": 37.6,
            "lon": 127.1,
            "altitude_m": 90.0,
            "aircraft_id": "SDACS-02",
            "model": "SDACS-Q4",
            "event_type": "battery_critical",
            "flight_phase": "RTB",
        },
    ]

    events = from_sim_log(log)

    assert len(events) == 2
    assert events[0].event_type is EventType.COLLISION
    assert events[1].event_type is EventType.BATTERY_CRITICAL


def test_from_sim_log_unknown_event_type_rejected():
    with pytest.raises(ValueError):
        from_sim_log([{"timestamp": "t", "event_type": "alien_abduction"}])
