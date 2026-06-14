"""ODYSSEY Phase 467 — 사고 조사 데이터 표준 변환기.

시뮬 안전 사건 로그가 ICAO Annex 13 구조 표준 양식으로 결정적으로 변환되는지,
사건 등급 분류·검증·export·결정성을 검증한다.
"""

from __future__ import annotations

import json

import pytest

from simulation.incident_investigation_report import (
    CLASS_ACCIDENT,
    CLASS_INCIDENT,
    CLASS_SERIOUS_INCIDENT,
    SERIOUS_SEPARATION_M,
    OperationMeta,
    SafetyOccurrence,
    build_investigation_report,
    classify_occurrence,
    export_json,
    export_text,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        operation_id="OP-2026-001",
        location="목포 해역",
        date="2026-06-14",
        drone_count=12,
        scenario="high_density",
    )


# ─── 분류 (classify_occurrence) ──────────────────────────────────────────────


def test_collision_classified_as_accident():
    occ = SafetyOccurrence("E1", t=10.0, occurrence_type="COLLISION", drone_ids=("D1", "D2"))
    result = classify_occurrence(occ)
    assert result.occurrence_class == CLASS_ACCIDENT
    assert result.category_code == "MAC"


def test_near_miss_below_threshold_is_serious_incident():
    occ = SafetyOccurrence("E2", t=5.0, occurrence_type="NEAR_MISS", separation_m=2.0)
    result = classify_occurrence(occ)
    assert result.occurrence_class == CLASS_SERIOUS_INCIDENT


def test_near_miss_above_threshold_downgrades_to_incident():
    occ = SafetyOccurrence(
        "E3", t=5.0, occurrence_type="NEAR_MISS", separation_m=SERIOUS_SEPARATION_M + 1.0
    )
    result = classify_occurrence(occ)
    assert result.occurrence_class == CLASS_INCIDENT


def test_conflict_classified_as_incident():
    occ = SafetyOccurrence("E4", t=3.0, occurrence_type="CONFLICT")
    assert classify_occurrence(occ).occurrence_class == CLASS_INCIDENT


def test_motor_failure_is_serious_incident_with_powerplant_code():
    occ = SafetyOccurrence("E5", t=7.0, occurrence_type="MOTOR_FAILURE", drone_ids=("D3",))
    result = classify_occurrence(occ)
    assert result.occurrence_class == CLASS_SERIOUS_INCIDENT
    assert result.category_code == "SCF-PP"


def test_gps_loss_uses_non_powerplant_code():
    occ = SafetyOccurrence("E6", t=8.0, occurrence_type="GPS_LOSS", drone_ids=("D4",))
    assert classify_occurrence(occ).category_code == "SCF-NP"


def test_nfz_intrusion_is_incident_airspace():
    occ = SafetyOccurrence("E7", t=9.0, occurrence_type="NFZ_INTRUSION", drone_ids=("D5",))
    result = classify_occurrence(occ)
    assert result.occurrence_class == CLASS_INCIDENT
    assert result.category_code == "AIRSPACE"


def test_battery_critical_and_comm_loss_codes():
    bat = classify_occurrence(SafetyOccurrence("B1", t=1.0, occurrence_type="BATTERY_CRITICAL"))
    comm = classify_occurrence(SafetyOccurrence("C1", t=1.0, occurrence_type="COMM_LOSS"))
    assert bat.category_code == "SCF-PP"
    assert bat.occurrence_class == CLASS_SERIOUS_INCIDENT
    assert comm.category_code == "SCF-NP"
    assert comm.occurrence_class == CLASS_SERIOUS_INCIDENT


def test_near_miss_at_exact_threshold_is_incident():
    occ = SafetyOccurrence("E8", t=1.0, occurrence_type="NEAR_MISS", separation_m=SERIOUS_SEPARATION_M)
    assert classify_occurrence(occ).occurrence_class == CLASS_INCIDENT


def test_near_miss_without_separation_keeps_serious_and_records_finding():
    occ = SafetyOccurrence("E9", t=1.0, occurrence_type="NEAR_MISS")
    result = classify_occurrence(occ)
    assert result.occurrence_class == CLASS_SERIOUS_INCIDENT
    assert any("미측정" in f for f in result.findings)


def test_classify_unknown_type_raises_directly():
    with pytest.raises(ValueError, match="알 수 없는 사건 유형"):
        classify_occurrence(SafetyOccurrence("E0", t=1.0, occurrence_type="BOGUS"))


# ─── 보고서 구성 (build_investigation_report) ────────────────────────────────


def test_overall_classification_takes_most_severe():
    occurrences = [
        SafetyOccurrence("E1", t=1.0, occurrence_type="CONFLICT"),
        SafetyOccurrence("E2", t=2.0, occurrence_type="COLLISION", drone_ids=("D1", "D2")),
        SafetyOccurrence("E3", t=3.0, occurrence_type="NFZ_INTRUSION"),
    ]
    report = build_investigation_report(occurrences, _meta())
    assert report["occurrence_classification"] == CLASS_ACCIDENT
    assert report["standard"] == "ICAO Annex 13"


def test_factual_information_sorted_by_time():
    occurrences = [
        SafetyOccurrence("E2", t=5.0, occurrence_type="CONFLICT"),
        SafetyOccurrence("E1", t=1.0, occurrence_type="CONFLICT"),
        SafetyOccurrence("E3", t=3.0, occurrence_type="CONFLICT"),
    ]
    report = build_investigation_report(occurrences, _meta())
    times = [f["t"] for f in report["factual_information"]]
    assert times == [1.0, 3.0, 5.0]


def test_analysis_counts_by_category_and_classification():
    occurrences = [
        SafetyOccurrence("E1", t=1.0, occurrence_type="CONFLICT"),
        SafetyOccurrence("E2", t=2.0, occurrence_type="CONFLICT"),
        SafetyOccurrence("E3", t=3.0, occurrence_type="MOTOR_FAILURE", drone_ids=("D1",)),
    ]
    report = build_investigation_report(occurrences, _meta())
    assert report["analysis"]["total_occurrences"] == 3
    assert report["analysis"]["by_category"]["MAC"] == 2
    assert report["analysis"]["by_category"]["SCF-PP"] == 1
    assert report["analysis"]["by_classification"][CLASS_INCIDENT] == 2
    assert report["analysis"]["by_classification"][CLASS_SERIOUS_INCIDENT] == 1


def test_safety_recommendations_deduplicated_and_sorted():
    occurrences = [
        SafetyOccurrence("E1", t=1.0, occurrence_type="CONFLICT"),
        SafetyOccurrence("E2", t=2.0, occurrence_type="NEAR_MISS", separation_m=1.0),
        SafetyOccurrence("E3", t=3.0, occurrence_type="NFZ_INTRUSION"),
    ]
    report = build_investigation_report(occurrences, _meta())
    recs = report["safety_recommendations"]
    # MAC + AIRSPACE 코드 → 권고 2건 (MAC 중복 제거), 코드 사전순(AIRSPACE < MAC)
    assert len(recs) == 2
    assert "지오펜스" in recs[0]


# ─── 검증 (ValueError) ───────────────────────────────────────────────────────


def test_empty_occurrences_raises():
    with pytest.raises(ValueError, match="사건 목록이 비어 있음"):
        build_investigation_report([], _meta())


def test_unknown_occurrence_type_raises():
    occ = [SafetyOccurrence("E1", t=1.0, occurrence_type="UNKNOWN")]
    with pytest.raises(ValueError, match="알 수 없는 사건 유형"):
        build_investigation_report(occ, _meta())


def test_duplicate_occurrence_id_raises():
    occ = [
        SafetyOccurrence("E1", t=1.0, occurrence_type="CONFLICT"),
        SafetyOccurrence("E1", t=2.0, occurrence_type="CONFLICT"),
    ]
    with pytest.raises(ValueError, match="사건 식별자 중복"):
        build_investigation_report(occ, _meta())


def test_negative_time_raises():
    occ = [SafetyOccurrence("E1", t=-1.0, occurrence_type="CONFLICT")]
    with pytest.raises(ValueError, match="음수일 수 없음"):
        build_investigation_report(occ, _meta())


def test_empty_occurrence_id_raises():
    occ = [SafetyOccurrence("", t=1.0, occurrence_type="CONFLICT")]
    with pytest.raises(ValueError, match="사건 식별자.*비어 있음"):
        build_investigation_report(occ, _meta())


def test_by_classification_reflects_near_miss_downgrade():
    occ = [
        SafetyOccurrence("E1", t=1.0, occurrence_type="NEAR_MISS", separation_m=8.0),
        SafetyOccurrence("E2", t=2.0, occurrence_type="NEAR_MISS", separation_m=1.0),
    ]
    report = build_investigation_report(occ, _meta())
    assert report["analysis"]["by_classification"][CLASS_INCIDENT] == 1
    assert report["analysis"]["by_classification"][CLASS_SERIOUS_INCIDENT] == 1
    assert report["occurrence_classification"] == CLASS_SERIOUS_INCIDENT


def test_zero_drone_count_raises():
    meta = OperationMeta(operation_id="OP", location="x", date="2026-06-14", drone_count=0)
    occ = [SafetyOccurrence("E1", t=1.0, occurrence_type="CONFLICT")]
    with pytest.raises(ValueError, match="드론 수는 0보다 커야 함"):
        build_investigation_report(occ, meta)


# ─── export ──────────────────────────────────────────────────────────────────


def test_export_json_roundtrip():
    occ = [SafetyOccurrence("E1", t=1.0, occurrence_type="COLLISION", drone_ids=("D1", "D2"))]
    report = build_investigation_report(occ, _meta())
    parsed = json.loads(export_json(report))
    assert parsed["occurrence_classification"] == CLASS_ACCIDENT
    assert parsed["operation"]["operation_id"] == "OP-2026-001"


def test_export_text_contains_key_sections():
    occ = [SafetyOccurrence("E1", t=1.5, occurrence_type="NEAR_MISS", separation_m=2.0)]
    text = export_text(build_investigation_report(occ, _meta()))
    assert "ICAO Annex 13 사고 조사 보고서" in text
    assert "준사고(Serious Incident)" in text
    assert "안전 권고" in text


def test_report_is_deterministic():
    occ = [
        SafetyOccurrence("E2", t=2.0, occurrence_type="MOTOR_FAILURE", drone_ids=("D1",)),
        SafetyOccurrence("E1", t=1.0, occurrence_type="NEAR_MISS", separation_m=1.0),
    ]
    first = export_json(build_investigation_report(occ, _meta()))
    second = export_json(build_investigation_report(occ, _meta()))
    assert first == second
