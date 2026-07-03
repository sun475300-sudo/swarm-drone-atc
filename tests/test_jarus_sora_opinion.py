"""ODYSSEY 밴드 첫 후보 완결 — JARUS SORA 군집 보완 의견서 검증 테스트.

핵심 계약: 동봉 문서 디스크 증거로부터 기준별 상태 결정적 도출(절 실재→MET·
부재→UNMET·redline 센티넬 부재→PARTIAL·WG-06 외부 의존 PARTIAL 상한),
판정의 Phase 472 위임(복제 0), Phase 472 `shipped_letter` 의 본 모듈 위임
(하드코딩 스냅샷 제거), 현 산출물 정직 공시(redline 완성으로 0.95·
NEEDS_WORK — 외부 기한 천장), Phase 473 포트폴리오 라벨 정합, 결정론·
매니페스트 JSON 직렬화·CLI.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from simulation.intl_wg_opinion_gate import (
    CRITERIA,
    STATUS_MET,
    STATUS_PARTIAL,
    STATUS_UNMET,
    VERDICT_NEEDS_WORK,
    VERDICT_NOT_READY,
    OpinionLetter,
    assess,
)
from simulation.jarus_sora_opinion import (
    DOC_PATH,
    TARGET_LABEL,
    assess_letter,
    authored_letter,
    evidence,
    main,
    manifest,
)

pytestmark = pytest.mark.unit

_CRITERION_IDS = tuple(c.criterion_id for c in CRITERIA)


# --- 동봉 문서 실재 --------------------------------------------------------
def test_companion_document_exists():
    # 의견서 문서가 리포에 실재해야 증거 결속이 의미를 갖는다.
    assert DOC_PATH.is_file()


def test_document_contains_all_required_anchors():
    text = DOC_PATH.read_text(encoding="utf-8")
    for ev in evidence():
        assert ev.anchor in text, f"필수 절 부재: {ev.anchor}"


# --- 증거 → 상태 도출 (실 문서) --------------------------------------------
def test_evidence_covers_every_criterion_exactly_once():
    ids = [ev.criterion_id for ev in evidence()]
    assert sorted(ids) == sorted(_CRITERION_IDS)
    assert len(ids) == len(set(ids))


def test_shipped_statuses_reflect_completed_redline():
    # 실 문서 기준: WG-01~WG-05 MET(절 실재), WG-06 PARTIAL(외부 기한 천장).
    by_id = {ev.criterion_id: ev.status for ev in evidence()}
    assert by_id["WG-01"] == STATUS_MET
    assert by_id["WG-02"] == STATUS_MET  # redline After 센티넬 실재
    assert by_id["WG-03"] == STATUS_MET
    assert by_id["WG-04"] == STATUS_MET
    assert by_id["WG-05"] == STATUS_MET
    assert by_id["WG-06"] == STATUS_PARTIAL


def test_wg06_is_partial_not_met_even_with_section():
    # 외부 회람 기한 의존 — 채널 절이 있어도 MET 으로 격상되지 않는다.
    by_id = {ev.criterion_id: ev.status for ev in evidence()}
    assert by_id["WG-06"] != STATUS_MET


# --- 판정 위임 (DRY) -------------------------------------------------------
def test_assess_delegates_to_phase472_gate():
    # 판정은 Phase 472 assess 결과와 정확히 일치(복제 아님).
    assert assess_letter() == assess(authored_letter())


def test_shipped_verdict_is_needs_work_at_score_095():
    result = assess_letter()
    assert result.verdict == VERDICT_NEEDS_WORK
    assert result.score == pytest.approx(0.95, abs=1e-4)


def test_authored_letter_is_valid_opinion_letter():
    letter = authored_letter()
    assert isinstance(letter, OpinionLetter)
    assert letter.target == TARGET_LABEL
    # 모든 기준 id 를 빠짐없이 포함(Phase 472 불변식).
    assert set(letter.statuses) == set(_CRITERION_IDS)


def test_phase472_shipped_letter_delegates_here():
    # Phase 472 shipped_letter 는 본 작성 결과를 위임 재사용한다(스냅샷 복제 0).
    from simulation.intl_wg_opinion_gate import shipped_letter

    assert shipped_letter() == authored_letter()


def test_target_label_matches_portfolio_registration():
    # Phase 473 포트폴리오가 등록하는 라벨과 동일해야 위임 재사용이 성립한다.
    from simulation.wg_opinion_portfolio import portfolio

    assert any(e.label == TARGET_LABEL for e in portfolio())


# --- 증거 부재·미완 경로 (tmp 문서) ----------------------------------------
def test_missing_document_all_unmet_critical_not_ready(tmp_path: Path):
    missing = tmp_path / "absent.md"
    statuses = {ev.criterion_id: ev.status for ev in evidence(missing)}
    # 문서 부재 → 모든 절 부재 → CRITICAL UNMET → NOT_READY.
    assert all(s == STATUS_UNMET for s in statuses.values())
    assert assess_letter(missing).verdict == VERDICT_NOT_READY


def test_redline_section_without_sentinel_is_partial(tmp_path: Path):
    # WG-02 절 제목은 있으나 실행 가능한 After 문안(센티넬) 부재 → PARTIAL.
    doc = tmp_path / "draft.md"
    text = DOC_PATH.read_text(encoding="utf-8").replace("**After (제안):**", "(추후 작성)")
    doc.write_text(text, encoding="utf-8")
    by_id = {ev.criterion_id: ev.status for ev in evidence(doc)}
    assert by_id["WG-02"] == STATUS_PARTIAL


def test_note_content_distinguishes_branches(tmp_path: Path):
    # MET 분기 note(실 문서) 와 PARTIAL+sentinel 분기 note(센티넬 제거) 를 직접 확인.
    met_note = {ev.criterion_id: ev.note for ev in evidence()}["WG-01"]
    assert "충족" in met_note

    doc = tmp_path / "draft.md"
    text = DOC_PATH.read_text(encoding="utf-8").replace("**After (제안):**", "(추후 작성)")
    doc.write_text(text, encoding="utf-8")
    partial_note = {ev.criterion_id: ev.note for ev in evidence(doc)}["WG-02"]
    assert "센티넬" in partial_note and "부분" in partial_note


def test_partial_redline_yields_lower_score(tmp_path: Path):
    # 센티넬 제거(redline 미완) 시 점수가 실 문서(0.95)보다 낮아야 한다.
    doc = tmp_path / "draft.md"
    text = DOC_PATH.read_text(encoding="utf-8").replace("**After (제안):**", "(추후 작성)")
    doc.write_text(text, encoding="utf-8")
    assert assess_letter(doc).score < assess_letter().score


# --- 결정론 ----------------------------------------------------------------
def test_deterministic():
    assert assess_letter() == assess_letter()
    assert evidence() == evidence()


# --- 매니페스트 ------------------------------------------------------------
def test_manifest_json_serialisable():
    blob = json.dumps(manifest(), ensure_ascii=False)
    restored = json.loads(blob)
    assert restored["schema"] == "sdacs-jarus-sora-opinion"
    assert restored["band"] == "471-480"
    assert restored["verdict"] == VERDICT_NEEDS_WORK
    assert len(restored["evidence"]) == len(_CRITERION_IDS)


def test_manifest_verdict_matches_assess():
    blob = manifest()
    result = assess_letter()
    assert blob["verdict"] == result.verdict
    assert blob["score"] == result.score


# --- CLI -------------------------------------------------------------------
@pytest.mark.parametrize("flag", ["--evidence", "--status", "--manifest"])
def test_cli_known_flags_succeed(flag, capsys):
    assert main([flag]) == 0
    out = capsys.readouterr().out
    assert out.strip()


def test_cli_default_is_evidence(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "WG-01" in out


def test_cli_unknown_flag_errors(capsys):
    assert main(["--bogus"]) == 2
    err = capsys.readouterr().err
    assert "알 수 없는 인자" in err


def test_cli_manifest_emits_valid_json(capsys):
    assert main(["--manifest"]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["schema"] == "sdacs-jarus-sora-opinion"
