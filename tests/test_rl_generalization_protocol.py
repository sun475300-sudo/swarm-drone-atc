"""ODYSSEY Phase 452 — RL 일반화 평가 프로토콜 적합성 게이트 테스트.

핵심 계약 검증: 요건 레지스트리 무결성·차원 일관성·정직성 결속(증거 ⟺ 충족,
디스크 실재 강제)·판정 우선순위(CRITICAL UNMET → NOT_DEFENSIBLE, CRITICAL PARTIAL →
INSUFFICIENT, 잔여 미완 → INSUFFICIENT, 전부 충족 → DEFENSIBLE)·점수 가중(N/A 제외)·
결정 매트릭스 일치·결정론·매니페스트 직렬화·현 자산의 정직한 자가 공시.
"""
from __future__ import annotations

import json
import os

import pytest

from simulation.rl_generalization_protocol import (
    POLICY_MATRIX,
    PROTOCOL_DIMENSIONS,
    REQUIREMENTS,
    STATE_MET,
    STATE_NOT_APPLICABLE,
    STATE_PARTIAL,
    STATE_UNMET,
    VERDICT_DEFENSIBLE,
    VERDICT_INSUFFICIENT,
    VERDICT_NOT_DEFENSIBLE,
    ProtocolRequirement,
    RequirementState,
    SHIPPED,
    all_requirements,
    assess,
    gaps,
    get_requirement,
    main,
    manifest,
    requirements_by_dimension,
    shipped_protocol,
    shipped_states,
)

pytestmark = pytest.mark.unit

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CRITICAL_IDS = tuple(r.requirement_id for r in REQUIREMENTS if r.critical)
_NONCRITICAL_IDS = tuple(r.requirement_id for r in REQUIREMENTS if not r.critical)


def _all_met() -> dict[str, str]:
    """모든 요건을 MET 으로 채운 상태 매핑."""
    return {r.requirement_id: STATE_MET for r in REQUIREMENTS}


def _req_state(**kw) -> RequirementState:
    """유효한 기본값으로 RequirementState 를 만든다(테스트 편의)."""
    defaults = dict(
        requirement_id="RG-01",
        state=STATE_MET,
        evidence="config/scenario_params",
        rationale="r",
    )
    defaults.update(kw)
    return RequirementState(**defaults)  # type: ignore[arg-type]


# --- 레지스트리 무결성 ----------------------------------------------------
def test_requirement_ids_are_unique():
    ids = [r.requirement_id for r in REQUIREMENTS]
    assert len(ids) == len(set(ids))


def test_requirements_have_nonempty_fields():
    for r in REQUIREMENTS:
        assert r.requirement_id.strip()
        assert r.name.strip()
        assert r.basis.strip()
        assert r.description.strip()


def test_every_requirement_dimension_is_known():
    for r in REQUIREMENTS:
        assert r.dimension in PROTOCOL_DIMENSIONS


def test_every_dimension_has_at_least_one_requirement():
    covered = {r.dimension for r in REQUIREMENTS}
    assert covered == set(PROTOCOL_DIMENSIONS)


def test_at_least_one_critical_and_one_noncritical():
    assert _CRITICAL_IDS
    assert _NONCRITICAL_IDS


def test_all_requirements_returns_registry():
    assert all_requirements() == REQUIREMENTS


def test_get_requirement_roundtrip():
    for r in REQUIREMENTS:
        assert get_requirement(r.requirement_id) is r


def test_get_requirement_unknown_raises():
    with pytest.raises(KeyError):
        get_requirement("RG-999")


def test_requirements_by_dimension_sorted_and_scoped():
    for dim in PROTOCOL_DIMENSIONS:
        members = requirements_by_dimension(dim)
        assert all(m.dimension == dim for m in members)
        assert list(members) == sorted(members, key=lambda r: r.requirement_id)


def test_requirements_by_dimension_unknown_raises():
    with pytest.raises(ValueError):
        requirements_by_dimension("nope")


# --- ProtocolRequirement 검증 ---------------------------------------------
def test_requirement_rejects_unknown_dimension():
    with pytest.raises(ValueError):
        ProtocolRequirement("X", "n", "nope", "b", True, "d")


def test_requirement_rejects_non_bool_critical():
    with pytest.raises(TypeError):
        ProtocolRequirement("X", "n", "data_partitioning", "b", 1, "d")  # type: ignore[arg-type]


def test_requirement_rejects_empty_id():
    with pytest.raises(ValueError):
        ProtocolRequirement("", "n", "data_partitioning", "b", True, "d")


# --- RequirementState 정직성 결속 -----------------------------------------
def test_met_requires_evidence():
    with pytest.raises(ValueError):
        _req_state(state=STATE_MET, evidence=None)


def test_partial_requires_evidence():
    with pytest.raises(ValueError):
        _req_state(state=STATE_PARTIAL, evidence=None)


def test_unmet_must_not_cite_evidence():
    with pytest.raises(ValueError):
        _req_state(state=STATE_UNMET, evidence="config/scenario_params")


def test_na_must_not_cite_evidence():
    with pytest.raises(ValueError):
        _req_state(state=STATE_NOT_APPLICABLE, evidence="config/scenario_params")


def test_state_rejects_unknown_state():
    with pytest.raises(ValueError):
        _req_state(state="MAYBE", evidence=None)


def test_state_rejects_unknown_requirement_id():
    with pytest.raises(KeyError):
        _req_state(requirement_id="RG-999")


def test_state_rejects_empty_rationale():
    with pytest.raises(ValueError):
        _req_state(rationale="  ")


def test_state_rejects_internal_space_id():
    with pytest.raises(ValueError):
        ProtocolRequirement("RG 01", "n", "data_partitioning", "b", True, "d")


def test_evidence_states_are_exactly_met_and_partial():
    # 정직성 결속이 적용되는 상태 집합이 의도(MET·PARTIAL)와 정확히 일치함을 고정.
    # 새 상태 추가 시 _EVIDENCE_STATES 갱신 누락을 방지한다.
    from simulation.rl_generalization_protocol import _EVIDENCE_STATES
    assert _EVIDENCE_STATES == frozenset({STATE_MET, STATE_PARTIAL})


# --- 판정 우선순위 --------------------------------------------------------
def test_all_met_is_defensible():
    a = assess(_all_met())
    assert a.verdict == VERDICT_DEFENSIBLE
    assert a.blocking == ()
    assert a.score == pytest.approx(1.0)


def test_critical_unmet_is_not_defensible():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_UNMET
    a = assess(states)
    assert a.verdict == VERDICT_NOT_DEFENSIBLE
    assert _CRITICAL_IDS[0] in a.blocking


def test_critical_partial_is_insufficient():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_PARTIAL
    a = assess(states)
    assert a.verdict == VERDICT_INSUFFICIENT
    assert _CRITICAL_IDS[0] in a.blocking


def test_noncritical_incomplete_is_insufficient():
    states = _all_met()
    states[_NONCRITICAL_IDS[0]] = STATE_PARTIAL
    a = assess(states)
    assert a.verdict == VERDICT_INSUFFICIENT
    assert _NONCRITICAL_IDS[0] in a.blocking


def test_critical_unmet_outranks_partial():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_PARTIAL
    states[_CRITICAL_IDS[1]] = STATE_UNMET
    a = assess(states)
    assert a.verdict == VERDICT_NOT_DEFENSIBLE
    # NOT_DEFENSIBLE 의 blocking 은 CRITICAL UNMET 만.
    assert a.blocking == (_CRITICAL_IDS[1],)


def test_unspecified_requirements_default_unmet():
    # 빈 매핑 → 전부 UNMET → CRITICAL UNMET 존재 → NOT_DEFENSIBLE.
    a = assess({})
    assert a.verdict == VERDICT_NOT_DEFENSIBLE
    assert a.score == pytest.approx(0.0)


def test_assess_rejects_unknown_requirement_id():
    with pytest.raises(KeyError):
        assess({"RG-999": STATE_MET})


def test_assess_rejects_unknown_state():
    with pytest.raises(ValueError):
        assess({"RG-01": "MAYBE"})


# --- 점수 가중 (N/A 제외) -------------------------------------------------
def test_na_excluded_from_score_denominator():
    # 전부 N/A 면 공허참 → score 1.0, verdict DEFENSIBLE.
    states = {r.requirement_id: STATE_NOT_APPLICABLE for r in REQUIREMENTS}
    a = assess(states)
    assert a.score == pytest.approx(1.0)
    assert a.verdict == VERDICT_DEFENSIBLE


def test_partial_scores_half():
    states = _all_met()
    states[_NONCRITICAL_IDS[0]] = STATE_PARTIAL
    a = assess(states)
    n = len(REQUIREMENTS)
    assert a.score == pytest.approx((n - 0.5) / n, abs=1e-4)


# --- 결정 매트릭스 일치 ---------------------------------------------------
def test_policy_matrix_matches_assess():
    for worst, other, expected in POLICY_MATRIX:
        states = _all_met()
        # CRITICAL 한 건을 worst 상태로.
        states[_CRITICAL_IDS[0]] = worst
        if other:
            states[_NONCRITICAL_IDS[0]] = STATE_PARTIAL
        a = assess(states)
        assert a.verdict == expected, (worst, other)


# --- 결정론 ---------------------------------------------------------------
def test_assess_is_deterministic():
    states = _all_met()
    states[_CRITICAL_IDS[0]] = STATE_PARTIAL
    assert assess(states).verdict == assess(states).verdict
    assert assess(states).score == assess(states).score


def test_shipped_protocol_is_deterministic():
    assert shipped_protocol().verdict == shipped_protocol().verdict
    assert shipped_protocol().score == shipped_protocol().score


# --- 현 자산 정직한 자가 공시 ---------------------------------------------
def test_shipped_covers_every_requirement_exactly_once():
    shipped_ids = [s.requirement_id for s in SHIPPED]
    assert sorted(shipped_ids) == sorted(r.requirement_id for r in REQUIREMENTS)
    assert len(shipped_ids) == len(set(shipped_ids))


def test_shipped_evidence_paths_exist_on_disk():
    """정직성 결속: MET/PARTIAL 이 인용한 증거 경로는 실제로 디스크에 존재해야 한다."""
    for s in SHIPPED:
        if s.evidence is not None:
            full = os.path.join(REPO_ROOT, s.evidence)
            assert os.path.exists(full), f"{s.requirement_id} 증거 경로 부재: {s.evidence}"


def test_shipped_unmet_have_no_evidence():
    for s in SHIPPED:
        if s.state in (STATE_UNMET, STATE_NOT_APPLICABLE):
            assert s.evidence is None


def test_shipped_verdict_is_honestly_not_defensible():
    """SDACS 의 RL 은 연구 수준 — 격상 없는 정직한 판정은 NOT_DEFENSIBLE."""
    a = shipped_protocol()
    assert a.verdict == VERDICT_NOT_DEFENSIBLE
    # CRITICAL UNMET 이 결격 사유로 보고된다.
    assert a.blocking
    for rid in a.blocking:
        assert get_requirement(rid).critical
        assert shipped_states()[rid] == STATE_UNMET


def test_gaps_are_unmet_only():
    for s in gaps():
        assert s.state == STATE_UNMET
        assert s.evidence is None


# --- 매니페스트 직렬화 ----------------------------------------------------
def test_manifest_is_json_serializable():
    m = manifest()
    blob = json.dumps(m, ensure_ascii=False)
    assert "sdacs-rl-generalization-protocol" in blob
    assert m["phase"] == 452
    assert len(m["requirements"]) == len(REQUIREMENTS)
    assert m["shipped"]["verdict"] == VERDICT_NOT_DEFENSIBLE


# --- CLI ------------------------------------------------------------------
@pytest.mark.parametrize("flag", ["--requirements", "--status", "--gaps", "--policy", "--manifest"])
def test_main_known_flags_succeed(flag, capsys):
    assert main([flag]) == 0
    assert capsys.readouterr().out.strip()


def test_main_default_is_status(capsys):
    assert main([]) == 0
    assert "현 자산 판정" in capsys.readouterr().out


def test_main_unknown_flag_returns_2(capsys):
    assert main(["--nope"]) == 2
