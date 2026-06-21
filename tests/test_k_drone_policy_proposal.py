"""ODYSSEY Phase 463 — K-드론 시스템 고도화 정책 제안서 적합성 게이트 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.k_drone_policy_proposal import (
    CRITICALITIES,
    CURRENT_SUBMISSION,
    PROPOSAL_SECTIONS,
    STATUSES,
    SUBMISSION_STAGES,
    VERDICT_NOT_READY,
    VERDICT_PARTIAL,
    VERDICT_READY,
    ProposalReadiness,
    ProposalSection,
    assess_readiness,
    evidence_present,
    find_section,
    main,
    proposal_matrix,
    sections_by_status,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _section(**kw) -> ProposalSection:
    """작성·필수 기본값으로 ProposalSection 을 만든다 (테스트 편의)."""
    defaults = dict(
        section_id="improvement-plan",
        title="정책 개선 방안",
        criticality="REQUIRED",
        status="DRAFTED",
        evidence=("docs/standards/K_DRONE_POLICY_PROPOSAL.md",),
        summary="s",
    )
    defaults.update(kw)
    return ProposalSection(**defaults)  # type: ignore[arg-type]


# --- ProposalSection 검증 --------------------------------------------------

def test_section_rejects_empty_id():
    with pytest.raises(ValueError):
        _section(section_id="")


def test_section_rejects_padded_id():
    with pytest.raises(ValueError):
        _section(section_id=" background ")


def test_section_rejects_internal_space_id():
    with pytest.raises(ValueError):
        _section(section_id="back ground")


def test_section_rejects_empty_title():
    with pytest.raises(ValueError):
        _section(title="  ")


def test_section_rejects_empty_summary():
    with pytest.raises(ValueError):
        _section(summary="")


def test_section_rejects_bad_criticality():
    with pytest.raises(ValueError):
        _section(criticality="OPTIONAL")


def test_section_rejects_bad_status():
    with pytest.raises(ValueError):
        _section(status="WIP")


def test_section_rejects_non_tuple_evidence():
    with pytest.raises(ValueError):
        _section(evidence=["a"])  # type: ignore[arg-type]


def test_section_rejects_padded_evidence_path():
    with pytest.raises(ValueError):
        _section(evidence=(" x ",))


def test_drafted_requires_evidence():
    with pytest.raises(ValueError):
        _section(status="DRAFTED", evidence=())


def test_missing_forbids_evidence():
    with pytest.raises(ValueError):
        _section(status="MISSING", evidence=("x",))


def test_missing_with_empty_evidence_ok():
    s = _section(status="MISSING", evidence=())
    assert s.status == "MISSING"


def test_outlined_allows_empty_evidence():
    s = _section(status="OUTLINED", evidence=())
    assert s.status == "OUTLINED"


# --- 속성 ------------------------------------------------------------------

def test_is_required():
    assert _section(criticality="REQUIRED").is_required
    assert not _section(criticality="RECOMMENDED").is_required


def test_is_drafted():
    assert _section(status="DRAFTED").is_drafted
    assert not _section(status="MISSING", evidence=()).is_drafted


def test_weight_values():
    assert _section(status="DRAFTED").weight == 1.0
    assert _section(status="OUTLINED", evidence=()).weight == 0.5
    assert _section(status="MISSING", evidence=()).weight == 0.0


# --- 레지스트리 무결성 ------------------------------------------------------

def test_registry_non_empty():
    assert len(PROPOSAL_SECTIONS) >= 6


def test_registry_unique_ids():
    ids = [s.section_id for s in PROPOSAL_SECTIONS]
    assert len(ids) == len(set(ids))


def test_registry_all_evidence_files_exist():
    """모든 인용 증거 산출물이 디스크에 실재해야 한다 (정직성 강제)."""
    for s in PROPOSAL_SECTIONS:
        for rel in s.evidence:
            assert os.path.isfile(os.path.join(REPO_ROOT, rel)), rel


def test_registry_has_required_sections():
    assert any(s.is_required for s in PROPOSAL_SECTIONS)


def test_constants_well_formed():
    assert set(STATUSES) == {"DRAFTED", "OUTLINED", "MISSING"}
    assert set(CRITICALITIES) == {"REQUIRED", "RECOMMENDED"}
    assert SUBMISSION_STAGES[0] == "NOT_SUBMITTED"
    assert CURRENT_SUBMISSION in SUBMISSION_STAGES


# --- 조회 ------------------------------------------------------------------

def test_find_section():
    s = find_section("improvement-plan")
    assert s.title == "정책 개선 방안"


def test_find_section_unknown_raises():
    with pytest.raises(KeyError):
        find_section("nope")


def test_sections_by_status_drafted():
    drafted = sections_by_status("DRAFTED")
    assert all(s.status == "DRAFTED" for s in drafted)
    ids = [s.section_id for s in drafted]
    assert ids == sorted(ids)


def test_sections_by_status_bad_value():
    with pytest.raises(ValueError):
        sections_by_status("WIP")


# --- evidence_present ------------------------------------------------------

def test_evidence_present_true_for_real_section():
    assert evidence_present(find_section("improvement-plan"), REPO_ROOT)


def test_evidence_present_false_for_missing_file(tmp_path):
    # 빈 임시 디렉터리에는 증거가 없으므로 False.
    assert not evidence_present(find_section("improvement-plan"), tmp_path)


def test_evidence_present_vacuous_truth_does_not_inflate_score(tmp_path, monkeypatch):
    """증거 인용이 없는 OUTLINED 섹션은 가중 점수를 받지 않는다 (공허 참 차단)."""
    import simulation.k_drone_policy_proposal as mod
    outlined = _section(section_id="x", status="OUTLINED", evidence=())
    monkeypatch.setattr(mod, "PROPOSAL_SECTIONS", (outlined,))
    r = mod.assess_readiness(tmp_path)
    # OUTLINED·증거 없음 → 점수 0.0 (0.5 가 더해지면 안 됨).
    assert r.score == 0.0


def test_sections_by_status_missing_and_outlined():
    assert sections_by_status("MISSING") == ()
    assert all(s.status == "OUTLINED" for s in sections_by_status("OUTLINED"))


def test_assess_readiness_empty_registry_not_ready(tmp_path, monkeypatch):
    """빈 레지스트리는 공허 참으로 READY 를 선언하지 않는다."""
    import simulation.k_drone_policy_proposal as mod
    monkeypatch.setattr(mod, "PROPOSAL_SECTIONS", ())
    r = mod.assess_readiness(tmp_path)
    assert r.verdict != VERDICT_READY


# --- assess_readiness ------------------------------------------------------

def test_assess_readiness_real_repo_is_ready():
    """실 리포에서 모든 필수 섹션이 작성·증거 실재 → READY_FOR_REVIEW."""
    r = assess_readiness(REPO_ROOT)
    assert r.verdict == VERDICT_READY
    assert not r.missing_required
    assert r.score == 1.0


def test_assess_readiness_default_root():
    r = assess_readiness()
    assert isinstance(r, ProposalReadiness)
    assert r.is_ready()


def test_assess_readiness_submission_not_submitted():
    """준비 완료여도 제출 상태는 정직하게 NOT_SUBMITTED."""
    r = assess_readiness(REPO_ROOT)
    assert r.submission_status == "NOT_SUBMITTED"
    assert not r.is_submitted()


def test_assess_readiness_missing_evidence_is_not_ready(tmp_path):
    """증거 파일이 하나도 없으면 필수 미충족 → NOT_READY."""
    r = assess_readiness(tmp_path)
    assert r.verdict == VERDICT_NOT_READY
    assert r.missing_required
    assert r.score == 0.0


def test_readiness_score_in_range():
    r = assess_readiness(REPO_ROOT)
    assert 0.0 <= r.score <= 1.0


def test_readiness_by_criticality_sums_total():
    r = assess_readiness(REPO_ROOT)
    assert sum(r.by_criticality.values()) == len(PROPOSAL_SECTIONS)


def test_readiness_by_criticality_read_only():
    r = assess_readiness(REPO_ROOT)
    with pytest.raises(TypeError):
        r.by_criticality["REQUIRED"] = 99  # type: ignore[index]


def test_readiness_summary_mentions_submission():
    r = assess_readiness(REPO_ROOT)
    assert "NOT_SUBMITTED" in r.summary()


def test_readiness_rejects_bad_verdict():
    with pytest.raises(ValueError):
        ProposalReadiness(
            verdict="WAT", score=1.0, submission_status="NOT_SUBMITTED",
            drafted=(), missing_required=(), incomplete_other=(),
            by_criticality={"REQUIRED": 1},
        )


def test_readiness_rejects_bad_submission():
    with pytest.raises(ValueError):
        ProposalReadiness(
            verdict=VERDICT_READY, score=1.0, submission_status="MAYBE",
            drafted=(), missing_required=(), incomplete_other=(),
            by_criticality={"REQUIRED": 1},
        )


def test_readiness_rejects_out_of_range_score():
    with pytest.raises(ValueError):
        ProposalReadiness(
            verdict=VERDICT_READY, score=1.5, submission_status="NOT_SUBMITTED",
            drafted=(), missing_required=(), incomplete_other=(),
            by_criticality={"REQUIRED": 1},
        )


def test_partial_verdict_constructs():
    r = ProposalReadiness(
        verdict=VERDICT_PARTIAL, score=0.9, submission_status="NOT_SUBMITTED",
        drafted=(), missing_required=(), incomplete_other=("budget",),
        by_criticality={"REQUIRED": 1},
    )
    assert not r.is_ready()


# --- proposal_matrix -------------------------------------------------------

def test_proposal_matrix_shape():
    matrix = proposal_matrix()
    assert len(matrix) == len(PROPOSAL_SECTIONS)
    keys = {"section_id", "title", "criticality", "status", "evidence", "summary"}
    for row in matrix:
        assert keys == set(row.keys())


def test_proposal_matrix_evidence_is_list():
    for row in proposal_matrix():
        assert isinstance(row["evidence"], list)


# --- CLI -------------------------------------------------------------------

def test_main_default_returns_zero(capsys):
    rc = main([])
    assert rc == 0
    assert "준비도" in capsys.readouterr().out


def test_main_matrix(capsys):
    rc = main(["--matrix"])
    assert rc == 0
    assert "매트릭스" in capsys.readouterr().out


def test_main_report(capsys):
    rc = main(["--report"])
    assert rc == 0
    assert "제출 상태" in capsys.readouterr().out


def test_main_gaps(capsys):
    rc = main(["--gaps"])
    assert rc == 0
    # 실 리포는 필수 미충족이 없어야 한다.
    assert "없음" in capsys.readouterr().out


def test_main_submission(capsys):
    rc = main(["--submission"])
    assert rc == 0
    assert "NOT_SUBMITTED" in capsys.readouterr().out.strip()
