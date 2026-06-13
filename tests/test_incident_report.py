"""사고 보고서 자동 생성 모듈 테스트 (GENESIS Phase 307).

시뮬레이션 분석 이벤트를 항철위(ARAIB) 사건 등급으로 분류하고 보고서 초안을
생성하는 ``simulation.incident_report`` 모듈을 검증한다.
"""
from __future__ import annotations

from simulation.incident_report import (
    IncidentCategory,
    build_incident_report,
    classify_event,
)


# ── 분류 ────────────────────────────────────────────────────────


def test_collision_classified_as_accident():
    # Arrange / Act / Assert
    assert classify_event("COLLISION") is IncidentCategory.ACCIDENT


def test_near_miss_classified_as_serious_incident():
    assert classify_event("NEAR_MISS") is IncidentCategory.SERIOUS_INCIDENT


def test_failure_classified_as_safety_occurrence():
    assert classify_event("FAILURE_INJECTED") is IncidentCategory.SAFETY_OCCURRENCE
    assert classify_event("COMMS_LOSS_INJECTED") is IncidentCategory.SAFETY_OCCURRENCE


def test_routine_event_not_reportable():
    # CONFLICT/ADVISORY 등 정상 운영 이벤트는 보고 대상이 아니다.
    assert classify_event("CONFLICT") is None
    assert classify_event("ADVISORY_ISSUED") is None


# ── 보고서 빌드 ──────────────────────────────────────────────────


def _sample_events() -> list[dict]:
    return [
        {"type": "CONFLICT", "t": 1.0, "drone_a": "D1", "drone_b": "D2"},
        {
            "type": "COLLISION",
            "t": 12.5,
            "drone_a": "D3",
            "drone_b": "D4",
            "dist_m": 3.2,
            "phase_a": "ENROUTE",
            "phase_b": "ENROUTE",
            "alt_a_m": 60.0,
            "alt_b_m": 58.0,
        },
        {"type": "NEAR_MISS", "t": 8.0, "drone_a": "D1", "drone_b": "D5", "dist_m": 7.4},
        {"type": "FAILURE_INJECTED", "t": 30.0, "drone_id": "D7", "failure_type": "MOTOR_FAILURE"},
        {"type": "COMMS_LOSS_INJECTED", "t": 45.0, "drone_id": "D2"},
    ]


def test_report_filters_non_reportable_events():
    report = build_incident_report(_sample_events())
    # CONFLICT 제외 → 보고 대상 4건
    assert len(report.records) == 4
    assert all(r.event_type != "CONFLICT" for r in report.records)


def test_report_records_sorted_by_time_with_sequence():
    report = build_incident_report(_sample_events())
    times = [r.time_s for r in report.records]
    assert times == sorted(times)
    assert [r.sequence for r in report.records] == [1, 2, 3, 4]


def test_category_counts():
    report = build_incident_report(_sample_events())
    counts = report.category_counts
    assert counts[IncidentCategory.ACCIDENT] == 1
    assert counts[IncidentCategory.SERIOUS_INCIDENT] == 1
    assert counts[IncidentCategory.SAFETY_OCCURRENCE] == 2


def test_collision_summary_includes_separation_and_phase():
    report = build_incident_report(_sample_events())
    collision = next(r for r in report.records if r.event_type == "COLLISION")
    assert collision.involved == ("D3", "D4")
    assert "3.2" in collision.summary
    assert "ENROUTE" in collision.summary


def test_failure_summary_includes_failure_type():
    report = build_incident_report(_sample_events())
    failure = next(r for r in report.records if r.event_type == "FAILURE_INJECTED")
    assert failure.involved == ("D7",)
    assert "MOTOR_FAILURE" in failure.summary


def test_empty_events_yield_zero_records():
    report = build_incident_report([])
    assert report.records == ()
    assert report.category_counts[IncidentCategory.ACCIDENT] == 0


# ── 직렬화 ──────────────────────────────────────────────────────


def test_to_dict_roundtrip_fields():
    report = build_incident_report(
        _sample_events(), scenario="high_density", seed=42, duration_s=60.0
    )
    d = report.to_dict()
    assert d["scenario"] == "high_density"
    assert d["seed"] == 42
    assert d["duration_s"] == 60.0
    assert len(d["records"]) == 4
    assert d["category_counts"]["항공기사고"] == 1


def test_to_markdown_contains_metadata_and_categories():
    report = build_incident_report(
        _sample_events(), scenario="high_density", seed=42, duration_s=60.0
    )
    md = report.to_markdown()
    assert "high_density" in md
    assert "항공기사고" in md
    assert "항공기준사고" in md
    assert "항공안전장애" in md
    # 충돌 관련 드론이 표에 포함
    assert "D3" in md and "D4" in md
    # 시뮬레이션 초안 면책 고지 포함
    assert "초안" in md


def test_to_markdown_empty_report_states_no_incident():
    report = build_incident_report([])
    md = report.to_markdown()
    assert "보고 대상 사건 없음" in md
