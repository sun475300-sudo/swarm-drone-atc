"""ODYSSEY Phase 472 — 국제 워킹그룹 의견서 적합성 게이트 테스트.

핵심 계약 검증: 기준 무결성·입력 검증(누락/미지 id/미지 상태)·판정 우선순위
(CRITICAL UNMET → NOT_READY > CRITICAL PARTIAL → NEEDS_WORK > 잔여 미완 →
NEEDS_WORK > 전부 MET → READY)·POLICY_MATRIX ↔ assess 정확 일치·가중 점수
집계(PARTIAL=절반)·결정론·매니페스트 JSON 직렬화·CLI·현 후보 정직성.
"""
from __future__ import annotations

import json

import pytest

from simulation.intl_wg_opinion_gate import (
    CRITERIA,
    POLICY_MATRIX,
    SEVERITY_CRITICAL,
    SEVERITY_RECOMMENDED,
    STATUS_MET,
    STATUS_PARTIAL,
    STATUS_UNMET,
    VERDICT_NEEDS_WORK,
    VERDICT_NOT_READY,
    VERDICT_READY_TO_SUBMIT,
    OpinionCriterion,
    OpinionLetter,
    assess,
    criteria_manifest,
    main,
    shipped_letter,
)

pytestmark = pytest.mark.unit

_CRITERION_IDS = tuple(c.criterion_id for c in CRITERIA)


def _letter(**overrides: str) -> OpinionLetter:
    """기본 전부 MET 의견서에 일부 기준만 덮어쓴 후보 생성."""
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    statuses.update(overrides)
    return OpinionLetter(target="테스트 대상", statuses=statuses)


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


# --- 입력 검증 -------------------------------------------------------------
def test_missing_criterion_rejected():
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    del statuses["WG-01"]
    with pytest.raises(ValueError, match="누락"):
        OpinionLetter(target="x", statuses=statuses)


def test_unknown_criterion_rejected():
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    statuses["WG-99"] = STATUS_MET
    with pytest.raises(ValueError, match="알 수 없는 기준"):
        OpinionLetter(target="x", statuses=statuses)


def test_unknown_status_rejected():
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    statuses["WG-01"] = "MAYBE"
    with pytest.raises(ValueError, match="알 수 없는 상태"):
        OpinionLetter(target="x", statuses=statuses)


def test_statuses_are_read_only_after_construction():
    # frozen 의 불변 보장이 dict 내용까지 확장됐는지 — 외부 변형 차단.
    letter = _letter()
    with pytest.raises(TypeError):
        letter.statuses["WG-01"] = STATUS_UNMET  # type: ignore[index]


def test_criterion_rejects_unknown_severity():
    with pytest.raises(ValueError, match="알 수 없는 심각도"):
        OpinionCriterion("X", "TYPO", "desc", "rationale")


# --- 판정 우선순위 ---------------------------------------------------------
def test_all_met_is_ready():
    result = assess(_letter())
    assert result.verdict == VERDICT_READY_TO_SUBMIT
    assert result.is_ready()
    assert result.score == 1.0
    assert result.met == tuple(sorted(_CRITERION_IDS))  # 정렬·전체


def test_critical_unmet_is_not_ready():
    result = assess(_letter(**{"WG-02": STATUS_UNMET}))
    assert result.verdict == VERDICT_NOT_READY
    assert "WG-02" in result.unmet_critical


def test_critical_partial_is_needs_work():
    result = assess(_letter(**{"WG-03": STATUS_PARTIAL}))
    assert result.verdict == VERDICT_NEEDS_WORK
    assert "WG-03" in result.partial_critical


def test_recommended_incomplete_is_needs_work():
    # CRITICAL 전부 충족, 권장 하나만 UNMET → NEEDS_WORK (제출 차단 아님).
    result = assess(_letter(**{"WG-05": STATUS_UNMET}))
    assert result.verdict == VERDICT_NEEDS_WORK
    assert "WG-05" in result.other_incomplete
    assert result.unmet_critical == ()


def test_critical_unmet_outranks_partial():
    # CRITICAL UNMET 과 CRITICAL PARTIAL 공존 → NOT_READY 우선.
    result = assess(_letter(**{"WG-01": STATUS_UNMET, "WG-02": STATUS_PARTIAL}))
    assert result.verdict == VERDICT_NOT_READY


# --- 점수 집계 -------------------------------------------------------------
def test_partial_credits_half_weight():
    # 단일 권장(WG-05, weight=1)만 PARTIAL: 총가중 = 4*2 + 2*1 = 10.
    # credit = 8(crit MET) + 0.5*1(WG-05) + 1*1(WG-06) = 9.5 → 0.95.
    result = assess(_letter(**{"WG-05": STATUS_PARTIAL}))
    assert result.score == 0.95


def test_shipped_letter_score_is_exact():
    # WG-02 PARTIAL(weight 2) + WG-06 UNMET(weight 1), 총가중 10:
    # credit = 10 - 0.5*2 - 1*1 = 8.0 → 0.8.
    assert assess(shipped_letter()).score == 0.8


def test_score_deterministic():
    letter = _letter(**{"WG-02": STATUS_PARTIAL, "WG-05": STATUS_UNMET})
    assert assess(letter).score == assess(letter).score


# --- POLICY_MATRIX ↔ assess 일치 ------------------------------------------
def _construct_for_flags(critical_unmet, critical_partial, any_incomplete):
    """진리표 플래그 조합을 실현하는 의견서 구성(없으면 None)."""
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    if critical_unmet:
        statuses["WG-01"] = STATUS_UNMET
    if critical_partial:
        statuses["WG-02"] = STATUS_PARTIAL
    # any_incomplete 가 True 인데 위 둘이 모두 False 면 권장 칸으로 미완 유발.
    if any_incomplete and not critical_unmet and not critical_partial:
        statuses["WG-05"] = STATUS_UNMET
    letter = OpinionLetter(target="matrix", statuses=statuses)
    # 구성된 의견서가 의도한 플래그를 실제로 갖는지 확인(자기 일관성).
    result = assess(letter)
    got_cu = bool(result.unmet_critical)
    got_cp = bool(result.partial_critical)
    got_ai = bool(
        result.unmet_critical or result.partial_critical or result.other_incomplete
    )
    if (got_cu, got_cp, got_ai) != (critical_unmet, critical_partial, any_incomplete):
        return None
    return letter


@pytest.mark.parametrize("flags,expected", POLICY_MATRIX)
def test_policy_matrix_matches_assess(flags, expected):
    letter = _construct_for_flags(*flags)
    assert letter is not None, f"진리표 조합 {flags} 미실현"
    assert assess(letter).verdict == expected


def test_policy_matrix_covers_all_realizable_flag_combos():
    # 진리표가 모순 없는 모든 (cu, cp, ai) 조합을 빠짐없이 담는지 확인.
    keys = {k for k, _ in POLICY_MATRIX}
    for cu in (False, True):
        for cp in (False, True):
            for ai in (False, True):
                # CRITICAL UNMET/PARTIAL 은 ai=True 를 강제 → ai=False 면 모순.
                if (cu or cp) and not ai:
                    continue
                assert (cu, cp, ai) in keys


# --- 매니페스트 ------------------------------------------------------------
def test_manifest_json_serializable():
    manifest = criteria_manifest()
    dumped = json.dumps(manifest, ensure_ascii=False)
    assert json.loads(dumped) == manifest


def test_manifest_lists_all_criteria_and_matrix():
    manifest = criteria_manifest()
    assert len(manifest["criteria"]) == len(CRITERIA)
    assert len(manifest["policy_matrix"]) == len(POLICY_MATRIX)
    assert manifest["verdicts"] == [
        VERDICT_READY_TO_SUBMIT,
        VERDICT_NEEDS_WORK,
        VERDICT_NOT_READY,
    ]


# --- 현 후보 정직성 --------------------------------------------------------
def test_shipped_letter_is_needs_work():
    # 격상 없이 현 상태를 정직 공시: NEEDS_WORK (WG-02 부분·WG-06 미충족).
    result = assess(shipped_letter())
    assert result.verdict == VERDICT_NEEDS_WORK
    assert "WG-02" in result.partial_critical
    assert "WG-06" in result.other_incomplete
    assert result.unmet_critical == ()


def test_shipped_letter_includes_all_criteria():
    letter = shipped_letter()
    assert set(letter.statuses) == set(_CRITERION_IDS)


# --- CLI -------------------------------------------------------------------
def test_cli_default_criteria(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "WG-01" in out


def test_cli_status(capsys):
    assert main(["--status"]) == 0
    out = capsys.readouterr().out
    assert "판정" in out


def test_cli_policy(capsys):
    assert main(["--policy"]) == 0
    out = capsys.readouterr().out
    assert VERDICT_NOT_READY in out


def test_cli_manifest_emits_json(capsys):
    assert main(["--manifest"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["schema"] == "sdacs-intl-wg-opinion-gate"


def test_cli_unknown_flag_returns_2(capsys):
    assert main(["--bogus"]) == 2
    err = capsys.readouterr().err
    assert "알 수 없는 인자" in err
