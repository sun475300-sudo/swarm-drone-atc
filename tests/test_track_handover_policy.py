"""ODYSSEY Phase 491 — 차세대 트랙 이양 검토 게이트 정책 테스트.

핵심 계약 검증: 소유자 부재 구조적 반려(REJECT) 우선·리뷰 미완 보류(DEFER)·
보완형 결함 REVISE·전부 충족 시 ACCEPT·우선순위(소유자 부재면 리뷰·헌장과
무관 REJECT)·POLICY_MATRIX 와 assess 의 일치(전수)·결정론·매니페스트 JSON
직렬화·빈 식별자 거부·리포 현 상태 정직성(AWAITING_PROPOSALS).
"""
from __future__ import annotations

import itertools
import json
from dataclasses import FrozenInstanceError

import pytest

from simulation.track_handover_policy import (
    EXISTING_TRACKS,
    POLICY_MATRIX,
    PROGRAM_AWAITING,
    PROGRAM_REGISTERED,
    VERDICT_ACCEPT,
    VERDICT_DEFER,
    VERDICT_REJECT,
    VERDICT_REVISE,
    HandoverAssessment,
    TrackProposal,
    assess_handover,
    is_clean,
    main,
    policy_manifest,
    program_status,
    shipped_proposals,
)

pytestmark = pytest.mark.unit


def _proposal(
    *,
    charter: bool = True,
    overlap: bool = False,
    owner: bool = True,
    sandbox: bool = True,
    track_id: str = "T1",
) -> TrackProposal:
    return TrackProposal(
        track_id=track_id,
        title="테스트 트랙",
        charter_present=charter,
        scope_overlaps_existing=overlap,
        has_next_gen_owner=owner,
        sandbox_feasible=sandbox,
    )


# --- 식별자 검증 -----------------------------------------------------------

@pytest.mark.parametrize("bad", ["", "   "])
def test_empty_track_id_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        TrackProposal(track_id=bad, title="x")


@pytest.mark.parametrize("bad", ["", "   "])
def test_empty_title_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        TrackProposal(track_id="T1", title=bad)


# --- is_clean -------------------------------------------------------------

def test_clean_requires_charter_no_overlap_sandbox() -> None:
    assert is_clean(_proposal())


@pytest.mark.parametrize("charter,overlap,sandbox", [
    (False, False, True),   # 헌장 부재
    (True, True, True),     # 범위 중복
    (True, False, False),   # sandbox 미검증
])
def test_clean_false_when_any_gap(
    charter: bool, overlap: bool, sandbox: bool
) -> None:
    assert not is_clean(
        _proposal(charter=charter, overlap=overlap, sandbox=sandbox)
    )


def test_clean_ignores_owner() -> None:
    # 소유자 유무는 clean 과 무관(구조적 결격은 별도 단계).
    assert is_clean(_proposal(owner=False))


# --- 판정 우선순위 ---------------------------------------------------------

def test_accept_when_all_satisfied() -> None:
    result = assess_handover(_proposal(), current_gen_reviewed=True)
    assert result.verdict == VERDICT_ACCEPT
    assert result.is_accepted()


def test_reject_when_no_owner_regardless_of_review_or_charter() -> None:
    # 소유자 부재는 리뷰 완료·헌장 완비여도 REJECT(구조적 결격 우선).
    result = assess_handover(
        _proposal(owner=False, charter=True), current_gen_reviewed=True
    )
    assert result.verdict == VERDICT_REJECT


def test_defer_when_owner_present_but_not_reviewed() -> None:
    result = assess_handover(_proposal(), current_gen_reviewed=False)
    assert result.verdict == VERDICT_DEFER


def test_revise_when_reviewed_owner_but_gap() -> None:
    result = assess_handover(
        _proposal(charter=False), current_gen_reviewed=True
    )
    assert result.verdict == VERDICT_REVISE


def test_reject_precedes_defer() -> None:
    # 소유자 없고 + 미검토 → REJECT(소유자 우선), DEFER 아님.
    result = assess_handover(_proposal(owner=False), current_gen_reviewed=False)
    assert result.verdict == VERDICT_REJECT


def test_defer_surfaces_fixable_blockers_early() -> None:
    result = assess_handover(
        _proposal(charter=False, sandbox=False), current_gen_reviewed=False
    )
    assert result.verdict == VERDICT_DEFER
    joined = result.summary()
    assert "헌장 부재" in joined
    assert "sandbox 재현 미검증" in joined
    # 미검토 보류 사유에 소유자 항목은 등장하지 않는다(소유자는 있음).
    assert "차세대 소유자" not in joined


# --- POLICY_MATRIX ↔ assess 전수 일치 -------------------------------------

def test_matrix_matches_assess_for_all_combinations() -> None:
    for charter, overlap, owner, sandbox, reviewed in itertools.product(
        [False, True], repeat=5
    ):
        proposal = _proposal(
            charter=charter, overlap=overlap, owner=owner, sandbox=sandbox
        )
        clean = is_clean(proposal)
        expected = POLICY_MATRIX[(owner, reviewed, clean)]
        actual = assess_handover(proposal, reviewed).verdict
        assert actual == expected, (
            f"owner={owner} reviewed={reviewed} clean={clean}: "
            f"matrix={expected} assess={actual}"
        )


def test_matrix_covers_all_buckets() -> None:
    keys = set(POLICY_MATRIX)
    assert keys == set(itertools.product([False, True], repeat=3))


def test_matrix_verdicts_are_known() -> None:
    known = {VERDICT_ACCEPT, VERDICT_REVISE, VERDICT_DEFER, VERDICT_REJECT}
    assert set(POLICY_MATRIX.values()) <= known


# --- 결정론 ----------------------------------------------------------------

def test_assessment_is_deterministic() -> None:
    proposal = _proposal(charter=False)
    a = assess_handover(proposal, True)
    b = assess_handover(proposal, True)
    assert a == b


def test_blockers_enumerated() -> None:
    result = assess_handover(
        _proposal(charter=False, overlap=True, owner=False, sandbox=False),
        current_gen_reviewed=True,
    )
    assert set(result.blockers) == {
        "차세대 소유자 미지정",
        "헌장 부재",
        "기존 트랙과 범위 중복",
        "sandbox 재현 미검증",
    }


# --- program_status --------------------------------------------------------

def test_blockers_empty_when_all_satisfied() -> None:
    result = assess_handover(_proposal(), current_gen_reviewed=True)
    assert result.blockers == ()


def test_program_status_awaiting_when_empty() -> None:
    assert program_status(()) == PROGRAM_AWAITING


def test_program_status_registered_when_nonempty() -> None:
    assert program_status((_proposal(),)) == PROGRAM_REGISTERED


# --- 리포 현 상태 정직성 ---------------------------------------------------

def test_shipped_proposals_empty_awaiting() -> None:
    # 2027+ 차세대 기수 미형성 → 0건. 첫 제안 등록 시 이 핀이 의도적으로 깨짐.
    proposals = shipped_proposals()
    assert proposals == ()
    assert program_status(proposals) == PROGRAM_AWAITING


# --- 매니페스트 ------------------------------------------------------------

def test_manifest_json_serializable() -> None:
    manifest = policy_manifest()
    dumped = json.dumps(manifest, ensure_ascii=False)
    assert "sdacs-track-handover" in dumped
    assert len(manifest["matrix"]) == len(POLICY_MATRIX)


def test_manifest_lists_existing_tracks() -> None:
    manifest = policy_manifest()
    names = {t["name"] for t in manifest["existing_tracks"]}
    assert names == {name for _, name in EXISTING_TRACKS}
    assert any("Continuum" in n for n in names)


# --- CLI -------------------------------------------------------------------

@pytest.mark.parametrize("flag", ["--policy", "--demo", "--status", "--manifest"])
def test_cli_known_flags_succeed(flag: str) -> None:
    assert main([flag]) == 0


def test_cli_default_is_policy() -> None:
    assert main([]) == 0


def test_cli_unknown_flag_errors() -> None:
    assert main(["--bogus"]) == 2


# --- summary 형식 ----------------------------------------------------------

def test_summary_includes_verdict_and_track_id() -> None:
    result = assess_handover(_proposal(track_id="ZZ"), current_gen_reviewed=True)
    assert result.summary().startswith("ACCEPT [ZZ]")


def test_assessment_is_frozen() -> None:
    result = assess_handover(_proposal(), current_gen_reviewed=True)
    with pytest.raises(FrozenInstanceError):
        result.verdict = "X"  # type: ignore[misc]
