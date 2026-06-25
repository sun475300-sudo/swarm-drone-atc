"""ODYSSEY Phase 454 — ML 애플리케이션 EASA Level 분류 게이트 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.ml_application_classification import (
    EASA_LEVELS,
    HUMAN_AUTHORITY,
    LEVEL_FAMILY,
    ML_CONSTITUENTS,
    POLICY_MATRIX,
    TASK_ALLOCATIONS,
    ClassificationReport,
    MLConstituent,
    classification_matrix,
    classification_report,
    classify_level,
    constituents_by_level,
    find_constituent,
    main,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _con(**kw) -> MLConstituent:
    """유효 기본값으로 MLConstituent 를 만든다 (테스트 편의)."""
    defaults = dict(
        constituent_id="cid",
        name="name",
        task="task",
        sdacs_module="src/rl/ppo_collision.py",
        allocation="assistance",
        human_authority="retained",
        override_authority="simulation/path_deconflict.py",
        rationale="r",
    )
    defaults.update(kw)
    return MLConstituent(**defaults)  # type: ignore[arg-type]


# --- MLConstituent 검증 ----------------------------------------------------

def test_constituent_rejects_empty_id():
    with pytest.raises(ValueError):
        _con(constituent_id="")


def test_constituent_rejects_padded_id():
    with pytest.raises(ValueError):
        _con(constituent_id=" cid ")


def test_constituent_rejects_internal_space_id():
    with pytest.raises(ValueError):
        _con(constituent_id="foo bar")


@pytest.mark.parametrize("field", ["name", "task", "sdacs_module", "rationale"])
def test_constituent_rejects_empty_text_fields(field):
    with pytest.raises(ValueError):
        _con(**{field: "  "})


def test_constituent_rejects_unknown_allocation():
    with pytest.raises(ValueError):
        _con(allocation="magic")


def test_constituent_rejects_unknown_authority():
    with pytest.raises(ValueError):
        _con(human_authority="sometimes")


# --- 정직성 결속: 권한 ⟺ 권한자 인용 --------------------------------------

def test_retained_authority_requires_override_holder():
    with pytest.raises(ValueError):
        _con(human_authority="retained", override_authority=None)


def test_reduced_authority_requires_override_holder():
    with pytest.raises(ValueError):
        _con(human_authority="reduced", override_authority=None)


def test_none_authority_forbids_override_holder():
    with pytest.raises(ValueError):
        _con(human_authority="none", override_authority="simulation/path_deconflict.py")


def test_none_authority_allows_missing_override():
    # automation/none 은 권한자 없음이 정합 (Level 3B).
    constituent = _con(allocation="automation", human_authority="none",
                       override_authority=None)
    assert constituent.level == "3B"


def test_retained_authority_with_holder_ok():
    constituent = _con(human_authority="retained",
                       override_authority="simulation/emergency_protocol.py")
    assert constituent.level == "1A"


def test_constituent_is_frozen():
    # frozen dataclass 는 통상 대입 경로의 변형을 차단한다.
    constituent = _con()
    with pytest.raises(Exception):
        constituent.human_authority = "none"  # type: ignore[misc]


# --- classify_level 정책 매트릭스 -----------------------------------------

def test_policy_matrix_covers_all_combinations():
    expected = {(a, h) for a in TASK_ALLOCATIONS for h in HUMAN_AUTHORITY}
    assert set(POLICY_MATRIX.keys()) == expected


def test_classify_level_matches_policy_matrix_exactly():
    for (allocation, authority), level in POLICY_MATRIX.items():
        assert classify_level(allocation, authority) == level


def test_classify_level_yields_only_known_levels():
    for level in POLICY_MATRIX.values():
        assert level in EASA_LEVELS


def test_assistance_never_exceeds_family_one():
    for authority in HUMAN_AUTHORITY:
        assert LEVEL_FAMILY[classify_level("assistance", authority)] == 1


def test_automation_always_family_three():
    for authority in HUMAN_AUTHORITY:
        assert LEVEL_FAMILY[classify_level("automation", authority)] == 3


def test_classify_level_rejects_unknown_allocation():
    with pytest.raises(ValueError):
        classify_level("magic", "retained")


def test_classify_level_rejects_unknown_authority():
    with pytest.raises(ValueError):
        classify_level("assistance", "sometimes")


def test_level_family_covers_all_levels():
    assert set(LEVEL_FAMILY.keys()) == set(EASA_LEVELS)


# --- 카탈로그 무결성 -------------------------------------------------------

def test_catalog_ids_unique():
    ids = [c.constituent_id for c in ML_CONSTITUENTS]
    assert len(ids) == len(set(ids))


def test_catalog_non_empty():
    assert len(ML_CONSTITUENTS) >= 1


def test_cited_modules_exist_on_disk():
    for constituent in ML_CONSTITUENTS:
        path = os.path.join(REPO_ROOT, constituent.sdacs_module)
        assert os.path.isfile(path), f"missing ML module: {constituent.sdacs_module}"


def test_cited_override_authorities_exist_on_disk():
    for constituent in ML_CONSTITUENTS:
        if constituent.override_authority is None:
            continue
        path = os.path.join(REPO_ROOT, constituent.override_authority)
        assert os.path.isfile(path), (
            f"missing override authority: {constituent.override_authority}"
        )


# --- 핵심 발견: 전 자산 Level 1A (자문) ------------------------------------

def test_all_sdacs_ml_is_level_1a():
    """SDACS 의 모든 ML 자산은 자문(1A)이다 — 정직한 강점 공시."""
    for constituent in ML_CONSTITUENTS:
        assert constituent.level == "1A"
        assert constituent.is_advisory
        assert constituent.family == 1


# --- find / by_level -------------------------------------------------------

def test_find_constituent_returns_match():
    constituent = find_constituent("ppo_collision_avoidance")
    assert constituent.constituent_id == "ppo_collision_avoidance"
    assert constituent.name


def test_find_constituent_unknown_raises():
    with pytest.raises(KeyError):
        find_constituent("nope")


def test_constituents_by_level_sorted():
    items = constituents_by_level("1A")
    ids = [c.constituent_id for c in items]
    assert ids == sorted(ids)
    assert len(items) == len(ML_CONSTITUENTS)


def test_constituents_by_level_empty_for_unused_level():
    assert constituents_by_level("3B") == ()


def test_constituents_by_level_rejects_unknown():
    with pytest.raises(ValueError):
        constituents_by_level("9Z")


# --- ClassificationReport --------------------------------------------------

def test_report_counts_sum_to_total():
    report = classification_report()
    assert sum(report.by_level.values()) == report.total
    assert report.total == len(ML_CONSTITUENTS)


def test_report_all_advisory_true_for_live_registry():
    report = classification_report()
    assert report.all_advisory
    assert report.highest_family == 1


def test_report_by_level_is_read_only():
    report = classification_report()
    with pytest.raises(TypeError):
        report.by_level["1A"] = 99  # type: ignore[index]


def test_report_rejects_unknown_level_key():
    with pytest.raises(ValueError):
        ClassificationReport(total=1, by_level={"9Z": 1}, by_family={9: 1})


def test_report_rejects_sum_mismatch():
    with pytest.raises(ValueError):
        ClassificationReport(total=5, by_level={"1A": 1}, by_family={1: 1})


def test_report_rejects_family_inconsistency():
    with pytest.raises(ValueError):
        ClassificationReport(total=1, by_level={"1A": 1}, by_family={3: 1})


def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        ClassificationReport(total=-1, by_level={}, by_family={})


def test_report_all_advisory_false_when_family_two_present():
    report = ClassificationReport(total=1, by_level={"2A": 1}, by_family={2: 1})
    assert not report.all_advisory
    assert report.highest_family == 2


# --- classification_matrix -------------------------------------------------

def test_matrix_rows_self_describing():
    rows = classification_matrix()
    assert len(rows) == len(ML_CONSTITUENTS)
    for row in rows:
        assert set(row.keys()) == {
            "constituent_id", "name", "task", "sdacs_module", "allocation",
            "human_authority", "override_authority", "level", "family", "rationale",
        }


def test_matrix_rows_are_read_only():
    row = classification_matrix()[0]
    with pytest.raises(TypeError):
        row["level"] = "3B"  # type: ignore[index]


def test_matrix_ordered_by_level_then_id():
    rows = classification_matrix()
    keys = [(EASA_LEVELS.index(str(r["level"])), r["constituent_id"]) for r in rows]
    assert keys == sorted(keys)


def test_matrix_level_matches_constituent_level():
    for row in classification_matrix():
        constituent = find_constituent(str(row["constituent_id"]))
        assert row["level"] == constituent.level


# --- 결정성 ----------------------------------------------------------------

def test_report_is_deterministic():
    first = classification_report()
    second = classification_report()
    assert dict(first.by_level) == dict(second.by_level)
    assert dict(first.by_family) == dict(second.by_family)


def test_matrix_is_deterministic():
    assert classification_matrix() == classification_matrix()


# --- CLI -------------------------------------------------------------------

def test_cli_matrix(capsys):
    assert main(["--matrix"]) == 0
    assert "분류 매트릭스" in capsys.readouterr().out


def test_cli_report(capsys):
    assert main(["--report"]) == 0
    assert "Level 1A" in capsys.readouterr().out


def test_cli_levels(capsys):
    assert main(["--levels"]) == 0
    out = capsys.readouterr().out
    for level in EASA_LEVELS:
        assert level in out


def test_cli_policy(capsys):
    assert main(["--policy"]) == 0
    assert "Level" in capsys.readouterr().out


def test_cli_constituent(capsys):
    assert main(["--constituent", "ppo_collision_avoidance"]) == 0
    assert "Level 1A" in capsys.readouterr().out


def test_cli_constituent_unknown_returns_error(capsys):
    assert main(["--constituent", "nonexistent_id"]) == 1
    assert "Error" in capsys.readouterr().err


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "분류 요약" in capsys.readouterr().out
