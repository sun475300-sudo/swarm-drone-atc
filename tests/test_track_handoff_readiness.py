"""ODYSSEY Phase 492 — 차세대 트랙 공모·선정 정책 테스트.

핵심 계약 검증: 제안 적격 판정(주체·범위·필수 기준 우선순위)·범위 버킷
경계·POLICY_MATRIX 와 assess_proposal 일치·선정 결정론(부가 강점 점수 →
안정 해시 동률 분리)·코호트 판정(대기/적격 없음/이양 준비)·매니페스트 JSON
직렬화·리포 현 상태 정직성(AWAITING_PROPOSALS).
"""
from __future__ import annotations

import dataclasses
import json

import pytest

from simulation.track_handoff_readiness import (
    MIN_TRACK_PHASES,
    POLICY_MATRIX,
    SCOPE_NONE,
    SCOPE_SMALL,
    SCOPE_TRACK,
    SELECTION_AWAITING_PROPOSALS,
    SELECTION_HANDOFF_READY,
    SELECTION_NO_ELIGIBLE,
    VERDICT_ELIGIBLE,
    VERDICT_NEEDS_WORK,
    VERDICT_REJECTED,
    TrackProposal,
    assess_proposal,
    main,
    policy_manifest,
    readiness_score,
    scope_bucket,
    select_track,
    shipped_proposals,
)

pytestmark = pytest.mark.unit


def _eligible(
    pid: str = "P",
    *,
    phases: int = MIN_TRACK_PHASES,
    mentor: bool = False,
    funding: bool = False,
) -> TrackProposal:
    """모든 필수 기준을 충족한 적격 제안 헬퍼."""
    return TrackProposal(
        proposal_id=pid,
        title=f"track {pid}",
        champion=f"lead-{pid}",
        has_charter=True,
        has_success_criteria=True,
        independent_of_principal=True,
        prerequisites_met=True,
        estimated_phases=phases,
        mentor_committed=mentor,
        funding_identified=funding,
    )


# --- 범위 버킷 -------------------------------------------------------------

@pytest.mark.parametrize("phases,bucket", [
    (-5, SCOPE_NONE),
    (0, SCOPE_NONE),
    (1, SCOPE_SMALL),
    (MIN_TRACK_PHASES - 1, SCOPE_SMALL),
    (MIN_TRACK_PHASES, SCOPE_TRACK),
    (40, SCOPE_TRACK),
])
def test_scope_bucket(phases: int, bucket: str) -> None:
    assert scope_bucket(phases) == bucket


# --- 제안 적격 판정 --------------------------------------------------------

def test_full_proposal_eligible() -> None:
    result = assess_proposal(_eligible())
    assert result.verdict == VERDICT_ELIGIBLE
    assert result.is_eligible()
    assert result.scope == SCOPE_TRACK
    assert any("적격" in r for r in result.reasons)


def test_empty_champion_rejected_even_if_complete() -> None:
    """주체가 없으면 다른 기준이 완비돼도 공모 성립 불가 — REJECTED."""
    p = TrackProposal(
        proposal_id="X", title="t", champion="   ",
        has_charter=True, has_success_criteria=True,
        independent_of_principal=True, prerequisites_met=True,
        estimated_phases=20,
    )
    result = assess_proposal(p)
    assert result.verdict == VERDICT_REJECTED
    assert result.score == 0


def test_zero_phases_rejected() -> None:
    result = assess_proposal(_eligible(phases=0))
    assert result.verdict == VERDICT_REJECTED
    assert result.scope == SCOPE_NONE


def test_small_scope_needs_work() -> None:
    """주체·필수 기준이 있어도 트랙 규모 미달이면 보완 대상."""
    result = assess_proposal(_eligible(phases=MIN_TRACK_PHASES - 1))
    assert result.verdict == VERDICT_NEEDS_WORK
    assert result.scope == SCOPE_SMALL


def test_track_scope_missing_musts_needs_work() -> None:
    p = TrackProposal(
        proposal_id="Y", title="t", champion="lead",
        has_charter=True, has_success_criteria=False,   # 성공 기준 결여
        independent_of_principal=True, prerequisites_met=True,
        estimated_phases=10,
    )
    result = assess_proposal(p)
    assert result.verdict == VERDICT_NEEDS_WORK
    assert any("성공 기준" in r for r in result.reasons)


def test_dependent_on_principal_not_eligible() -> None:
    """원저자에 다시 묶이는 제안은 이양이 아님 — NEEDS_WORK."""
    p = dataclasses.replace(_eligible(), independent_of_principal=False)
    result = assess_proposal(p)
    assert result.verdict == VERDICT_NEEDS_WORK
    assert any("독립성" in r for r in result.reasons)


# --- readiness_score -------------------------------------------------------

@pytest.mark.parametrize("mentor,funding,score", [
    (False, False, 0),
    (True, False, 1),
    (False, True, 1),
    (True, True, 2),
])
def test_readiness_score(mentor: bool, funding: bool, score: int) -> None:
    assert readiness_score(_eligible(mentor=mentor, funding=funding)) == score


def test_score_zero_for_non_eligible() -> None:
    """비적격 제안의 판정 score 는 0(부가 강점 무의미)."""
    p = _eligible(phases=2, mentor=True, funding=True)  # 규모 미달
    result = assess_proposal(p)
    assert result.verdict == VERDICT_NEEDS_WORK
    assert result.score == 0


# --- POLICY_MATRIX ↔ assess 일치 -------------------------------------------

def _proposal_for(has_champion: bool, scope: str, musts: bool) -> TrackProposal:
    phases = {SCOPE_NONE: 0, SCOPE_SMALL: 3, SCOPE_TRACK: MIN_TRACK_PHASES}[scope]
    return TrackProposal(
        proposal_id="m",
        title="t",
        champion="lead" if has_champion else "",
        has_charter=musts,
        has_success_criteria=musts,
        independent_of_principal=musts,
        prerequisites_met=musts,
        estimated_phases=phases,
    )


@pytest.mark.parametrize("champ", [True, False])
@pytest.mark.parametrize("scope", [SCOPE_NONE, SCOPE_SMALL, SCOPE_TRACK])
@pytest.mark.parametrize("musts", [True, False])
def test_matrix_matches_assess(champ: bool, scope: str, musts: bool) -> None:
    expected = POLICY_MATRIX[(champ, scope, musts)]
    result = assess_proposal(_proposal_for(champ, scope, musts))
    assert result.verdict == expected


def test_matrix_covers_all_combos() -> None:
    assert len(POLICY_MATRIX) == 2 * 3 * 2  # champion × scope × musts


# --- 선정 ------------------------------------------------------------------

def test_no_proposals_awaiting() -> None:
    result = select_track(())
    assert result.verdict == SELECTION_AWAITING_PROPOSALS
    assert result.selected_id is None
    assert result.proposal_count == 0


def test_proposals_but_none_eligible() -> None:
    proposals = (
        TrackProposal("a", "t", "", estimated_phases=10),       # REJECTED
        _eligible("b", phases=2),                                # NEEDS_WORK
    )
    result = select_track(proposals)
    assert result.verdict == SELECTION_NO_ELIGIBLE
    assert result.selected_id is None
    assert result.eligible_ids == ()


def test_single_eligible_selected() -> None:
    result = select_track((_eligible("only"),))
    assert result.verdict == SELECTION_HANDOFF_READY
    assert result.selected_id == "only"
    assert result.is_handoff_ready()


def test_higher_score_wins() -> None:
    """부가 강점 점수가 높은 적격 제안이 선정된다."""
    weak = _eligible("weak", mentor=False, funding=False)   # 0
    strong = _eligible("strong", mentor=True, funding=True)  # 2
    result = select_track((weak, strong))
    assert result.selected_id == "strong"
    assert set(result.eligible_ids) == {"weak", "strong"}


def test_tie_broken_by_stable_hash() -> None:
    """동점 적격 제안은 안정 해시로 결정적 분리 — 순서 무관."""
    a = _eligible("alpha", mentor=True, funding=False)  # score 1
    b = _eligible("bravo", mentor=False, funding=True)  # score 1
    forward = select_track((a, b))
    backward = select_track((b, a))
    assert forward.selected_id == backward.selected_id  # 입력 순서 무관 결정론


def test_selection_deterministic() -> None:
    proposals = (_eligible("a", mentor=True), _eligible("b"), _eligible("c"))
    assert select_track(proposals) == select_track(proposals)


# --- 매니페스트 ------------------------------------------------------------

def test_manifest_json_serializable() -> None:
    manifest = policy_manifest()
    assert json.loads(json.dumps(manifest, ensure_ascii=False)) == manifest


def test_manifest_matrix_matches_policy() -> None:
    manifest = policy_manifest()
    from_manifest = {
        (row["has_champion"], row["scope"], row["musts_complete"]): row["verdict"]
        for row in manifest["matrix"]
    }
    assert from_manifest == POLICY_MATRIX
    assert manifest["min_track_phases"] == MIN_TRACK_PHASES


# --- 리포 현 상태 정직성 ---------------------------------------------------

def test_shipped_status_awaiting_proposals() -> None:
    """현 리포는 차세대 기수 미형성·제안 0 — 정직한 판정은 AWAITING_PROPOSALS."""
    result = select_track(shipped_proposals())
    assert result.verdict == SELECTION_AWAITING_PROPOSALS


def test_shipped_pin_breaks_when_proposal_added() -> None:
    """실제 제안이 접수되면 0 가정이 깨지도록 핀(로드맵 갱신 강제)."""
    assert len(shipped_proposals()) == 0


# --- CLI -------------------------------------------------------------------

@pytest.mark.parametrize("flag", ["--policy", "--demo", "--status", "--manifest"])
def test_cli_known_flags_succeed(flag: str) -> None:
    assert main([flag]) == 0


def test_cli_default_is_policy() -> None:
    assert main([]) == 0


def test_cli_unknown_flag_errors() -> None:
    assert main(["--bogus"]) == 2


def test_cli_manifest_outputs_valid_json(capsys: pytest.CaptureFixture) -> None:
    main(["--manifest"])
    out = capsys.readouterr().out
    assert json.loads(out)["schema"] == "sdacs-nextgen-track-handoff"


def test_cli_demo_selects_strongest(capsys: pytest.CaptureFixture) -> None:
    """데모 공모에서 부가 강점 2/2 인 NT-002 가 선정됨이 출력에 드러난다."""
    main(["--demo"])
    out = capsys.readouterr().out
    assert "NT-002" in out
