"""ODYSSEY Phase 452 — RL 일반화 평가 프로토콜 적합성 게이트 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.rl_generalization_protocol import (
    NO_PROTOCOL,
    PROTOCOL_REQUIREMENTS,
    PROTOCOL_STAGES,
    PROTOCOL_STATUSES,
    READINESS_VERDICTS,
    ProtocolReport,
    ProtocolRequirement,
    ReadinessVerdict,
    absent_requirements,
    find_requirement,
    foundational_requirements,
    main,
    protocol_matrix,
    protocol_readiness,
    protocol_report,
    requirements_by_stage,
    requirements_by_status,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _req(**kw) -> ProtocolRequirement:
    """구비 기본값으로 ProtocolRequirement 를 만든다 (테스트 편의)."""
    defaults = dict(
        requirement_id="id",
        name="name",
        stage="evaluation_design",
        anchor="ED:TT-01",
        foundational=True,
        status="established",
        evidence="simulation/standard_scenarios.py",
        summary="s",
    )
    defaults.update(kw)
    return ProtocolRequirement(**defaults)  # type: ignore[arg-type]


# --- ProtocolRequirement 검증 ----------------------------------------------

def test_requirement_rejects_empty_id():
    with pytest.raises(ValueError):
        _req(requirement_id="")


def test_requirement_rejects_padded_id():
    with pytest.raises(ValueError):
        _req(requirement_id=" id ")


def test_requirement_rejects_internal_space_id():
    with pytest.raises(ValueError):
        _req(requirement_id="foo bar")


def test_requirement_rejects_empty_name():
    with pytest.raises(ValueError):
        _req(name="  ")


def test_requirement_rejects_empty_anchor():
    with pytest.raises(ValueError):
        _req(anchor="  ")


def test_requirement_rejects_empty_summary():
    with pytest.raises(ValueError):
        _req(summary="  ")


def test_requirement_rejects_unknown_stage():
    with pytest.raises(ValueError):
        _req(stage="nope")


def test_requirement_rejects_non_bool_foundational():
    with pytest.raises(TypeError):
        _req(foundational=1)


def test_requirement_rejects_unknown_status():
    with pytest.raises(ValueError):
        _req(status="maybe")


# --- 정직성 결속: absent ⟺ 근거 없음 --------------------------------------

def test_absent_must_not_cite_evidence():
    with pytest.raises(ValueError):
        _req(status="absent", evidence="simulation/standard_scenarios.py")


def test_absent_with_none_evidence_is_valid():
    r = _req(status="absent", evidence=None)
    assert r.is_absent is True


def test_established_requires_evidence():
    with pytest.raises(ValueError):
        _req(status="established", evidence=None)


def test_partial_requires_non_empty_evidence():
    with pytest.raises(ValueError):
        _req(status="partial", evidence="   ")


def test_weight_values():
    assert _req(status="established").weight == 1.0
    assert _req(status="partial", evidence="x").weight == 0.5
    assert _req(status="absent", evidence=None).weight == 0.0


# --- 카탈로그 무결성 -------------------------------------------------------

def test_catalog_non_empty():
    assert len(PROTOCOL_REQUIREMENTS) >= 12


def test_catalog_ids_unique():
    ids = [r.requirement_id for r in PROTOCOL_REQUIREMENTS]
    assert len(ids) == len(set(ids))


def test_all_stages_present_in_catalog():
    used = {r.stage for r in PROTOCOL_REQUIREMENTS}
    assert used == set(PROTOCOL_STAGES)


def test_all_statuses_valid():
    assert all(r.status in PROTOCOL_STATUSES for r in PROTOCOL_REQUIREMENTS)


def test_cited_evidence_exists_on_disk():
    """정직성 강제: 인용된 모든 evidence 경로가 디스크에 실재해야 한다."""
    for r in PROTOCOL_REQUIREMENTS:
        if r.evidence is not None:
            path = os.path.join(REPO_ROOT, r.evidence)
            assert os.path.exists(path), f"{r.requirement_id}: missing {r.evidence}"


def test_absent_requirements_have_no_evidence():
    for r in PROTOCOL_REQUIREMENTS:
        if r.status == "absent":
            assert r.evidence is None


def test_non_absent_requirements_cite_evidence():
    for r in PROTOCOL_REQUIREMENTS:
        if r.status != "absent":
            assert r.evidence


def test_catalog_has_known_frontier_gaps():
    """일반화 프로토콜의 핵심 갭이 정직하게 absent 여야 한다."""
    absent_ids = {r.requirement_id for r in absent_requirements()}
    assert "train_test_scenario_split" in absent_ids
    assert "generalization_gap_quantification" in absent_ids
    assert "multi_seed_evaluation" in absent_ids


def test_parent_gap_traceability_is_established():
    """SDACS 가 한 일 — 상위 EASA 갭 추적성은 구비(established)여야 한다."""
    req = find_requirement("parent_gap_traceability")
    assert req.status == "established"
    assert req.evidence == "simulation/easa_ai_conformance.py"


def test_traceability_is_not_foundational():
    """추적성은 기반 요소가 아니어야 한다 — 그래야 추적성만으론 READY 불가."""
    req = find_requirement("parent_gap_traceability")
    assert req.foundational is False


# --- 조회 API --------------------------------------------------------------

def test_find_requirement_returns_match():
    req = find_requirement("train_test_scenario_split")
    assert req.requirement_id == "train_test_scenario_split"


def test_find_requirement_unknown_raises():
    with pytest.raises(KeyError):
        find_requirement("nope")


def test_requirements_by_stage_sorted():
    res = requirements_by_stage("evaluation_design")
    assert len(res) >= 1
    assert all(r.stage == "evaluation_design" for r in res)
    assert list(res) == sorted(res, key=lambda r: r.requirement_id)


def test_requirements_by_stage_unknown_raises():
    with pytest.raises(ValueError):
        requirements_by_stage("nope")


def test_foundational_requirements_all_foundational():
    res = foundational_requirements()
    assert len(res) >= 1
    assert all(r.foundational for r in res)


def test_requirements_by_status_filters():
    for status in PROTOCOL_STATUSES:
        res = requirements_by_status(status)
        assert all(r.status == status for r in res)


def test_requirements_by_status_unknown_raises():
    with pytest.raises(ValueError):
        requirements_by_status("nope")


def test_absent_requirements_all_absent():
    assert all(r.is_absent for r in absent_requirements())


# --- ProtocolReport --------------------------------------------------------

def test_report_counts_consistent():
    r = protocol_report()
    assert r.established + r.partial + r.absent == r.total
    assert r.total == len(PROTOCOL_REQUIREMENTS)


def test_report_by_stage_sums_match():
    r = protocol_report()
    e = sum(v[0] for v in r.by_stage.values())
    p = sum(v[1] for v in r.by_stage.values())
    a = sum(v[2] for v in r.by_stage.values())
    assert (e, p, a) == (r.established, r.partial, r.absent)


def test_report_by_stage_is_readonly():
    r = protocol_report()
    with pytest.raises(TypeError):
        r.by_stage["evaluation_design"] = (0, 0, 0)  # type: ignore[index]


def test_report_weighted_score_in_range():
    r = protocol_report()
    assert 0.0 <= r.weighted_score_pct <= 100.0


def test_report_weighted_score_is_conservative():
    """프런티어 갭 — 가중 점수는 정직하게 낮아야 한다(<50%)."""
    r = protocol_report()
    assert r.weighted_score_pct < 50.0


def test_report_foundational_none_established():
    """기반 요소는 현 리포에서 하나도 구비되지 않아야 한다(정직)."""
    r = protocol_report()
    assert r.foundational_established == 0
    assert r.foundational_total >= 1


def test_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=3, established=1, partial=1, absent=0,
            foundational_total=1, foundational_established=0, by_stage={},
        )


def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=1, established=-1, partial=1, absent=1,
            foundational_total=0, foundational_established=0, by_stage={},
        )


def test_report_rejects_foundational_over_total():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=2, established=2, partial=0, absent=0,
            foundational_total=3, foundational_established=0, by_stage={},
        )


def test_report_rejects_foundational_established_over_foundational_total():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=5, established=2, partial=0, absent=3,
            foundational_total=1, foundational_established=2, by_stage={},
        )


def test_report_rejects_mismatched_by_stage():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=2, established=2, partial=0, absent=0,
            foundational_total=0, foundational_established=0,
            by_stage={"evaluation_design": (1, 0, 0)},
        )


def test_report_rejects_unknown_by_stage_key():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=2, established=2, partial=0, absent=0,
            foundational_total=0, foundational_established=0,
            by_stage={"garbage": (2, 0, 0)},
        )


def test_report_foundational_pct_zero_when_no_foundational():
    r = ProtocolReport(
        total=0, established=0, partial=0, absent=0,
        foundational_total=0, foundational_established=0, by_stage={},
    )
    assert r.foundational_established_pct == 0.0


def test_report_rejects_empty_by_stage_with_nonzero_total():
    """어드바이저 MEDIUM: total>0 인데 by_stage 비면 합산 불일치로 거부돼야 한다."""
    with pytest.raises(ValueError):
        ProtocolReport(
            total=1, established=1, partial=0, absent=0,
            foundational_total=0, foundational_established=0, by_stage={},
        )


# --- ReadinessVerdict (정직성 결속) ----------------------------------------

def test_verdict_is_no_protocol_currently():
    """기반 0개 구비 → 추적성 established 여도 NO_PROTOCOL 이어야 한다."""
    v = protocol_readiness()
    assert v.verdict == NO_PROTOCOL
    assert v.is_ready is False


def test_verdict_foundational_counts_match_report():
    v = protocol_readiness()
    r = protocol_report()
    assert v.foundational_established == r.foundational_established
    assert v.foundational_total == r.foundational_total


def test_verdict_traceability_alone_does_not_lift_readiness():
    """정직성 결속: established 항목이 있어도 기반 0개면 NO_PROTOCOL 고정."""
    r = protocol_report()
    assert r.established >= 1            # 추적성 1개 established
    assert r.foundational_established == 0
    assert protocol_readiness().verdict == NO_PROTOCOL


def test_verdict_rejects_unknown_verdict():
    with pytest.raises(ValueError):
        ReadinessVerdict(
            verdict="MAYBE", foundational_established=0,
            foundational_total=5, weighted_score_pct=0.0, rationale="r",
        )


def test_verdict_rejects_empty_rationale():
    with pytest.raises(ValueError):
        ReadinessVerdict(
            verdict=NO_PROTOCOL, foundational_established=0,
            foundational_total=5, weighted_score_pct=0.0, rationale="  ",
        )


def test_verdict_rejects_established_over_total():
    with pytest.raises(ValueError):
        ReadinessVerdict(
            verdict=NO_PROTOCOL, foundational_established=6,
            foundational_total=5, weighted_score_pct=0.0, rationale="r",
        )


def test_verdict_rejects_out_of_range_score():
    """어드바이저 MEDIUM: weighted_score_pct 는 [0, 100] 범위여야 한다."""
    with pytest.raises(ValueError):
        ReadinessVerdict(
            verdict=NO_PROTOCOL, foundational_established=0,
            foundational_total=5, weighted_score_pct=200.0, rationale="r",
        )
    with pytest.raises(ValueError):
        ReadinessVerdict(
            verdict=NO_PROTOCOL, foundational_established=0,
            foundational_total=5, weighted_score_pct=-1.0, rationale="r",
        )


def test_verdict_all_constants_valid():
    assert NO_PROTOCOL in READINESS_VERDICTS
    assert len(READINESS_VERDICTS) == 3


# --- 매트릭스 / 결정성 -----------------------------------------------------

def test_protocol_matrix_covers_all():
    rows = protocol_matrix()
    assert len(rows) == len(PROTOCOL_REQUIREMENTS)
    assert {r["requirement_id"] for r in rows} == {
        r.requirement_id for r in PROTOCOL_REQUIREMENTS
    }


def test_protocol_matrix_stage_grouped():
    rows = protocol_matrix()
    seen_index = [PROTOCOL_STAGES.index(str(r["stage"])) for r in rows]
    assert seen_index == sorted(seen_index)


def test_protocol_matrix_rows_self_describing():
    row = protocol_matrix()[0]
    for key in ("requirement_id", "name", "stage", "anchor",
                "foundational", "status", "evidence", "summary"):
        assert key in row


def test_protocol_matrix_rows_are_readonly():
    row = protocol_matrix()[0]
    with pytest.raises(TypeError):
        row["status"] = "hacked"  # type: ignore[index]


def test_report_is_deterministic():
    a, b = protocol_report(), protocol_report()
    assert (a.total, a.established, a.partial, a.absent) == (
        b.total, b.established, b.partial, b.absent
    )
    assert dict(a.by_stage) == dict(b.by_stage)  # 어드바이저 LOW: by_stage 값 결정성


def test_matrix_is_deterministic():
    assert protocol_matrix() == protocol_matrix()


def test_verdict_is_deterministic():
    assert protocol_readiness().verdict == protocol_readiness().verdict


# --- CLI -------------------------------------------------------------------

def test_cli_report_runs(capsys):
    assert main(["--report"]) == 0
    out = capsys.readouterr().out
    assert "RL 일반화" in out


def test_cli_matrix_runs(capsys):
    assert main(["--matrix"]) == 0
    assert "매트릭스" in capsys.readouterr().out


def test_cli_absent_runs(capsys):
    assert main(["--absent"]) == 0


def test_cli_stage_runs(capsys):
    assert main(["--stage", "evaluation_design"]) == 0


def test_cli_foundational_runs(capsys):
    assert main(["--foundational"]) == 0


def test_cli_verdict_runs(capsys):
    assert main(["--verdict"]) == 0
    assert NO_PROTOCOL in capsys.readouterr().out


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "가중 점수" in capsys.readouterr().out
