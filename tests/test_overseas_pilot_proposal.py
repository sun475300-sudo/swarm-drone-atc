"""ODYSSEY Phase 411 — 해외 파일럿 제안서 적합성 게이트 테스트.

핵심 계약 검증: 기준 무결성·입력 검증(누락/미지 id/미지 상태/PP-02 근거 결속)·
판정 우선순위(CRITICAL UNMET → NOT_READY > CRITICAL PARTIAL → NEEDS_WORK >
잔여 미완 → NEEDS_WORK > 전부 MET → READY)·POLICY_MATRIX ↔ assess 정확 일치·
가중 점수 집계(PARTIAL=절반)·결정론·매니페스트 JSON 직렬화·CLI·현 후보 3종
정직성·인용 모듈 디스크 실재.
"""
from __future__ import annotations

import json

import pytest

from simulation.overseas_pilot_proposal import (
    CRITERIA,
    POLICY_MATRIX,
    SEVERITY_CRITICAL,
    SEVERITY_RECOMMENDED,
    STATUS_MET,
    STATUS_PARTIAL,
    STATUS_UNMET,
    VERDICT_NEEDS_WORK,
    VERDICT_NOT_READY,
    VERDICT_READY_TO_PROPOSE,
    PilotCriterion,
    PilotProposal,
    assess,
    criteria_manifest,
    find_proposal,
    main,
    missing_module_refs,
    most_ready,
    shipped_proposals,
)

pytestmark = pytest.mark.unit

_CRITERION_IDS = tuple(c.criterion_id for c in CRITERIA)


def _proposal(**overrides: str) -> PilotProposal:
    """기본 전부 MET 제안서에 일부 기준만 덮어쓴 후보 생성."""
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    statuses.update(overrides)
    return PilotProposal(
        proposal_id="test",
        target="테스트 대상",
        jurisdiction="TEST",
        statuses=statuses,
        module_refs=("simulation/geo_zones.py",),
    )


# --- 기준 무결성 -----------------------------------------------------------
def test_criteria_ids_unique():
    ids = [c.criterion_id for c in CRITERIA]
    assert len(ids) == len(set(ids))


def test_criteria_severities_valid():
    for c in CRITERIA:
        assert c.severity in (SEVERITY_CRITICAL, SEVERITY_RECOMMENDED)


def test_criteria_have_rationale():
    for c in CRITERIA:
        assert c.description.strip()
        assert c.rationale.strip()


def test_expected_critical_count():
    # 필수 4 + 권장 2 설계.
    crit = [c for c in CRITERIA if c.severity == SEVERITY_CRITICAL]
    rec = [c for c in CRITERIA if c.severity == SEVERITY_RECOMMENDED]
    assert len(crit) == 4
    assert len(rec) == 2


def test_criterion_rejects_unknown_severity():
    with pytest.raises(ValueError, match="알 수 없는 심각도"):
        PilotCriterion("X", "TYPO", "desc", "rationale")


def test_criterion_rejects_empty_description():
    with pytest.raises(ValueError, match="description"):
        PilotCriterion("X", SEVERITY_CRITICAL, "", "rationale")


def test_criterion_rejects_empty_rationale():
    with pytest.raises(ValueError, match="rationale"):
        PilotCriterion("X", SEVERITY_CRITICAL, "desc", "")


# --- 입력 검증 -------------------------------------------------------------
def test_missing_criterion_rejected():
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    del statuses["PP-01"]
    with pytest.raises(ValueError, match="누락"):
        PilotProposal("x", "t", "J", statuses, ("simulation/geo_zones.py",))


def test_unknown_criterion_rejected():
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    statuses["PP-99"] = STATUS_MET
    with pytest.raises(ValueError, match="알 수 없는 기준"):
        PilotProposal("x", "t", "J", statuses, ("simulation/geo_zones.py",))


def test_unknown_status_rejected():
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    statuses["PP-01"] = "MAYBE"
    with pytest.raises(ValueError, match="알 수 없는 상태"):
        PilotProposal("x", "t", "J", statuses, ("simulation/geo_zones.py",))


def test_pp02_met_requires_module_refs():
    # PP-02 가 MET/PARTIAL 인데 근거 모듈이 없으면 거부(정직성 결속).
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    with pytest.raises(ValueError, match="module_refs"):
        PilotProposal("x", "t", "J", statuses, ())


def test_pp02_unmet_allows_empty_module_refs():
    # PP-02 가 UNMET 이면 근거 모듈 없이도 구성 가능.
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    statuses["PP-02"] = STATUS_UNMET
    proposal = PilotProposal("x", "t", "J", statuses, ())
    assert proposal.module_refs == ()


def test_empty_module_ref_rejected():
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    with pytest.raises(ValueError, match="비어 있을 수 없다"):
        PilotProposal("x", "t", "J", statuses, ("simulation/geo_zones.py", "  "))


def test_statuses_are_read_only_after_construction():
    proposal = _proposal()
    with pytest.raises(TypeError):
        proposal.statuses["PP-01"] = STATUS_UNMET  # type: ignore[index]


# --- 판정 우선순위 ---------------------------------------------------------
def test_all_met_is_ready():
    result = assess(_proposal())
    assert result.verdict == VERDICT_READY_TO_PROPOSE
    assert result.is_ready()
    assert result.score == 1.0
    assert result.met == tuple(sorted(_CRITERION_IDS))


def test_critical_unmet_is_not_ready():
    result = assess(_proposal(**{"PP-03": STATUS_UNMET}))
    assert result.verdict == VERDICT_NOT_READY
    assert "PP-03" in result.unmet_critical


def test_critical_partial_is_needs_work():
    result = assess(_proposal(**{"PP-01": STATUS_PARTIAL}))
    assert result.verdict == VERDICT_NEEDS_WORK
    assert "PP-01" in result.partial_critical


def test_recommended_incomplete_is_needs_work():
    result = assess(_proposal(**{"PP-05": STATUS_UNMET}))
    assert result.verdict == VERDICT_NEEDS_WORK
    assert "PP-05" in result.other_incomplete
    assert result.unmet_critical == ()


def test_critical_unmet_outranks_partial():
    result = assess(_proposal(**{"PP-03": STATUS_UNMET, "PP-01": STATUS_PARTIAL}))
    assert result.verdict == VERDICT_NOT_READY


# --- 점수 집계 -------------------------------------------------------------
def test_partial_credits_half_weight():
    # 단일 권장(PP-05, weight=1)만 PARTIAL: 총가중 = 4*2 + 2*1 = 10.
    # credit = 8(crit MET) + 0.5*1(PP-05) + 1*1(PP-06) = 9.5 → 0.95.
    result = assess(_proposal(**{"PP-05": STATUS_PARTIAL}))
    assert result.score == 0.95


def test_score_deterministic():
    proposal = _proposal(**{"PP-01": STATUS_PARTIAL, "PP-05": STATUS_UNMET})
    assert assess(proposal).score == assess(proposal).score


# --- POLICY_MATRIX ↔ assess 일치 ------------------------------------------
def _construct_for_flags(critical_unmet, critical_partial, any_incomplete):
    """진리표 플래그 조합을 실현하는 제안서 구성(없으면 None)."""
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    if critical_unmet:
        statuses["PP-03"] = STATUS_UNMET
    if critical_partial:
        statuses["PP-01"] = STATUS_PARTIAL
    if any_incomplete and not critical_unmet and not critical_partial:
        statuses["PP-05"] = STATUS_UNMET
    proposal = PilotProposal(
        "matrix", "t", "J", statuses, ("simulation/geo_zones.py",)
    )
    result = assess(proposal)
    got_cu = bool(result.unmet_critical)
    got_cp = bool(result.partial_critical)
    got_ai = bool(
        result.unmet_critical or result.partial_critical or result.other_incomplete
    )
    if (got_cu, got_cp, got_ai) != (critical_unmet, critical_partial, any_incomplete):
        return None
    return proposal


@pytest.mark.parametrize("flags,expected", POLICY_MATRIX)
def test_policy_matrix_matches_assess(flags, expected):
    proposal = _construct_for_flags(*flags)
    assert proposal is not None, f"진리표 조합 {flags} 미실현"
    assert assess(proposal).verdict == expected


def test_policy_matrix_covers_all_realizable_flag_combos():
    keys = {k for k, _ in POLICY_MATRIX}
    for cu in (False, True):
        for cp in (False, True):
            for ai in (False, True):
                if (cu or cp) and not ai:
                    continue
                assert (cu, cp, ai) in keys


# --- 매니페스트 ------------------------------------------------------------
def test_manifest_json_serializable():
    manifest = criteria_manifest()
    dumped = json.dumps(manifest, ensure_ascii=False)
    assert json.loads(dumped) == manifest


def test_manifest_lists_all_criteria_matrix_and_proposals():
    manifest = criteria_manifest()
    assert len(manifest["criteria"]) == len(CRITERIA)
    assert len(manifest["policy_matrix"]) == len(POLICY_MATRIX)
    assert len(manifest["proposals"]) == len(shipped_proposals())
    assert manifest["verdicts"] == [
        VERDICT_READY_TO_PROPOSE,
        VERDICT_NEEDS_WORK,
        VERDICT_NOT_READY,
    ]


# --- 현 후보 3종 정직성 ----------------------------------------------------
def test_three_shipped_proposals():
    # 밴드 411-420 "해외 파일럿 제안서 3종".
    assert len(shipped_proposals()) == 3
    ids = {p.proposal_id for p in shipped_proposals()}
    assert ids == {"asean_island_delivery", "eu_uspace_demo", "us_university_research"}


def test_all_shipped_proposals_not_ready():
    # 격상 없이 현 상태 정직 공시: 세 후보 모두 현지 파트너(PP-03) 결격 → NOT_READY.
    for proposal in shipped_proposals():
        result = assess(proposal)
        assert result.verdict == VERDICT_NOT_READY
        assert "PP-03" in result.unmet_critical


def test_shipped_proposals_include_all_criteria():
    for proposal in shipped_proposals():
        assert set(proposal.statuses) == set(_CRITERION_IDS)


def test_asean_proposal_has_two_critical_unmet():
    # 아세안은 PP-03(현지 파트너) + PP-04(영문 산출물) 이중 CRITICAL 결격 — 정직성.
    a = assess(find_proposal("asean_island_delivery"))
    assert a.unmet_critical == ("PP-03", "PP-04")
    assert a.score == 0.3


@pytest.mark.parametrize(
    "pid,expected_score",
    [
        ("asean_island_delivery", 0.3),
        ("eu_uspace_demo", 0.55),
        ("us_university_research", 0.5),
    ],
)
def test_shipped_proposal_scores(pid, expected_score):
    # ROADMAP 자가 공시 점수와 정확 일치(상태 무단 격상 회귀 방지).
    assert assess(find_proposal(pid)).score == expected_score


def test_shipped_module_refs_exist_on_disk():
    # 정직성 결속: PP-02 근거로 인용한 모듈은 리포에 실재해야 한다.
    for proposal in shipped_proposals():
        assert missing_module_refs(proposal) == ()


def test_missing_module_refs_detects_absent_path():
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    proposal = PilotProposal("x", "t", "J", statuses, ("simulation/__nope__.py",))
    assert missing_module_refs(proposal) == ("simulation/__nope__.py",)


def test_find_proposal_round_trip():
    proposal = find_proposal("eu_uspace_demo")
    assert proposal.jurisdiction == "EU"


def test_find_proposal_unknown_raises():
    with pytest.raises(KeyError):
        find_proposal("mars_colony")


def test_most_ready_is_eu_demo():
    # EU U-space 데모가 PP-01·PP-02 MET 으로 최고 점수(동점 없음).
    result = most_ready()
    assert result.proposal_id == "eu_uspace_demo"
    assert result.verdict == VERDICT_NOT_READY  # 그래도 PP-03 결격


# --- CLI -------------------------------------------------------------------
def test_cli_default_criteria(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "PP-01" in out


def test_cli_status(capsys):
    assert main(["--status"]) == 0
    out = capsys.readouterr().out
    assert "판정" in out
    assert "ASEAN" in out


def test_cli_policy(capsys):
    assert main(["--policy"]) == 0
    out = capsys.readouterr().out
    assert VERDICT_NOT_READY in out


def test_cli_manifest_emits_json(capsys):
    assert main(["--manifest"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["schema"] == "sdacs-overseas-pilot-proposal"


def test_cli_unknown_flag_returns_2(capsys):
    assert main(["--bogus"]) == 2
    err = capsys.readouterr().err
    assert "알 수 없는 인자" in err
