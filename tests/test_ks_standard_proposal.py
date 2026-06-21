"""ODYSSEY Phase 471 — KS 국가표준 제안 적합성 게이트 테스트.

핵심 계약 검증: 제안 요건 레지스트리 무결성·판정 우선순위(CRITICAL UNMET →
NOT_READY, CRITICAL PARTIAL → NEEDS_WORK, 잔여 미완 → NEEDS_WORK, 전부 충족 →
READY_TO_PROPOSE, 미지 상태 → REVIEW 없음/예외)·점수 가중(N/A 제외)·결정 매트릭스
일치·결정론·매니페스트 직렬화·현 리포 후보의 정직한 자가 공시.
"""
from __future__ import annotations

import json

import pytest

from simulation.ks_standard_proposal import (
    CRITERIA,
    POLICY_MATRIX,
    STATE_MET,
    STATE_NOT_APPLICABLE,
    STATE_PARTIAL,
    STATE_UNMET,
    VERDICT_NEEDS_WORK,
    VERDICT_NOT_READY,
    VERDICT_READY,
    KsCriterion,
    all_criteria,
    assess,
    get_criterion,
    manifest,
    shipped_proposal,
)

pytestmark = pytest.mark.unit

_CRITICAL_IDS = tuple(c.criterion_id for c in CRITERIA if c.critical)
_NONCRITICAL_IDS = tuple(c.criterion_id for c in CRITERIA if not c.critical)


def _all_met() -> dict[str, str]:
    """모든 요건을 MET 으로 채운 상태 매핑."""
    return {c.criterion_id: STATE_MET for c in CRITERIA}


# --- 레지스트리 무결성 ----------------------------------------------------
def test_criteria_ids_are_unique():
    # Arrange / Act
    ids = [c.criterion_id for c in CRITERIA]
    # Assert
    assert len(ids) == len(set(ids))


def test_criteria_have_nonempty_fields():
    for c in CRITERIA:
        assert c.criterion_id.strip()
        assert c.name.strip()
        assert c.basis.strip()
        assert c.description.strip()


def test_at_least_one_critical_and_one_noncritical():
    assert _CRITICAL_IDS
    assert _NONCRITICAL_IDS


def test_all_criteria_returns_full_registry():
    assert all_criteria() == CRITERIA


def test_get_criterion_round_trips():
    c = CRITERIA[0]
    assert get_criterion(c.criterion_id) is c


def test_get_criterion_unknown_raises():
    with pytest.raises(KeyError):
        get_criterion("KS-NOPE")


def test_criterion_is_frozen():
    with pytest.raises(Exception):
        CRITERIA[0].critical = False  # type: ignore[misc]


# --- 판정 우선순위 --------------------------------------------------------
def test_all_met_is_ready():
    # Arrange / Act
    a = assess(_all_met())
    # Assert
    assert a.verdict == VERDICT_READY
    assert a.score == pytest.approx(1.0)
    assert a.blocking == ()


def test_critical_unmet_is_not_ready():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_UNMET
    a = assess(states)
    assert a.verdict == VERDICT_NOT_READY
    assert _CRITICAL_IDS[0] in a.blocking


def test_critical_partial_is_needs_work():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_PARTIAL
    a = assess(states)
    assert a.verdict == VERDICT_NEEDS_WORK
    assert _CRITICAL_IDS[0] in a.blocking


def test_noncritical_unmet_is_needs_work_not_blocked_by_critical():
    states = _all_met()
    states[_NONCRITICAL_IDS[0]] = STATE_UNMET
    a = assess(states)
    assert a.verdict == VERDICT_NEEDS_WORK
    assert _NONCRITICAL_IDS[0] in a.blocking


def test_critical_unmet_dominates_noncritical_partial():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_UNMET
    states[_NONCRITICAL_IDS[0]] = STATE_PARTIAL
    a = assess(states)
    # CRITICAL UNMET 이 최우선 → NOT_READY, blocking 은 CRITICAL 만.
    assert a.verdict == VERDICT_NOT_READY
    assert set(a.blocking) == {_CRITICAL_IDS[0]}


def test_critical_partial_dominates_noncritical_unmet():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_PARTIAL
    states[_NONCRITICAL_IDS[0]] = STATE_UNMET
    a = assess(states)
    assert a.verdict == VERDICT_NEEDS_WORK
    assert set(a.blocking) == {_CRITICAL_IDS[0]}


# --- 미지정 요건 / 입력 검증 ----------------------------------------------
def test_unspecified_criterion_defaults_to_unmet():
    # 빈 매핑 → 모든 요건 UNMET → CRITICAL UNMET 존재 → NOT_READY.
    a = assess({})
    assert a.verdict == VERDICT_NOT_READY
    assert all(s == STATE_UNMET for s in a.state_by_criterion.values())


def test_unknown_criterion_id_raises():
    with pytest.raises(KeyError):
        assess({"KS-NOPE": STATE_MET})


def test_unknown_state_value_raises():
    with pytest.raises(ValueError):
        assess({_CRITICAL_IDS[0]: "MAYBE"})


# --- 점수 가중 ------------------------------------------------------------
def test_partial_counts_as_half():
    states = _all_met()
    states[_NONCRITICAL_IDS[0]] = STATE_PARTIAL
    a = assess(states)
    expected = (len(CRITERIA) - 0.5) / len(CRITERIA)
    assert a.score == pytest.approx(round(expected, 4))


def test_not_applicable_excluded_from_score_denominator():
    # 비적용 1건은 분모에서 빠지므로 나머지 전부 MET 이면 점수 1.0.
    states = _all_met()
    states[_NONCRITICAL_IDS[0]] = STATE_NOT_APPLICABLE
    a = assess(states)
    assert a.score == pytest.approx(1.0)
    # N/A 는 게이트 제외 → 나머지 MET 이면 READY.
    assert a.verdict == VERDICT_READY


def test_all_not_applicable_score_is_zero():
    states = {c.criterion_id: STATE_NOT_APPLICABLE for c in CRITERIA}
    a = assess(states)
    assert a.score == pytest.approx(0.0)
    # 평가 대상이 없으면 미완 항목도 없으므로 READY.
    assert a.verdict == VERDICT_READY


# --- 결정 매트릭스 일치 ---------------------------------------------------
def test_policy_matrix_matches_assess():
    crit = _CRITICAL_IDS[0]
    other = _NONCRITICAL_IDS[0]
    for worst_critical, has_other, expected in POLICY_MATRIX:
        states = _all_met()
        states[crit] = worst_critical
        if has_other:
            states[other] = STATE_UNMET
        a = assess(states)
        assert a.verdict == expected, (
            f"({worst_critical}, other={has_other}) → {a.verdict} != {expected}"
        )


# --- 결정론 ---------------------------------------------------------------
def test_assess_is_deterministic():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_PARTIAL
    first = assess(states)
    second = assess(states)
    assert first == second


def test_state_by_criterion_is_read_only():
    a = assess(_all_met())
    with pytest.raises(TypeError):
        a.state_by_criterion["KS-01"] = STATE_UNMET  # type: ignore[index]


# --- 매니페스트 -----------------------------------------------------------
def test_manifest_is_json_serializable():
    m = manifest()
    dumped = json.dumps(m, ensure_ascii=False)
    assert "sdacs-ks-standard-proposal" in dumped
    assert len(m["criteria"]) == len(CRITERIA)


def test_manifest_shipped_matches_shipped_proposal():
    m = manifest()
    a = shipped_proposal()
    assert m["shipped"]["verdict"] == a.verdict
    assert m["shipped"]["score"] == a.score


# --- 현 리포 후보의 정직한 자가 공시 --------------------------------------
def test_shipped_proposal_is_not_ready_honestly():
    # 중복성 검토·의견수렴 미수행(UNMET) 중 CRITICAL(KS-04)이 있어 NOT_READY 여야.
    a = shipped_proposal()
    assert a.verdict == VERDICT_NOT_READY
    assert "KS-04" in a.blocking


def test_shipped_proposal_score_in_unit_interval():
    a = shipped_proposal()
    assert 0.0 <= a.score <= 1.0


def test_shipped_summary_is_human_readable():
    a = shipped_proposal()
    s = a.summary()
    assert a.verdict in s
    assert "%" in s
