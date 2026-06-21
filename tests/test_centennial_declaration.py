"""ODYSSEY Phase 500 — Centennial 선언 종합 게이트 테스트.

자매 모듈 위임(DRY)·all-or-nothing 선언·결정성·정직 공시·CLI 계약을 검증한다.
무작위성 0 — 같은 입력은 항상 같은 판정.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from simulation.centennial_declaration import (
    PILLAR_ARCHIVE,
    PILLAR_GOVERNANCE,
    PILLAR_HANDOVER,
    PILLAR_LEGACY,
    PILLARS,
    STATE_SATISFIED,
    STATE_UNMET,
    VERDICT_DECLARED,
    VERDICT_NOT_DECLARED,
    assess_centennial,
    declaration_manifest,
    main,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ALL_PILLAR_IDS = (PILLAR_LEGACY, PILLAR_ARCHIVE, PILLAR_GOVERNANCE, PILLAR_HANDOVER)
ALL_SATISFIED = dict.fromkeys(ALL_PILLAR_IDS, True)


# --- 레지스트리 무결성 -----------------------------------------------------

def test_pillars_registry_has_four_distinct_pillars():
    # Arrange / Act
    ids = [p.pillar_id for p in PILLARS]

    # Assert
    assert len(ids) == 4
    assert len(set(ids)) == 4


def test_each_pillar_delegates_to_a_sister_phase():
    # 모든 기둥은 자매 Phase(487~492)에 판정을 위임한다 — 자체 임계값 없음.
    for pillar in PILLARS:
        assert pillar.phase in (487, 489, 490, 492)


def test_pillar_ready_states_match_sister_terminal_verdicts():
    ready_by_id = {p.pillar_id: p.ready_state for p in PILLARS}
    assert ready_by_id[PILLAR_LEGACY] == "READY"
    assert ready_by_id[PILLAR_ARCHIVE] == "REDUNDANT"
    assert ready_by_id[PILLAR_GOVERNANCE] == "COMMITTEE_READY"
    assert ready_by_id[PILLAR_HANDOVER] == "HANDOFF_READY"


# --- all-or-nothing 선언 규칙 ----------------------------------------------

def test_all_pillars_satisfied_yields_declared():
    # Arrange / Act
    result = assess_centennial(REPO_ROOT, gate_overrides=ALL_SATISFIED)

    # Assert
    assert result.verdict == VERDICT_DECLARED
    assert result.is_declared() is True
    assert result.progress == 1.0
    assert result.unmet == ()


@pytest.mark.parametrize("missing", ALL_PILLAR_IDS)
def test_any_single_unmet_pillar_blocks_declaration(missing):
    # 한 기둥만 미충족이어도 선언 불가 — 네 기둥 모두 필요조건.
    overrides = dict(ALL_SATISFIED)
    overrides[missing] = False

    result = assess_centennial(REPO_ROOT, gate_overrides=overrides)

    assert result.verdict == VERDICT_NOT_DECLARED
    assert result.is_declared() is False
    assert missing in result.unmet
    assert result.progress == 0.75


def test_no_pillar_satisfied_yields_zero_progress():
    overrides = dict.fromkeys(ALL_PILLAR_IDS, False)

    result = assess_centennial(REPO_ROOT, gate_overrides=overrides)

    assert result.verdict == VERDICT_NOT_DECLARED
    assert result.progress == 0.0
    assert set(result.unmet) == set(ALL_PILLAR_IDS)
    assert result.satisfied == ()


def test_satisfied_and_unmet_are_sorted_and_partition_all_pillars():
    overrides = dict(ALL_SATISFIED)
    overrides[PILLAR_ARCHIVE] = False
    overrides[PILLAR_LEGACY] = False

    result = assess_centennial(REPO_ROOT, gate_overrides=overrides)

    assert list(result.satisfied) == sorted(result.satisfied)
    assert list(result.unmet) == sorted(result.unmet)
    assert set(result.satisfied) | set(result.unmet) == set(ALL_PILLAR_IDS)
    assert set(result.satisfied) & set(result.unmet) == set()


# --- 기둥별 상세(PillarStatus) ---------------------------------------------

def test_pillar_statuses_preserve_registry_order():
    result = assess_centennial(REPO_ROOT, gate_overrides=ALL_SATISFIED)

    assert tuple(s.pillar_id for s in result.pillars) == tuple(
        p.pillar_id for p in PILLARS
    )


def test_overridden_pillar_reports_injected_state():
    overrides = dict(ALL_SATISFIED)
    overrides[PILLAR_GOVERNANCE] = False

    result = assess_centennial(REPO_ROOT, gate_overrides=overrides)
    by_id = {s.pillar_id: s for s in result.pillars}

    assert by_id[PILLAR_GOVERNANCE].state == STATE_UNMET
    assert by_id[PILLAR_GOVERNANCE].is_satisfied() is False
    assert by_id[PILLAR_LEGACY].state == STATE_SATISFIED


# --- 정직 공시(현 리포 실측) -----------------------------------------------

def test_current_repo_is_not_declared():
    # 현 리포는 LICENSE/DOI/원저자 1인/차세대 미형성으로 네 기둥 모두 미충족.
    result = assess_centennial(REPO_ROOT)

    assert result.verdict == VERDICT_NOT_DECLARED
    assert result.is_declared() is False


def test_current_repo_pillar_details_cite_sister_phases():
    result = assess_centennial(REPO_ROOT)
    details = {s.pillar_id: s.detail for s in result.pillars}

    assert "Phase 490" in details[PILLAR_LEGACY]
    assert "Phase 489" in details[PILLAR_ARCHIVE]
    assert "Phase 487" in details[PILLAR_GOVERNANCE]
    assert "Phase 492" in details[PILLAR_HANDOVER]


# --- 결정성 ----------------------------------------------------------------

def test_assessment_is_deterministic():
    a = assess_centennial(REPO_ROOT)
    b = assess_centennial(REPO_ROOT)

    assert a == b


def test_override_assessment_is_deterministic():
    overrides = dict(ALL_SATISFIED)
    overrides[PILLAR_HANDOVER] = False

    a = assess_centennial(REPO_ROOT, gate_overrides=overrides)
    b = assess_centennial(REPO_ROOT, gate_overrides=overrides)

    assert a == b


# --- 입력 검증 -------------------------------------------------------------

def test_unknown_override_key_raises_key_error():
    with pytest.raises(KeyError):
        assess_centennial(REPO_ROOT, gate_overrides={"not_a_pillar": True})


def test_empty_overrides_equivalent_to_default():
    assert assess_centennial(REPO_ROOT, gate_overrides={}) == assess_centennial(
        REPO_ROOT
    )


def test_partial_override_uses_real_gates_for_remaining_pillars():
    # 두 기둥만 주입(충족)하고 나머지 둘은 실제 자매 게이트로 평가된다.
    # 현 리포에서 나머지 둘(거버넌스·이양)은 미충족이므로 선언 불가.
    overrides = {PILLAR_LEGACY: True, PILLAR_ARCHIVE: True}

    result = assess_centennial(REPO_ROOT, gate_overrides=overrides)
    by_id = {s.pillar_id: s for s in result.pillars}

    assert result.verdict == VERDICT_NOT_DECLARED
    assert set(result.satisfied) == {PILLAR_LEGACY, PILLAR_ARCHIVE}
    # 주입 기둥은 주입값, 미주입 기둥은 실제 게이트 근거(자매 Phase 인용).
    assert by_id[PILLAR_LEGACY].detail.startswith("주입값")
    assert "Phase 487" in by_id[PILLAR_GOVERNANCE].detail
    assert "Phase 492" in by_id[PILLAR_HANDOVER].detail


# --- 매니페스트 ------------------------------------------------------------

def test_manifest_is_json_serializable_and_lists_all_pillars():
    manifest = declaration_manifest()
    dumped = json.dumps(manifest, ensure_ascii=False)

    assert manifest["schema"] == "sdacs-centennial-declaration"
    assert {p["id"] for p in manifest["pillars"]} == set(ALL_PILLAR_IDS)
    assert json.loads(dumped) == manifest


def test_manifest_verdicts_are_binary():
    manifest = declaration_manifest()

    assert manifest["verdicts"] == [VERDICT_DECLARED, VERDICT_NOT_DECLARED]


# --- CLI 계약 --------------------------------------------------------------

def test_cli_pillars_returns_zero(capsys):
    rc = main(["--pillars"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "PILLAR" in out


def test_cli_status_returns_zero_and_shows_verdict(capsys):
    rc = main(["--status"])
    out = capsys.readouterr().out

    assert rc == 0
    assert VERDICT_NOT_DECLARED in out


def test_cli_manifest_emits_valid_json(capsys):
    rc = main(["--manifest"])
    out = capsys.readouterr().out

    assert rc == 0
    assert json.loads(out)["schema"] == "sdacs-centennial-declaration"


def test_cli_unknown_flag_returns_two(capsys):
    rc = main(["--bogus"])
    err = capsys.readouterr().err

    assert rc == 2
    assert "알 수 없는 인자" in err


def test_cli_default_is_pillars(capsys):
    rc = main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert "기둥 매트릭스" in out


# --- 자매 모듈 정합(회귀 핀) ----------------------------------------------

def test_summary_reflects_verdict_and_progress():
    declared = assess_centennial(REPO_ROOT, gate_overrides=ALL_SATISFIED)
    not_declared = assess_centennial(REPO_ROOT)

    assert declared.verdict in declared.summary()
    assert "100.0%" in declared.summary()
    assert not_declared.verdict in not_declared.summary()
