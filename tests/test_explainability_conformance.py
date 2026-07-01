"""ODYSSEY Phase 456 — EASA AI 설명가능성 적합성 심층 평가 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.explainability_conformance import (
    AUDIENCES,
    EXPL_OBJECTIVES,
    EXPL_STATUSES,
    ExplainabilityReport,
    ExplObjective,
    explainability_matrix,
    explainability_report,
    find_objective,
    foundational_objectives,
    gaps,
    main,
    objectives_by_audience,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _obj(**kw) -> ExplObjective:
    """완전 충족 기본값으로 ExplObjective 를 만든다 (테스트 편의)."""
    defaults = dict(
        objective_id="id",
        name="name",
        audience="developer",
        anchor="EXP:DEV-01",
        foundational=True,
        status="conformant",
        sdacs_module="simulation/explainable_ai.py",
        summary="s",
    )
    defaults.update(kw)
    return ExplObjective(**defaults)  # type: ignore[arg-type]


# --- ExplObjective 불변식 ---------------------------------------------------

def test_objective_rejects_empty_id():
    with pytest.raises(ValueError):
        _obj(objective_id="")


def test_objective_rejects_padded_id():
    with pytest.raises(ValueError):
        _obj(objective_id=" id ")


def test_objective_rejects_spaced_id():
    with pytest.raises(ValueError):
        _obj(objective_id="bad id")


def test_objective_rejects_empty_name():
    with pytest.raises(ValueError):
        _obj(name="  ")


def test_objective_rejects_empty_anchor():
    with pytest.raises(ValueError):
        _obj(anchor="")


def test_objective_rejects_empty_summary():
    with pytest.raises(ValueError):
        _obj(summary="")


def test_objective_rejects_unknown_audience():
    with pytest.raises(ValueError):
        _obj(audience="public")


def test_objective_rejects_non_bool_foundational():
    with pytest.raises(TypeError):
        _obj(foundational=1)


def test_objective_rejects_unknown_status():
    with pytest.raises(ValueError):
        _obj(status="unknown")


# --- 정직성 결속: gap ⟺ 근거 없음 -----------------------------------------

def test_gap_must_not_cite_module():
    with pytest.raises(ValueError):
        _obj(status="gap", sdacs_module="simulation/explainable_ai.py")


def test_conformant_must_cite_module():
    with pytest.raises(ValueError):
        _obj(status="conformant", sdacs_module=None)


def test_partial_must_cite_module():
    with pytest.raises(ValueError):
        _obj(status="partial", sdacs_module="")


def test_gap_with_none_module_is_valid():
    o = _obj(status="gap", sdacs_module=None)
    assert o.is_gap is True
    assert o.weight == 0.0


# --- 카탈로그 무결성 --------------------------------------------------------

def test_catalog_non_empty():
    assert len(EXPL_OBJECTIVES) >= 10


def test_catalog_ids_unique():
    ids = [o.objective_id for o in EXPL_OBJECTIVES]
    assert len(ids) == len(set(ids))


def test_catalog_audiences_valid():
    for o in EXPL_OBJECTIVES:
        assert o.audience in AUDIENCES


def test_catalog_statuses_valid():
    for o in EXPL_OBJECTIVES:
        assert o.status in EXPL_STATUSES


def test_cited_modules_exist_on_disk():
    """충족/부분 목표가 인용한 경로는 디스크에 실재해야 한다 (허위 충족 차단)."""
    for o in EXPL_OBJECTIVES:
        if o.sdacs_module is not None:
            path = os.path.join(REPO_ROOT, o.sdacs_module)
            assert os.path.exists(path), f"{o.objective_id}: missing {o.sdacs_module}"


def test_gap_objectives_have_no_module():
    for o in EXPL_OBJECTIVES:
        if o.is_gap:
            assert o.sdacs_module is None


# --- 조회 API ---------------------------------------------------------------

def test_find_objective_roundtrip():
    o = EXPL_OBJECTIVES[0]
    assert find_objective(o.objective_id) is o


def test_find_objective_unknown_raises():
    with pytest.raises(KeyError):
        find_objective("does_not_exist")


def test_objectives_by_audience_sorted_and_scoped():
    for audience in AUDIENCES:
        members = objectives_by_audience(audience)
        assert all(o.audience == audience for o in members)
        assert list(members) == sorted(members, key=lambda o: o.objective_id)


def test_objectives_by_audience_rejects_unknown():
    with pytest.raises(ValueError):
        objectives_by_audience("nobody")


def test_objectives_by_audience_partition_covers_catalog():
    seen = sum(len(objectives_by_audience(a)) for a in AUDIENCES)
    assert seen == len(EXPL_OBJECTIVES)


def test_foundational_objectives_subset():
    f = foundational_objectives()
    assert all(o.foundational for o in f)
    assert len(f) >= 1


def test_gaps_returns_only_gaps():
    g = gaps()
    assert all(o.is_gap for o in g)


def test_gaps_sorted():
    g = gaps()
    assert list(g) == sorted(g, key=lambda o: o.objective_id)


def test_foundational_objectives_sorted():
    f = foundational_objectives()
    assert list(f) == sorted(f, key=lambda o: o.objective_id)


def test_weight_values_by_status():
    assert _obj(status="conformant").weight == 1.0
    assert _obj(status="partial").weight == 0.5
    assert _obj(status="gap", sdacs_module=None).weight == 0.0


def test_objective_rejects_tab_in_id():
    """snake_case 강제 — 공백 외 탭·개행도 거부해야 한다."""
    with pytest.raises(ValueError):
        _obj(objective_id="id\ttab")


def test_objective_rejects_newline_in_id():
    with pytest.raises(ValueError):
        _obj(objective_id="col\nlumn")


def test_objective_rejects_uppercase_id():
    with pytest.raises(ValueError):
        _obj(objective_id="BadId")


# --- 리포트 집계 ------------------------------------------------------------

def test_report_counts_consistent():
    r = explainability_report()
    assert r.conformant + r.partial + r.gap == r.total
    assert r.total == len(EXPL_OBJECTIVES)


def test_report_by_audience_sums_match():
    r = explainability_report()
    c = sum(v[0] for v in r.by_audience.values())
    p = sum(v[1] for v in r.by_audience.values())
    g = sum(v[2] for v in r.by_audience.values())
    assert (c, p, g) == (r.conformant, r.partial, r.gap)


def test_report_by_audience_is_read_only():
    r = explainability_report()
    with pytest.raises(TypeError):
        r.by_audience["developer"] = (0, 0, 0)  # type: ignore[index]


def test_report_score_conservative():
    """SDACS 의 ML 설명은 연구 수준 — 점수는 60% 미만의 보수적 값이어야 한다."""
    r = explainability_report()
    assert 0.0 < r.weighted_score_pct < 60.0


def test_report_foundational_incomplete():
    """기반 설명가능성 목표는 일부 미충족(운영 인터페이스·의미 검증 갭)이어야 한다."""
    r = explainability_report()
    assert r.has_foundational_incomplete is True


def test_report_deterministic():
    r1 = explainability_report()
    r2 = explainability_report()
    assert r1 == r2


# --- ExplainabilityReport 직접 생성 불변식 ---------------------------------

def test_report_rejects_count_mismatch():
    with pytest.raises(ValueError):
        ExplainabilityReport(
            total=10, conformant=1, partial=1, gap=1,
            foundational_total=1, foundational_conformant=0, by_audience={},
        )


def test_report_rejects_unknown_audience_key():
    with pytest.raises(ValueError):
        ExplainabilityReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_audience={"developer": (1, 0, 0), "end_user": (0, 0, 0),
                         "regulator": (0, 0, 0), "strangers": (0, 0, 0)},
        )


def test_report_rejects_empty_by_audience_when_total_positive():
    """total>0 인데 by_audience 가 비면 교차검증 우회 — 거부해야 한다 (정직성 결속)."""
    with pytest.raises(ValueError):
        ExplainabilityReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0, by_audience={},
        )


def test_report_rejects_audience_sum_mismatch():
    """by_audience 합이 상위 총계와 어긋나면 거부해야 한다."""
    with pytest.raises(ValueError):
        ExplainabilityReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_audience={"developer": (0, 0, 1), "end_user": (0, 0, 0),
                         "regulator": (0, 0, 0)},
        )


def test_report_rejects_nonempty_by_audience_when_total_zero():
    with pytest.raises(ValueError):
        ExplainabilityReport(
            total=0, conformant=0, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_audience={"developer": (0, 0, 0)},
        )


def test_report_rejects_foundational_overflow():
    with pytest.raises(ValueError):
        ExplainabilityReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=1, foundational_conformant=2, by_audience={},
        )


def test_report_empty_score_zero():
    r = ExplainabilityReport(
        total=0, conformant=0, partial=0, gap=0,
        foundational_total=0, foundational_conformant=0, by_audience={},
    )
    assert r.weighted_score_pct == 0.0
    assert r.foundational_conformant_pct == 0.0
    assert r.has_foundational_incomplete is False


# --- 매트릭스 ---------------------------------------------------------------

def test_matrix_rows_self_describing():
    rows = explainability_matrix()
    assert len(rows) == len(EXPL_OBJECTIVES)
    keys = {"objective_id", "name", "audience", "anchor",
            "foundational", "status", "sdacs_module", "summary"}
    for row in rows:
        assert keys <= set(row.keys())


def test_matrix_rows_read_only():
    row = explainability_matrix()[0]
    with pytest.raises(TypeError):
        row["status"] = "conformant"  # type: ignore[index]


def test_matrix_ordered_by_audience():
    rows = explainability_matrix()
    order = [AUDIENCES.index(str(r["audience"])) for r in rows]
    assert order == sorted(order)


# --- 핵심 정직성 주장 -------------------------------------------------------

def test_interpretable_logic_is_conformant():
    """안전-결정 해석가능성은 충족(결정적 규칙 로직)이어야 한다."""
    o = find_objective("interpretable_decision_logic")
    assert o.status == "conformant"


def test_audit_traceability_is_conformant():
    """결정 추적성(감사)은 충족이어야 한다."""
    o = find_objective("decision_traceability_audit")
    assert o.status == "conformant"


def test_operational_interface_is_gap():
    """운영용 실시간 설명 인터페이스는 갭이어야 한다 (정직 공시)."""
    o = find_objective("operational_explanation_interface")
    assert o.is_gap is True


# --- CLI --------------------------------------------------------------------

@pytest.mark.parametrize("flag", [
    "--matrix", "--report", "--gaps", "--foundational",
])
def test_cli_flags(flag, capsys):
    assert main([flag]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_audience(capsys):
    assert main(["--audience", "end_user"]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "설명가능성" in capsys.readouterr().out
