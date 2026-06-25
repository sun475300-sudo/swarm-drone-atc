"""ODYSSEY Phase 452 — RL 일반화 평가 프로토콜 적합성 게이트 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.rl_generalization_protocol import (
    PROTOCOL_REQUIREMENTS,
    PROTOCOL_STAGES,
    PROTOCOL_STATUSES,
    VERDICTS,
    ProtocolReport,
    ProtocolRequirement,
    critical_requirements,
    find_requirement,
    gaps,
    main,
    protocol_matrix,
    protocol_report,
    requirements_by_stage,
    requirements_by_status,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _req(**kw) -> ProtocolRequirement:
    """완전 충족 기본값으로 ProtocolRequirement 를 만든다 (테스트 편의)."""
    defaults = dict(
        requirement_id="id",
        name="name",
        stage="split_protocol",
        anchor="SP:SPLIT",
        critical=True,
        status="satisfied",
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


def test_requirement_rejects_internal_tab_id():
    """탭·개행 등 내부 비-공백 공백문자도 snake_case 위반으로 거부(어드바이저 반영)."""
    with pytest.raises(ValueError):
        _req(requirement_id="foo\tbar")


def test_requirement_rejects_uppercase_id():
    with pytest.raises(ValueError):
        _req(requirement_id="FooBar")


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


def test_requirement_rejects_non_bool_critical():
    with pytest.raises(TypeError):
        _req(critical=1)


def test_requirement_rejects_unknown_status():
    with pytest.raises(ValueError):
        _req(status="maybe")


# --- 정직성 결속: absent ⟺ 증거 없음 --------------------------------------

def test_absent_must_not_cite_evidence():
    with pytest.raises(ValueError):
        _req(status="absent", evidence="simulation/standard_scenarios.py")


def test_absent_with_none_evidence_is_valid():
    r = _req(status="absent", evidence=None)
    assert r.is_absent is True


def test_satisfied_requires_evidence():
    with pytest.raises(ValueError):
        _req(status="satisfied", evidence=None)


def test_partial_requires_non_empty_evidence():
    with pytest.raises(ValueError):
        _req(status="partial", evidence="   ")


def test_weight_values():
    assert _req(status="satisfied").weight == 1.0
    assert _req(status="partial", evidence="x").weight == 0.5
    assert _req(status="absent", evidence=None).weight == 0.0


# --- 카탈로그 무결성 -------------------------------------------------------

def test_catalog_non_empty():
    assert len(PROTOCOL_REQUIREMENTS) >= 10


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


def test_catalog_has_known_core_gaps():
    """연구 수준 RL — 분리·일반화 지표 정의 등 임계 갭이 정직하게 존재해야 한다."""
    gap_ids = {r.requirement_id for r in gaps()}
    assert "disjoint_train_eval_split" in gap_ids
    assert "generalization_metric_definition" in gap_ids


def test_advisory_invariant_is_satisfied():
    """SDACS 의 강점 — RL 자문 불변식(안전망 권한)은 충족이어야 한다."""
    req = find_requirement("advisory_only_invariant")
    assert req.status == "satisfied"
    assert req.stage == "baseline_grounding"


def test_core_gaps_are_critical():
    """일반화 측정 전제(분할·지표 정의)는 반드시 임계 요건이어야 한다."""
    assert find_requirement("disjoint_train_eval_split").critical is True
    assert find_requirement("generalization_metric_definition").critical is True


# --- 조회 API --------------------------------------------------------------

def test_find_requirement_returns_match():
    req = find_requirement("ood_condition_coverage")
    assert req.requirement_id == "ood_condition_coverage"


def test_find_requirement_unknown_raises():
    with pytest.raises(KeyError):
        find_requirement("nope")


def test_requirements_by_stage_sorted():
    res = requirements_by_stage("statistical_rigor")
    assert len(res) >= 1
    assert all(r.stage == "statistical_rigor" for r in res)
    assert list(res) == sorted(res, key=lambda r: r.requirement_id)


def test_requirements_by_stage_unknown_raises():
    with pytest.raises(ValueError):
        requirements_by_stage("nope")


def test_critical_requirements_all_critical():
    res = critical_requirements()
    assert len(res) >= 1
    assert all(r.critical for r in res)


def test_requirements_by_status_filters():
    for status in PROTOCOL_STATUSES:
        res = requirements_by_status(status)
        assert all(r.status == status for r in res)


def test_requirements_by_status_unknown_raises():
    with pytest.raises(ValueError):
        requirements_by_status("nope")


def test_gaps_all_are_absent():
    assert all(r.is_absent for r in gaps())


# --- ProtocolReport --------------------------------------------------------

def test_report_counts_consistent():
    r = protocol_report()
    assert r.satisfied + r.partial + r.absent == r.total
    assert r.total == len(PROTOCOL_REQUIREMENTS)


def test_report_critical_counts_within_bounds():
    r = protocol_report()
    assert r.critical_satisfied <= r.critical_total
    assert r.critical_unmet <= r.critical_total
    assert r.critical_total <= r.total


def test_report_by_stage_sums_match():
    r = protocol_report()
    s = sum(v[0] for v in r.by_stage.values())
    p = sum(v[1] for v in r.by_stage.values())
    a = sum(v[2] for v in r.by_stage.values())
    assert (s, p, a) == (r.satisfied, r.partial, r.absent)


def test_report_by_stage_is_read_only():
    r = protocol_report()
    with pytest.raises(TypeError):
        r.by_stage["split_protocol"] = (0, 0, 0)  # type: ignore[index]


def test_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=5, satisfied=1, partial=1, absent=1,
            critical_total=1, critical_satisfied=1, critical_unmet=0,
            by_stage={},
        )


def test_report_rejects_critical_satisfied_over_total():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=3, satisfied=3, partial=0, absent=0,
            critical_total=1, critical_satisfied=2, critical_unmet=0,
            by_stage={},
        )


def test_report_rejects_critical_sum_over_total():
    """완전 충족 + 미충족이 임계 총계를 넘으면 거부(어드바이저 HIGH 반영)."""
    with pytest.raises(ValueError):
        ProtocolReport(
            total=3, satisfied=1, partial=0, absent=2,
            critical_total=2, critical_satisfied=1, critical_unmet=2,
            by_stage={"split_protocol": (1, 0, 2)},
        )


def test_report_rejects_unknown_stage_in_by_stage():
    with pytest.raises(ValueError):
        ProtocolReport(
            total=1, satisfied=1, partial=0, absent=0,
            critical_total=1, critical_satisfied=1, critical_unmet=0,
            by_stage={"nope": (1, 0, 0)},
        )


def test_weighted_score_in_range():
    r = protocol_report()
    assert 0.0 <= r.weighted_score_pct <= 100.0


# --- 종합 판정 (verdict) ---------------------------------------------------

def test_current_verdict_is_not_established():
    """현 리포는 임계 갭(분할·지표)이 있으므로 NOT_ESTABLISHED 여야 한다(정직 공시)."""
    r = protocol_report()
    assert r.verdict == "NOT_ESTABLISHED"
    assert r.critical_unmet > 0


def test_verdict_is_known_value():
    assert protocol_report().verdict in VERDICTS


def test_verdict_not_established_when_critical_unmet():
    r = ProtocolReport(
        total=2, satisfied=1, partial=0, absent=1,
        critical_total=2, critical_satisfied=1, critical_unmet=1,
        by_stage={"split_protocol": (1, 0, 1)},
    )
    assert r.verdict == "NOT_ESTABLISHED"


def test_verdict_established_when_all_satisfied():
    r = ProtocolReport(
        total=2, satisfied=2, partial=0, absent=0,
        critical_total=2, critical_satisfied=2, critical_unmet=0,
        by_stage={"split_protocol": (2, 0, 0)},
    )
    assert r.verdict == "ESTABLISHED"


def test_verdict_partial_when_critical_met_but_partials_remain():
    r = ProtocolReport(
        total=2, satisfied=1, partial=1, absent=0,
        critical_total=1, critical_satisfied=1, critical_unmet=0,
        by_stage={"split_protocol": (1, 1, 0)},
    )
    assert r.verdict == "PARTIAL"


def test_high_score_does_not_override_critical_unmet():
    """가중 점수가 높아도 임계 미충족이면 NOT_ESTABLISHED — 점수가 판정을 앞당기지 않는다."""
    r = ProtocolReport(
        total=4, satisfied=3, partial=0, absent=1,
        critical_total=1, critical_satisfied=0, critical_unmet=1,
        by_stage={"split_protocol": (3, 0, 1)},
    )
    assert r.weighted_score_pct == 75.0
    assert r.verdict == "NOT_ESTABLISHED"


# --- 매트릭스 / CLI --------------------------------------------------------

def test_matrix_rows_match_catalog():
    rows = protocol_matrix()
    assert len(rows) == len(PROTOCOL_REQUIREMENTS)
    ids = {row["requirement_id"] for row in rows}
    assert ids == {r.requirement_id for r in PROTOCOL_REQUIREMENTS}


def test_matrix_ordered_by_stage_then_id():
    rows = protocol_matrix()
    keys = [
        (PROTOCOL_STAGES.index(str(row["stage"])), str(row["requirement_id"]))
        for row in rows
    ]
    assert keys == sorted(keys)


def test_matrix_rows_read_only():
    rows = protocol_matrix()
    with pytest.raises(TypeError):
        rows[0]["status"] = "satisfied"  # type: ignore[index]


def test_main_report_default(capsys):
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NOT_ESTABLISHED" in out


def test_main_report_flag(capsys):
    rc = main(["--report"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NOT_ESTABLISHED" in out


def test_main_matrix(capsys):
    rc = main(["--matrix"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "disjoint_train_eval_split" in out or "SP:SPLIT" in out


def test_main_gaps(capsys):
    rc = main(["--gaps"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "generalization_metric_definition" in out or "RI:METRIC" in out


def test_main_critical(capsys):
    rc = main(["--critical"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "BG:ADV" in out


def test_main_stage(capsys):
    rc = main(["--stage", "distribution_shift"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ood_condition_coverage" in out
