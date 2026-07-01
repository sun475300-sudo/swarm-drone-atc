"""ODYSSEY Phase 488 — CVE 대응 SLA + 핀 갱신 정책 단위 테스트.

`simulation/cve_response_policy.py` 의 결정성·SLA·핀 갱신·정직성 결속 검증.
"""
from __future__ import annotations

import pytest

from simulation.cve_response_policy import (
    DECISION_MONITOR,
    DECISION_OUT_OF_SCOPE,
    DECISION_PATCH_NOW,
    DECISION_SCHEDULED,
    EXPOSURE_ARCHIVED,
    EXPOSURE_DEV,
    EXPOSURE_RUNTIME,
    POLICY_MATRIX,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_NONE,
    CveReport,
    assess,
    effective_severity,
    policy_manifest,
    severity_from_cvss,
)


# --- severity_from_cvss: CVSS v3.1 절단점 -----------------------------------

@pytest.mark.parametrize("score,expected", [
    (0.0, SEVERITY_NONE),
    (0.1, SEVERITY_LOW),
    (3.9, SEVERITY_LOW),
    (4.0, SEVERITY_MEDIUM),
    (6.9, SEVERITY_MEDIUM),
    (7.0, SEVERITY_HIGH),
    (8.9, SEVERITY_HIGH),
    (9.0, SEVERITY_CRITICAL),
    (10.0, SEVERITY_CRITICAL),
])
def test_severity_band_cutpoints(score, expected):
    # Arrange / Act / Assert
    assert severity_from_cvss(score) == expected


@pytest.mark.parametrize("bad", [-0.1, 10.1, 100.0])
def test_severity_rejects_out_of_range_score(bad):
    with pytest.raises(ValueError):
        severity_from_cvss(bad)


def test_severity_is_deterministic():
    assert severity_from_cvss(7.5) == severity_from_cvss(7.5)


# --- effective_severity: dev 한 단계 강등 -----------------------------------

def test_dev_demotes_one_band():
    assert effective_severity(SEVERITY_CRITICAL, EXPOSURE_DEV) == SEVERITY_HIGH
    assert effective_severity(SEVERITY_HIGH, EXPOSURE_DEV) == SEVERITY_MEDIUM
    assert effective_severity(SEVERITY_MEDIUM, EXPOSURE_DEV) == SEVERITY_LOW


def test_dev_demotion_floors_at_none():
    assert effective_severity(SEVERITY_LOW, EXPOSURE_DEV) == SEVERITY_NONE
    assert effective_severity(SEVERITY_NONE, EXPOSURE_DEV) == SEVERITY_NONE


def test_runtime_keeps_severity():
    for sev in (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW):
        assert effective_severity(sev, EXPOSURE_RUNTIME) == sev


# --- CveReport 입력 검증 ----------------------------------------------------

def test_report_severity_property():
    r = CveReport("CVE-1", "numpy", 9.8, EXPOSURE_RUNTIME, fixed_version="1.0.0")
    assert r.severity == SEVERITY_CRITICAL


def test_report_rejects_blank_id():
    with pytest.raises(ValueError):
        CveReport("  ", "numpy", 5.0, EXPOSURE_RUNTIME, fixed_version="1.0.0")


def test_report_rejects_blank_package():
    with pytest.raises(ValueError):
        CveReport("CVE-1", "", 5.0, EXPOSURE_RUNTIME, fixed_version="1.0.0")


def test_report_rejects_bad_cvss():
    with pytest.raises(ValueError):
        CveReport("CVE-1", "numpy", 11.0, EXPOSURE_RUNTIME, fixed_version="1.0")


def test_report_rejects_unknown_exposure():
    with pytest.raises(ValueError):
        CveReport("CVE-1", "numpy", 5.0, "transitive", fixed_version="1.0.0")


def test_report_requires_fixed_version_when_fix_available():
    with pytest.raises(ValueError):
        CveReport("CVE-1", "numpy", 5.0, EXPOSURE_RUNTIME, fix_available=True)


def test_report_forbids_fixed_version_when_no_fix():
    with pytest.raises(ValueError):
        CveReport("CVE-1", "numpy", 5.0, EXPOSURE_RUNTIME,
                  fix_available=False, fixed_version="1.0.0")


# --- assess: 결정 우선순위 --------------------------------------------------

def test_archived_is_out_of_scope_even_when_critical():
    r = CveReport("CVE-1", "old", 9.9, EXPOSURE_ARCHIVED, fixed_version="2.0")
    resp = assess(r)
    assert resp.decision == DECISION_OUT_OF_SCOPE
    assert resp.ack_days is None and resp.remediate_days is None
    assert resp.pin_refresh_required is False


def test_archived_out_of_scope_when_no_upstream_fix():
    r = CveReport("CVE-1", "old", 9.9, EXPOSURE_ARCHIVED, fix_available=False)
    resp = assess(r)
    assert resp.decision == DECISION_OUT_OF_SCOPE
    assert resp.pin_refresh_required is False


def test_report_treats_blank_fixed_version_as_absent_when_no_fix():
    # 대칭 규약: 공백/빈 문자열 fixed_version 은 "없음"(None 과 동치)으로 허용.
    # 실제 비공백 버전만 거부(test_report_forbids_fixed_version_when_no_fix).
    r = CveReport("CVE-1", "p", 5.0, EXPOSURE_RUNTIME,
                  fix_available=False, fixed_version="   ")
    assert r.fix_available is False


def test_none_severity_is_monitor():
    r = CveReport("CVE-1", "lib", 0.0, EXPOSURE_RUNTIME, fix_available=False)
    resp = assess(r)
    assert resp.decision == DECISION_MONITOR
    assert resp.remediate_days is None
    assert resp.pin_refresh_required is False


def test_critical_runtime_patch_now():
    r = CveReport("CVE-1", "numpy", 9.8, EXPOSURE_RUNTIME, fixed_version="1.0")
    resp = assess(r)
    assert resp.decision == DECISION_PATCH_NOW
    assert (resp.ack_days, resp.remediate_days) == (1, 7)
    assert resp.pin_refresh_required is True


def test_high_runtime_matches_security_md_baseline():
    # SECURITY.md: ack 7d / remediation 14d. HIGH 의 해결 14일이 상한과 일치.
    r = CveReport("CVE-1", "pyyaml", 7.5, EXPOSURE_RUNTIME, fixed_version="6.0.3")
    resp = assess(r)
    assert resp.decision == DECISION_PATCH_NOW
    assert (resp.ack_days, resp.remediate_days) == (3, 14)


def test_medium_runtime_scheduled():
    r = CveReport("CVE-1", "matplotlib", 5.3, EXPOSURE_RUNTIME,
                  fixed_version="3.10.9")
    resp = assess(r)
    assert resp.decision == DECISION_SCHEDULED
    assert (resp.ack_days, resp.remediate_days) == (7, 30)


def test_low_runtime_scheduled():
    r = CveReport("CVE-1", "lib", 2.0, EXPOSURE_RUNTIME, fixed_version="1.0")
    resp = assess(r)
    assert resp.decision == DECISION_SCHEDULED
    assert (resp.ack_days, resp.remediate_days) == (14, 90)


def test_low_dev_demotes_to_none_becomes_monitor():
    # LOW(2.0) dev → 유효 NONE → MONITOR, SLA 없음, 핀 갱신 없음.
    r = CveReport("CVE-1", "lib", 2.0, EXPOSURE_DEV, fixed_version="1.1.0")
    resp = assess(r)
    assert resp.decision == DECISION_MONITOR
    assert resp.ack_days is None and resp.remediate_days is None
    assert resp.pin_refresh_required is False


def test_none_severity_dev_is_monitor_regardless_of_exposure():
    r = CveReport("CVE-1", "lib", 0.0, EXPOSURE_DEV, fix_available=False)
    resp = assess(r)
    assert resp.decision == DECISION_MONITOR
    assert resp.remediate_days is None


def test_dev_high_demoted_to_medium_sla():
    # HIGH(7.5) dev → 유효 MEDIUM → SCHEDULED, SLA (7,30).
    r = CveReport("CVE-1", "playwright", 7.5, EXPOSURE_DEV, fixed_version="1.6")
    resp = assess(r)
    assert resp.decision == DECISION_SCHEDULED
    assert (resp.ack_days, resp.remediate_days) == (7, 30)


def test_dev_critical_demoted_to_high_still_patch_now():
    r = CveReport("CVE-1", "electron", 9.5, EXPOSURE_DEV, fixed_version="42.0")
    resp = assess(r)
    assert resp.decision == DECISION_PATCH_NOW
    assert (resp.ack_days, resp.remediate_days) == (3, 14)


def test_no_fix_blocks_pin_refresh_but_keeps_urgency():
    r = CveReport("CVE-1", "requests", 9.1, EXPOSURE_RUNTIME, fix_available=False)
    resp = assess(r)
    assert resp.decision == DECISION_PATCH_NOW  # 긴급도는 유지
    assert resp.pin_refresh_required is False   # 상류 수정 없음 → 핀 불가
    assert any("완화" in reason for reason in resp.reasons)


def test_fix_available_sets_pin_refresh_with_version_in_reason():
    r = CveReport("CVE-1", "numpy", 8.0, EXPOSURE_RUNTIME, fixed_version="1.26.4")
    resp = assess(r)
    assert resp.pin_refresh_required is True
    assert any("1.26.4" in reason for reason in resp.reasons)


def test_assess_is_deterministic():
    r = CveReport("CVE-1", "numpy", 9.8, EXPOSURE_RUNTIME, fixed_version="1.0")
    assert assess(r) == assess(r)


# --- POLICY_MATRIX ↔ assess 일치 강제 ---------------------------------------

def test_policy_matrix_matches_assess_for_all_cells():
    # Arrange: 각 (severity, exposure) 칸을 대표하는 CVSS 점수.
    score_of = {
        SEVERITY_CRITICAL: 9.5,
        SEVERITY_HIGH: 7.5,
        SEVERITY_MEDIUM: 5.0,
        SEVERITY_LOW: 2.0,
        SEVERITY_NONE: 0.0,
    }
    for (severity, exposure), expected_decision in POLICY_MATRIX.items():
        score = score_of[severity]
        if score == 0.0:
            report = CveReport("CVE-X", "p", 0.0, exposure, fix_available=False)
        else:
            report = CveReport("CVE-X", "p", score, exposure,
                               fixed_version="9.9.9")
        # Act / Assert: 매트릭스 결정이 assess 결정과 정확히 일치.
        assert assess(report).decision == expected_decision, (severity, exposure)


def test_policy_matrix_excludes_archived():
    # archived 는 항상 OUT_OF_SCOPE 이라 매트릭스에 두지 않는다.
    assert all(exp != EXPOSURE_ARCHIVED for (_sev, exp) in POLICY_MATRIX)


def test_policy_matrix_size():
    # 5 심각도 × 2 노출(runtime·dev).
    assert len(POLICY_MATRIX) == 10


# --- 매니페스트 -------------------------------------------------------------

def test_manifest_is_json_serializable_and_stable():
    import json
    m = policy_manifest()
    assert json.loads(json.dumps(m, ensure_ascii=False)) == m


def test_manifest_advisory_only():
    assert policy_manifest()["advisory_only"] is True


def test_manifest_sla_includes_all_severities():
    sla = policy_manifest()["sla_by_severity"]
    for sev in (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
                SEVERITY_LOW, SEVERITY_NONE):
        assert sev in sla


def test_manifest_matrix_matches_policy_matrix():
    rows = policy_manifest()["matrix"]
    reconstructed = {(r["severity"], r["exposure"]): r["decision"] for r in rows}
    assert reconstructed == POLICY_MATRIX
