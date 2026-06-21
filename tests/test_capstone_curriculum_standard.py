"""ODYSSEY Phase 468 — 대학 캡스톤 표준 커리큘럼 제안 적합성 게이트 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.capstone_curriculum_standard import (
    ABEEK_OUTCOMES,
    ADOPTION_STAGES,
    CURRENT_ADOPTION,
    CURRICULUM_UNITS,
    REQUIRED_OUTCOMES,
    STATUSES,
    TOTAL_WEEKS,
    VERDICT_NOT_READY,
    VERDICT_PARTIAL,
    VERDICT_READY,
    CurriculumReadiness,
    CurriculumUnit,
    _verdict_for,
    assess_curriculum,
    coverage_matrix,
    curriculum_matrix,
    evidence_present,
    find_unit,
    main,
    units_by_outcome,
    units_by_status,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _unit(**kw) -> CurriculumUnit:
    """작성 기본값으로 CurriculumUnit 을 만든다 (테스트 편의)."""
    defaults = dict(
        unit_id="U01",
        weeks=(1, 2),
        title="공역 통제 문제 정의",
        outcomes=("PO1", "PO4"),
        status="DRAFTED",
        evidence=("docs/standards/CAPSTONE_CURRICULUM_STANDARD.md",),
        summary="s",
    )
    defaults.update(kw)
    return CurriculumUnit(**defaults)


# --- CurriculumUnit 불변식 ---------------------------------------------------

def test_unit_rejects_blank_id():
    with pytest.raises(ValueError):
        _unit(unit_id="")


def test_unit_rejects_padded_id():
    with pytest.raises(ValueError):
        _unit(unit_id=" U01 ")


def test_unit_rejects_id_with_space():
    with pytest.raises(ValueError):
        _unit(unit_id="U 01")


def test_unit_rejects_blank_title():
    with pytest.raises(ValueError):
        _unit(title="  ")


def test_unit_rejects_blank_summary():
    with pytest.raises(ValueError):
        _unit(summary="")


def test_unit_rejects_unknown_status():
    with pytest.raises(ValueError):
        _unit(status="WIP")


def test_unit_rejects_empty_weeks():
    with pytest.raises(ValueError):
        _unit(weeks=())


def test_unit_rejects_duplicate_weeks():
    with pytest.raises(ValueError):
        _unit(weeks=(1, 1))


def test_unit_rejects_week_out_of_range_low():
    with pytest.raises(ValueError):
        _unit(weeks=(0,))


def test_unit_rejects_week_out_of_range_high():
    with pytest.raises(ValueError):
        _unit(weeks=(TOTAL_WEEKS + 1,))


def test_unit_rejects_unsorted_weeks():
    with pytest.raises(ValueError):
        _unit(weeks=(2, 1))


def test_unit_rejects_empty_outcomes():
    with pytest.raises(ValueError):
        _unit(outcomes=())


def test_unit_rejects_duplicate_outcomes():
    with pytest.raises(ValueError):
        _unit(outcomes=("PO1", "PO1"))


def test_unit_rejects_unknown_outcome():
    with pytest.raises(ValueError):
        _unit(outcomes=("PO99",))


def test_unit_rejects_padded_evidence_path():
    with pytest.raises(ValueError):
        _unit(evidence=(" docs/x.md",))


def test_drafted_unit_must_cite_evidence():
    with pytest.raises(ValueError):
        _unit(status="DRAFTED", evidence=())


def test_missing_unit_must_not_cite_evidence():
    with pytest.raises(ValueError):
        _unit(status="MISSING", evidence=("docs/x.md",))


def test_outlined_unit_may_have_or_omit_evidence():
    # OUTLINED 는 증거 결속이 없다 — 양쪽 모두 유효(거짓 결속 없음).
    assert _unit(status="OUTLINED", evidence=()).status == "OUTLINED"
    assert _unit(
        status="OUTLINED",
        evidence=("docs/standards/CAPSTONE_CURRICULUM_STANDARD.md",),
    ).status == "OUTLINED"


def test_unit_rejects_noncontiguous_weeks():
    with pytest.raises(ValueError):
        _unit(weeks=(1, 3))


def test_unit_weight_by_status():
    assert _unit(status="DRAFTED").weight == 1.0
    assert _unit(status="OUTLINED", evidence=()).weight == 0.5
    assert _unit(status="MISSING", evidence=()).weight == 0.0


def test_unit_is_drafted():
    assert _unit(status="DRAFTED").is_drafted is True
    assert _unit(status="OUTLINED", evidence=()).is_drafted is False


# --- 레지스트리 무결성 -------------------------------------------------------

def test_registry_ids_unique():
    ids = [u.unit_id for u in CURRICULUM_UNITS]
    assert len(ids) == len(set(ids))


def test_registry_weeks_no_overlap():
    weeks = [wk for u in CURRICULUM_UNITS for wk in u.weeks]
    assert len(weeks) == len(set(weeks))


def test_registry_covers_all_15_weeks():
    weeks = {wk for u in CURRICULUM_UNITS for wk in u.weeks}
    assert weeks == set(range(1, TOTAL_WEEKS + 1))


def test_registry_outcomes_are_known():
    for u in CURRICULUM_UNITS:
        for code in u.outcomes:
            assert code in ABEEK_OUTCOMES


def test_required_outcomes_subset_of_known():
    assert set(ABEEK_OUTCOMES) >= REQUIRED_OUTCOMES


def test_registry_evidence_files_exist():
    for u in CURRICULUM_UNITS:
        assert evidence_present(u, REPO_ROOT), f"missing evidence: {u.unit_id}"


# --- 조회 API ----------------------------------------------------------------

def test_find_unit_known():
    assert find_unit("U01").unit_id == "U01"


def test_find_unit_unknown_raises():
    with pytest.raises(KeyError):
        find_unit("U99")


def test_units_by_status_sorted():
    drafted = units_by_status("DRAFTED")
    ids = [u.unit_id for u in drafted]
    assert ids == sorted(ids)
    assert all(u.status == "DRAFTED" for u in drafted)


def test_units_by_status_invalid():
    with pytest.raises(ValueError):
        units_by_status("WIP")


def test_units_by_outcome_known():
    units = units_by_outcome("PO1")
    assert all("PO1" in u.outcomes for u in units)
    ids = [u.unit_id for u in units]
    assert ids == sorted(ids)


def test_units_by_outcome_unknown():
    with pytest.raises(ValueError):
        units_by_outcome("PO99")


# --- 준비도 판정 -------------------------------------------------------------

def test_assess_returns_readiness():
    r = assess_curriculum(REPO_ROOT)
    assert isinstance(r, CurriculumReadiness)


def test_assess_current_repo_is_partial():
    # U09 가 OUTLINED 라 PARTIAL, 필수 학습성과는 전부 커버.
    r = assess_curriculum(REPO_ROOT)
    assert r.verdict == VERDICT_PARTIAL
    assert "U09" in r.incomplete
    assert r.uncovered_required == ()


def test_assess_all_15_weeks_covered():
    r = assess_curriculum(REPO_ROOT)
    assert r.weeks_covered == TOTAL_WEEKS


def test_assess_required_outcomes_all_covered():
    r = assess_curriculum(REPO_ROOT)
    assert set(r.covered_outcomes) >= REQUIRED_OUTCOMES


def test_assess_adoption_is_not_proposed():
    r = assess_curriculum(REPO_ROOT)
    assert r.adoption_status == CURRENT_ADOPTION == "NOT_PROPOSED"
    assert r.is_adopted() is False


def test_assess_score_in_range():
    r = assess_curriculum(REPO_ROOT)
    assert 0.0 <= r.score <= 1.0


def test_assess_score_deterministic():
    assert assess_curriculum(REPO_ROOT).score == assess_curriculum(REPO_ROOT).score


def test_missing_evidence_dir_yields_not_drafted(tmp_path):
    # 증거가 하나도 실재하지 않는 빈 리포 → 자료 완비 0·필수 미커버 → NOT_READY.
    r = assess_curriculum(tmp_path)
    assert r.verdict == VERDICT_NOT_READY
    assert r.drafted == ()
    assert set(r.uncovered_required) == set(REQUIRED_OUTCOMES)


def test_empty_dir_score_is_zero(tmp_path):
    r = assess_curriculum(tmp_path)
    assert r.score == 0.0


# --- 교차 불변식: _verdict_for 직접 검증 (463 대비 핵심 신규성) ----------------

def test_verdict_uncovered_required_beats_incomplete():
    # 모든 단원이 완비(incomplete 없음)여도 필수 학습성과 미커버면 NOT_READY.
    assert _verdict_for(
        has_units=True, has_incomplete=False, uncovered_required=True
    ) == VERDICT_NOT_READY


def test_verdict_uncovered_required_with_incomplete_is_not_ready():
    assert _verdict_for(
        has_units=True, has_incomplete=True, uncovered_required=True
    ) == VERDICT_NOT_READY


def test_verdict_incomplete_only_is_partial():
    assert _verdict_for(
        has_units=True, has_incomplete=True, uncovered_required=False
    ) == VERDICT_PARTIAL


def test_verdict_all_satisfied_is_ready():
    assert _verdict_for(
        has_units=True, has_incomplete=False, uncovered_required=False
    ) == VERDICT_READY


def test_verdict_empty_registry_never_ready():
    # 공허 참 차단: 단원이 없으면 미커버·미완이 모두 거짓이어도 READY 금지.
    assert _verdict_for(
        has_units=False, has_incomplete=False, uncovered_required=False
    ) == VERDICT_NOT_READY


def test_readiness_summary_mentions_adoption():
    r = assess_curriculum(REPO_ROOT)
    assert "NOT_PROPOSED" in r.summary()


def test_readiness_rejects_bad_verdict():
    with pytest.raises(ValueError):
        CurriculumReadiness(
            verdict="BOGUS", score=1.0, adoption_status="NOT_PROPOSED",
            drafted=(), incomplete=(), covered_outcomes=(),
            uncovered_required=(), weeks_covered=0,
        )


def test_readiness_rejects_bad_adoption():
    with pytest.raises(ValueError):
        CurriculumReadiness(
            verdict=VERDICT_READY, score=1.0, adoption_status="LAUNCHED",
            drafted=(), incomplete=(), covered_outcomes=(),
            uncovered_required=(), weeks_covered=0,
        )


def test_readiness_rejects_score_out_of_range():
    with pytest.raises(ValueError):
        CurriculumReadiness(
            verdict=VERDICT_READY, score=1.5, adoption_status="NOT_PROPOSED",
            drafted=(), incomplete=(), covered_outcomes=(),
            uncovered_required=(), weeks_covered=0,
        )


def test_readiness_rejects_weeks_out_of_range():
    with pytest.raises(ValueError):
        CurriculumReadiness(
            verdict=VERDICT_READY, score=1.0, adoption_status="NOT_PROPOSED",
            drafted=(), incomplete=(), covered_outcomes=(),
            uncovered_required=(), weeks_covered=TOTAL_WEEKS + 1,
        )


# --- 매트릭스 / 커버리지 -----------------------------------------------------

def test_curriculum_matrix_order_preserved():
    rows = curriculum_matrix()
    assert [r["unit_id"] for r in rows] == [u.unit_id for u in CURRICULUM_UNITS]


def test_curriculum_matrix_fields():
    row = curriculum_matrix()[0]
    assert set(row) == {
        "unit_id", "weeks", "title", "outcomes", "status", "evidence", "summary"
    }


def test_coverage_matrix_marks_required():
    rows = {r["outcome"]: r for r in coverage_matrix(REPO_ROOT)}
    for code in REQUIRED_OUTCOMES:
        assert rows[code]["required"] is True
        assert rows[code]["covered"] is True


def test_coverage_matrix_all_outcomes_present():
    rows = coverage_matrix(REPO_ROOT)
    assert {r["outcome"] for r in rows} == set(ABEEK_OUTCOMES)


def test_coverage_matrix_empty_repo_uncovered(tmp_path):
    rows = {r["outcome"]: r for r in coverage_matrix(tmp_path)}
    assert all(not r["covered"] for r in rows.values())


# --- 상수 / CLI --------------------------------------------------------------

def test_statuses_disjoint_known():
    assert set(STATUSES) == {"DRAFTED", "OUTLINED", "MISSING"}


def test_adoption_stages_monotone():
    assert ADOPTION_STAGES[0] == "NOT_PROPOSED"
    assert ADOPTION_STAGES[-1] == "ADOPTED"


def test_main_report_runs(capsys):
    assert main(["--report"]) == 0
    assert "준비도" in capsys.readouterr().out


def test_main_matrix_runs(capsys):
    assert main(["--matrix"]) == 0
    assert "공역" in capsys.readouterr().out


def test_main_coverage_runs(capsys):
    assert main(["--coverage"]) == 0
    assert "PO1" in capsys.readouterr().out


def test_main_gaps_runs(capsys):
    assert main(["--gaps"]) == 0
    assert "U09" in capsys.readouterr().out


def test_main_adoption_runs(capsys):
    assert main(["--adoption"]) == 0
    assert "NOT_PROPOSED" in capsys.readouterr().out


def test_main_default_runs(capsys):
    assert main([]) == 0
    assert "준비도" in capsys.readouterr().out
