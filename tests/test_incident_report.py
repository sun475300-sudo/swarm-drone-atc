"""GENESIS 307 + ODYSSEY 467 — 사고 보고 양식 / 사고조사 데이터 표준 테스트."""
import pytest

from simulation.incident_report import (
    Incident,
    accident_report,
    extract_incidents,
    investigation_dataset,
    to_investigation_record,
)

pytestmark = pytest.mark.unit


SAMPLE_LOG = [
    {"t": 0.0, "type": "conflict_detected"},
    {"t": 1.0, "type": "conflict_resolved"},
    {"t": 12.5, "type": "near_miss", "drone_a": "D1", "drone_b": "D2",
     "separation_m": 3.2},
    {"t": 30.0, "type": "collision", "drone_a": "D3", "drone_b": "D4"},
    {"t": 45.0, "type": "battery_depleted", "drone_id": "D5"},
    {"t": 50.0, "type": "trajectory_logged"},  # 사고 아님
]


class TestExtractIncidents:
    def test_filters_only_incident_events(self):
        incidents = extract_incidents(SAMPLE_LOG)
        types = [i.event_type for i in incidents]
        assert "collision" in types
        assert "near_miss" in types
        assert "battery_depleted" in types
        # 충돌 비사고 이벤트는 제외
        assert "conflict_detected" not in types
        assert "trajectory_logged" not in types

    def test_sorted_by_time(self):
        incidents = extract_incidents(SAMPLE_LOG)
        times = [i.time_s for i in incidents]
        assert times == sorted(times)

    def test_severity_classification(self):
        incidents = {i.event_type: i for i in extract_incidents(SAMPLE_LOG)}
        assert incidents["collision"].severity == "accident"
        assert incidents["near_miss"].severity == "serious_incident"
        assert incidents["battery_depleted"].severity == "incident"

    def test_involved_drones_captured(self):
        incidents = {i.event_type: i for i in extract_incidents(SAMPLE_LOG)}
        assert set(incidents["collision"].drones) == {"D3", "D4"}
        assert incidents["battery_depleted"].drones == ("D5",)

    def test_empty_log_returns_empty(self):
        assert extract_incidents([]) == []


class TestInvestigationRecord:
    def test_standard_schema_fields(self):
        inc = extract_incidents(SAMPLE_LOG)[0]  # near_miss @12.5
        rec = to_investigation_record(inc, sim_id="run42")
        assert rec["schema"] == "sdacs.incident.v1"
        assert rec["sim_id"] == "run42"
        assert rec["occurrence_class"] == inc.severity
        assert rec["event_type"] == inc.event_type
        assert rec["time_offset_s"] == inc.time_s
        assert isinstance(rec["involved_uas"], list)

    def test_deterministic_occurrence_id(self):
        inc = extract_incidents(SAMPLE_LOG)[0]
        a = to_investigation_record(inc, sim_id="run42")
        b = to_investigation_record(inc, sim_id="run42")
        assert a["occurrence_id"] == b["occurrence_id"]
        # sim_id 가 다르면 id 도 달라짐
        c = to_investigation_record(inc, sim_id="other")
        assert c["occurrence_id"] != a["occurrence_id"]

    def test_dataset_covers_all_incidents(self):
        ds = investigation_dataset(SAMPLE_LOG, sim_id="run42")
        assert len(ds) == 3
        assert all(r["schema"] == "sdacs.incident.v1" for r in ds)

    def test_record_is_json_serializable(self):
        import json
        ds = investigation_dataset(SAMPLE_LOG, sim_id="run42")
        # 직렬화 시 예외 없어야 함
        json.dumps(ds)


class TestAccidentReport:
    def test_report_lists_each_incident(self):
        report = accident_report(
            extract_incidents(SAMPLE_LOG), sim_id="run42", scenario="high_density"
        )
        assert "run42" in report
        assert "high_density" in report
        assert "D3" in report and "D4" in report  # 충돌 관련 기체
        assert "|" in report  # 마크다운 표

    def test_report_counts_by_severity(self):
        report = accident_report(extract_incidents(SAMPLE_LOG), sim_id="run42")
        # 사고 1 / 준사고 1 / 이벤트 1
        assert "사고" in report

    def test_no_incidents_states_clean(self):
        report = accident_report([], sim_id="clean_run")
        assert "clean_run" in report
        assert "없음" in report or "0" in report
