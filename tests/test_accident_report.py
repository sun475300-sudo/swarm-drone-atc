"""Phase 307 (GENESIS): 사고 보고 양식 자동 작성 테스트.

ARAIB 표준 사고 보고서의 사건 분류·구성·검증·export 결정성을 검증한다.
"""

import json
from datetime import datetime

import pytest

from simulation.accident_report import (
    CONTACT_SEPARATION_M,
    NEAR_MISS_SEPARATION_M,
    DamageLevel,
    InvolvedDrone,
    OccurrenceCategory,
    OccurrenceRecord,
    build_report,
    classify_occurrence,
    export_json,
    export_text,
    occurrence_from_log,
)


def _drones() -> tuple[InvolvedDrone, ...]:
    return (
        InvolvedDrone("d1", "SDACS-Quad-X", "동강대 SDACS팀", "UAS-2026-0001"),
        InvolvedDrone("d2", "SDACS-Quad-X", "동강대 SDACS팀", ""),
    )


def _record(**kwargs) -> OccurrenceRecord:
    base = dict(
        occurrence_id="OCC-001",
        timestamp=datetime(2026, 7, 1, 14, 30),
        lat=34.79,
        lon=126.39,
        altitude_m=80.0,
        drones=_drones(),
        min_separation_m=50.0,
    )
    base.update(kwargs)
    return OccurrenceRecord(**base)


# ── 분류 로직 ─────────────────────────────────────────────


def test_contact_is_classified_as_accident():
    decision = classify_occurrence(_record(min_separation_m=2.0))

    assert decision.category is OccurrenceCategory.ACCIDENT
    assert decision.is_reportable is True
    assert any("충돌" in r for r in decision.reasons)


def test_explicit_contact_flag_forces_accident():
    decision = classify_occurrence(
        _record(min_separation_m=40.0, made_contact=True)
    )

    assert decision.category is OccurrenceCategory.ACCIDENT


def test_injuries_force_accident():
    decision = classify_occurrence(_record(min_separation_m=40.0, injuries=1))

    assert decision.category is OccurrenceCategory.ACCIDENT
    assert any("인명" in r for r in decision.reasons)


def test_substantial_damage_forces_accident():
    decision = classify_occurrence(
        _record(min_separation_m=40.0, damage=DamageLevel.SUBSTANTIAL)
    )

    assert decision.category is OccurrenceCategory.ACCIDENT


def test_near_miss_is_serious_incident():
    decision = classify_occurrence(_record(min_separation_m=8.0))

    assert decision.category is OccurrenceCategory.SERIOUS_INCIDENT
    assert decision.is_reportable is True


def test_wide_separation_is_safety_occurrence():
    decision = classify_occurrence(_record(min_separation_m=40.0))

    assert decision.category is OccurrenceCategory.SAFETY_OCCURRENCE
    assert decision.is_reportable is False


def test_exact_near_miss_threshold_is_not_serious_incident():
    # 정확히 10 m는 미만(<)이 아니므로 준사고가 아님
    decision = classify_occurrence(_record(min_separation_m=NEAR_MISS_SEPARATION_M))

    assert decision.category is OccurrenceCategory.SAFETY_OCCURRENCE


def test_exact_contact_threshold_is_accident():
    # 정확히 5 m는 이하(<=)이므로 충돌(사고)
    decision = classify_occurrence(_record(min_separation_m=CONTACT_SEPARATION_M))

    assert decision.category is OccurrenceCategory.ACCIDENT


# ── 로그 → 기록 변환 ──────────────────────────────────────


def test_occurrence_from_log_derives_min_and_contact():
    record = occurrence_from_log(
        "OCC-LOG", datetime(2026, 7, 1, 10, 0), 34.8, 126.4, 60.0,
        _drones(), separation_log=[30.0, 12.0, 3.5, 18.0],
    )

    assert record.min_separation_m == 3.5
    assert record.made_contact is True


def test_occurrence_from_log_empty_raises():
    with pytest.raises(ValueError, match="분리거리 로그"):
        occurrence_from_log(
            "OCC", datetime(2026, 7, 1), 0.0, 0.0, 0.0, _drones(),
            separation_log=[],
        )


# ── 보고서 생성 / 검증 ────────────────────────────────────


def test_build_report_structure_and_determinism():
    first = build_report(_record(min_separation_m=2.0), reporter="관제 시스템")
    second = build_report(_record(min_separation_m=2.0), reporter="관제 시스템")

    assert first == second  # 결정성
    assert first["form_type"] == "araib_occurrence_report"
    assert first["report_no"] == "SDACS-OCC-001"
    assert first["classification"]["category"] == "초경량비행장치사고"


def test_build_report_custom_report_no():
    report = build_report(
        _record(), reporter="관제 시스템", report_no="ARAIB-2026-07"
    )

    assert report["report_no"] == "ARAIB-2026-07"


def test_missing_registration_shows_placeholder():
    report = build_report(_record(), reporter="관제 시스템")

    regs = [d["registration_no"] for d in report["involved"]]
    assert "(미신고)" in regs


def test_empty_reporter_raises():
    with pytest.raises(ValueError, match="보고자"):
        build_report(_record(), reporter="")


def test_no_drones_raises():
    with pytest.raises(ValueError, match="관련 기체"):
        build_report(_record(drones=()), reporter="관제 시스템")


def test_negative_injuries_raises():
    with pytest.raises(ValueError, match="인명 피해"):
        build_report(_record(injuries=-1), reporter="관제 시스템")


def test_accident_includes_layer4_recommendation():
    report = build_report(_record(min_separation_m=2.0), reporter="관제 시스템")

    assert any("Layer 4" in r for r in report["recommendations"])


# ── export ────────────────────────────────────────────────


def test_export_json_roundtrip():
    report = build_report(_record(min_separation_m=2.0), reporter="관제 시스템")

    parsed = json.loads(export_json(report))

    assert parsed == report


def test_export_text_contains_key_fields():
    record = _record(
        min_separation_m=2.0,
        narrative="순항 중 경로 교차로 충돌",
        sequence=("t=14.0 분리 12 m", "t=15.0 충돌"),
        contributing_factors=("CPA 예측 지연",),
    )
    report = build_report(record, reporter="관제 시스템")

    text = export_text(report)

    assert "ARAIB" in text
    assert "초경량비행장치사고" in text
    assert "보고 의무: 대상" in text
    assert "CPA 예측 지연" in text
