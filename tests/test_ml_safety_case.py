"""ODYSSEY Phase 459 — EASA ML 안전 사례(Safety Case) 적합성 게이트 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.ml_safety_case import (
    SAFETY_CASE_CATEGORIES,
    SAFETY_CASE_OBJECTIVES,
    SC_STATUSES,
    SafetyCaseObjective,
    SafetyCaseReport,
    find_objective,
    foundational_objectives,
    gaps,
    main,
    objectives_by_category,
    objectives_by_status,
    safety_case_matrix,
    safety_case_report,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _obj(**kw) -> SafetyCaseObjective:
    """완전 충족 기본값으로 SafetyCaseObjective 를 만든다 (테스트 편의)."""
    defaults = dict(
        objective_id="id",
        name="name",
        category="hazard_identification",
        anchor="SC:HI-01",
        foundational=True,
        status="conformant",
        sdacs_module="simulation/hitl_report_generator.py",
        summary="s",
    )
    defaults.update(kw)
    return SafetyCaseObjective(**defaults)  # type: ignore[arg-type]


# --- SafetyCaseObjective 불변식 -----------------------------------------------

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


def test_objective_rejects_unknown_category():
    with pytest.raises(ValueError):
        _obj(category="nonexistent")


def test_objective_rejects_non_bool_foundational():
    with pytest.raises(TypeError):
        _obj(foundational=1)


def test_objective_rejects_unknown_status():
    with pytest.raises(ValueError):
        _obj(status="unknown")


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


def test_objective_rejects_digit_leading_id():
    with pytest.raises(ValueError):
        _obj(objective_id="1abc")


# --- 정직성 결속: gap ⟺ 근거 없음 --------------------------------------------

def test_gap_must_not_cite_module():
    with pytest.raises(ValueError):
        _obj(status="gap", sdacs_module="simulation/hitl_report_generator.py")


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


def test_partial_with_module_is_valid():
    o = _obj(status="partial", sdacs_module="simulation/hitl_report_generator.py")
    assert o.is_gap is False
    assert o.weight == 0.5


# --- 가중 값 -----------------------------------------------------------------

def test_weight_values_by_status():
    assert _obj(status="conformant").weight == 1.0
    assert _obj(status="partial").weight == 0.5
    assert _obj(status="gap", sdacs_module=None).weight == 0.0


# --- 카탈로그 무결성 ----------------------------------------------------------

def test_catalog_non_empty():
    assert len(SAFETY_CASE_OBJECTIVES) >= 15


def test_catalog_ids_unique():
    ids = [o.objective_id for o in SAFETY_CASE_OBJECTIVES]
    assert len(ids) == len(set(ids))


def test_catalog_categories_valid():
    for o in SAFETY_CASE_OBJECTIVES:
        assert o.category in SAFETY_CASE_CATEGORIES


def test_catalog_statuses_valid():
    for o in SAFETY_CASE_OBJECTIVES:
        assert o.status in SC_STATUSES


def test_catalog_foundational_all_bool():
    for o in SAFETY_CASE_OBJECTIVES:
        assert isinstance(o.foundational, bool)


def test_catalog_anchors_unique():
    """각 목표의 EASA 참조 토큰(anchor)은 고유해야 한다."""
    anchors = [o.anchor for o in SAFETY_CASE_OBJECTIVES]
    assert len(anchors) == len(set(anchors))


def test_cited_modules_exist_on_disk():
    """충족/부분 목표가 인용한 경로는 디스크에 실재해야 한다 (허위 충족 차단)."""
    for o in SAFETY_CASE_OBJECTIVES:
        if o.sdacs_module is not None:
            path = os.path.join(REPO_ROOT, o.sdacs_module)
            assert os.path.exists(path), f"{o.objective_id}: missing {o.sdacs_module}"


def test_gap_objectives_have_no_module():
    for o in SAFETY_CASE_OBJECTIVES:
        if o.is_gap:
            assert o.sdacs_module is None


def test_non_gap_objectives_have_module():
    for o in SAFETY_CASE_OBJECTIVES:
        if not o.is_gap:
            assert o.sdacs_module is not None
            assert o.sdacs_module.strip()


# --- 조회 API ----------------------------------------------------------------

def test_find_objective_roundtrip():
    o = SAFETY_CASE_OBJECTIVES[0]
    assert find_objective(o.objective_id) is o


def test_find_objective_unknown_raises():
    with pytest.raises(KeyError):
        find_objective("does_not_exist")


def test_objectives_by_category_sorted_and_scoped():
    for category in SAFETY_CASE_CATEGORIES:
        members = objectives_by_category(category)
        assert all(o.category == category for o in members)
        assert list(members) == sorted(members, key=lambda o: o.objective_id)


def test_objectives_by_category_rejects_unknown():
    with pytest.raises(ValueError):
        objectives_by_category("nonexistent")


def test_objectives_by_category_partition_covers_catalog():
    seen = sum(len(objectives_by_category(c)) for c in SAFETY_CASE_CATEGORIES)
    assert seen == len(SAFETY_CASE_OBJECTIVES)


def test_objectives_by_status_scoped():
    for status in SC_STATUSES:
        members = objectives_by_status(status)
        assert all(o.status == status for o in members)
        assert list(members) == sorted(members, key=lambda o: o.objective_id)


def test_objectives_by_status_rejects_unknown():
    with pytest.raises(ValueError):
        objectives_by_status("unknown")


def test_objectives_by_status_partition_covers_catalog():
    seen = sum(len(objectives_by_status(s)) for s in SC_STATUSES)
    assert seen == len(SAFETY_CASE_OBJECTIVES)


def test_foundational_objectives_subset():
    f = foundational_objectives()
    assert all(o.foundational for o in f)
    assert len(f) >= 1


def test_foundational_objectives_sorted():
    f = foundational_objectives()
    assert list(f) == sorted(f, key=lambda o: o.objective_id)


def test_gaps_returns_only_gaps():
    g = gaps()
    assert all(o.is_gap for o in g)


def test_gaps_sorted():
    g = gaps()
    assert list(g) == sorted(g, key=lambda o: o.objective_id)


# --- 카테고리별 존재 검증 (모든 카테고리에 최소 1건) --------------------------

@pytest.mark.parametrize("category", list(SAFETY_CASE_CATEGORIES))
def test_every_category_has_at_least_one_objective(category):
    assert len(objectives_by_category(category)) >= 1


# --- 리포트 집계 --------------------------------------------------------------

def test_report_counts_consistent():
    r = safety_case_report()
    assert r.conformant + r.partial + r.gap == r.total
    assert r.total == len(SAFETY_CASE_OBJECTIVES)


def test_report_by_category_sums_match():
    r = safety_case_report()
    c = sum(v[0] for v in r.by_category.values())
    p = sum(v[1] for v in r.by_category.values())
    g = sum(v[2] for v in r.by_category.values())
    assert (c, p, g) == (r.conformant, r.partial, r.gap)


def test_report_by_category_is_read_only():
    r = safety_case_report()
    with pytest.raises(TypeError):
        r.by_category["hazard_identification"] = (0, 0, 0)  # type: ignore[index]


def test_report_score_conservative():
    """SDACS 의 ML 안전 사례는 연구 수준 — 점수는 70% 미만의 보수적 값이어야 한다."""
    r = safety_case_report()
    assert 0.0 < r.weighted_score_pct < 70.0


def test_report_foundational_incomplete():
    """기반 안전 사례 목표는 일부 미충족(DAL 할당·잔여 위험 문서화 갭)이어야 한다."""
    r = safety_case_report()
    assert r.has_foundational_incomplete is True


def test_report_deterministic():
    r1 = safety_case_report()
    r2 = safety_case_report()
    assert r1 == r2


def test_report_foundational_conformant_pct_range():
    r = safety_case_report()
    assert 0.0 <= r.foundational_conformant_pct <= 100.0


# --- SafetyCaseReport 직접 생성 불변식 ----------------------------------------

def test_report_rejects_count_mismatch():
    with pytest.raises(ValueError):
        SafetyCaseReport(
            total=10, conformant=1, partial=1, gap=1,
            foundational_total=1, foundational_conformant=0, by_category={},
        )


def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        SafetyCaseReport(
            total=-1, conformant=0, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0, by_category={},
        )


def test_report_rejects_unknown_category_key():
    with pytest.raises(ValueError):
        SafetyCaseReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={
                "hazard_identification": (1, 0, 0), "risk_classification": (0, 0, 0),
                "safety_requirement_allocation": (0, 0, 0), "assurance_level": (0, 0, 0),
                "residual_risk": (0, 0, 0), "strangers": (0, 0, 0),
            },
        )


def test_report_rejects_empty_by_category_when_total_positive():
    """total>0 인데 by_category 가 비면 교차검증 우회 — 거부해야 한다 (정직성 결속)."""
    with pytest.raises(ValueError):
        SafetyCaseReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0, by_category={},
        )


def test_report_rejects_category_sum_mismatch():
    """by_category 합이 상위 총계와 어긋나면 거부해야 한다."""
    with pytest.raises(ValueError):
        SafetyCaseReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={
                "hazard_identification": (0, 0, 1), "risk_classification": (0, 0, 0),
                "safety_requirement_allocation": (0, 0, 0), "assurance_level": (0, 0, 0),
                "residual_risk": (0, 0, 0),
            },
        )


def test_report_rejects_nonempty_by_category_when_total_zero():
    with pytest.raises(ValueError):
        SafetyCaseReport(
            total=0, conformant=0, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={"hazard_identification": (0, 0, 0)},
        )


def test_report_rejects_foundational_overflow():
    with pytest.raises(ValueError):
        SafetyCaseReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=1, foundational_conformant=2, by_category={},
        )


def test_report_rejects_foundational_exceeds_total():
    with pytest.raises(ValueError):
        SafetyCaseReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=2, foundational_conformant=2, by_category={},
        )


def test_report_empty_score_zero():
    r = SafetyCaseReport(
        total=0, conformant=0, partial=0, gap=0,
        foundational_total=0, foundational_conformant=0, by_category={},
    )
    assert r.weighted_score_pct == 0.0
    assert r.foundational_conformant_pct == 0.0
    assert r.has_foundational_incomplete is False


def test_report_by_category_coerces_plain_dict():
    """by_category 가 일반 dict 로 주어져도 MappingProxyType 으로 동결돼야 한다."""
    from types import MappingProxyType

    r = SafetyCaseReport(
        total=1, conformant=1, partial=0, gap=0,
        foundational_total=0, foundational_conformant=0,
        by_category={
            "hazard_identification": (1, 0, 0), "risk_classification": (0, 0, 0),
            "safety_requirement_allocation": (0, 0, 0), "assurance_level": (0, 0, 0),
            "residual_risk": (0, 0, 0),
        },
    )
    assert isinstance(r.by_category, MappingProxyType)
    with pytest.raises(TypeError):
        r.by_category["risk_classification"] = (9, 9, 9)  # type: ignore[index]


# --- 매트릭스 -----------------------------------------------------------------

def test_matrix_rows_self_describing():
    rows = safety_case_matrix()
    assert len(rows) == len(SAFETY_CASE_OBJECTIVES)
    keys = {"objective_id", "name", "category", "anchor",
            "foundational", "status", "sdacs_module", "summary"}
    for row in rows:
        assert keys <= set(row.keys())


def test_matrix_rows_read_only():
    from types import MappingProxyType

    row = safety_case_matrix()[0]
    assert isinstance(row, MappingProxyType)
    with pytest.raises(TypeError):
        row["status"] = "conformant"  # type: ignore[index]


def test_matrix_ordered_by_category():
    rows = safety_case_matrix()
    order = [SAFETY_CASE_CATEGORIES.index(str(r["category"])) for r in rows]
    assert order == sorted(order)


def test_matrix_intra_category_sorted():
    """카테고리 내부는 objective_id 알파벳 정렬이어야 한다."""
    rows = safety_case_matrix()
    for cat in SAFETY_CASE_CATEGORIES:
        ids = [str(r["objective_id"]) for r in rows if r["category"] == cat]
        assert ids == sorted(ids)


def test_matrix_matches_catalog_ids():
    matrix_ids = {str(r["objective_id"]) for r in safety_case_matrix()}
    catalog_ids = {o.objective_id for o in SAFETY_CASE_OBJECTIVES}
    assert matrix_ids == catalog_ids


def test_matrix_is_deterministic():
    assert safety_case_matrix() == safety_case_matrix()


# --- 핵심 정직성 주장 ---------------------------------------------------------

def test_deterministic_safety_authority_is_conformant():
    """결정적 관제기의 안전-결정권 보유는 충족(SDACS 의 진짜 강점)이어야 한다."""
    o = find_objective("deterministic_safety_authority")
    assert o.status == "conformant"
    assert o.category == "safety_requirement_allocation"


def test_ml_advisory_containment_is_conformant():
    o = find_objective("ml_advisory_containment")
    assert o.status == "conformant"


def test_safety_net_independence_is_conformant():
    o = find_objective("safety_net_independence")
    assert o.status == "conformant"


def test_ml_failure_mode_analysis_is_gap():
    """ML 특유 고장 모드 분석은 갭이어야 한다 (정직 공시 — RL 은 연구 수준)."""
    o = find_objective("ml_failure_mode_analysis")
    assert o.is_gap is True


def test_dal_assignment_documentation_is_gap():
    o = find_objective("dal_assignment_documentation")
    assert o.is_gap is True


def test_residual_risk_documentation_is_gap():
    o = find_objective("residual_risk_documentation")
    assert o.is_gap is True


def test_ml_criticality_classification_is_conformant():
    o = find_objective("ml_criticality_classification")
    assert o.status == "conformant"


def test_ml_advisory_only_risk_bound_is_conformant():
    o = find_objective("ml_advisory_only_risk_bound")
    assert o.status == "conformant"


# --- CLI -----------------------------------------------------------------------

@pytest.mark.parametrize("flag", [
    "--matrix", "--report", "--gaps", "--foundational",
])
def test_cli_flags(flag, capsys):
    assert main([flag]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_category(capsys):
    assert main(["--category", "residual_risk"]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "안전 사례" in capsys.readouterr().out


def test_cli_invalid_category_rejected():
    with pytest.raises(SystemExit):
        main(["--category", "nonexistent"])
