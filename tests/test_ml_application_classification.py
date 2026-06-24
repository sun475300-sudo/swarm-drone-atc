"""ODYSSEY Phase 452 — ML 애플리케이션 분류 게이트 테스트.

dataclass 축 결속 불변식·결정적 분류·정직성(디스크 실재) 강제·리포트 불변식·
POLICY_MATRIX 와 classify 정확 일치·CLI 를 검증한다.
"""
from __future__ import annotations

import os

import pytest

from simulation.ml_application_classification import (
    AI_LEVELS,
    AI_ROLES,
    CONSTITUENTS,
    POLICY_MATRIX,
    ClassificationReport,
    MlConstituent,
    classification_matrix,
    classification_report,
    classify,
    constituents_by_level,
    find_constituent,
    main,
    manifest,
    operational_constituents,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- MlConstituent 축 결속 불변식 -----------------------------------------

def test_advisory_requires_emits():
    with pytest.raises(ValueError):
        MlConstituent(
            "x", "X", "f", "advisory", None, None, None, "src/rl/ppo_collision.py", "r"
        )


def test_advisory_rejects_oversight_and_fallback():
    with pytest.raises(ValueError):
        MlConstituent(
            "x", "X", "f", "advisory", "information", "human", None,
            "src/rl/ppo_collision.py", "r"
        )


def test_supervised_actor_requires_oversight():
    with pytest.raises(ValueError):
        MlConstituent(
            "x", "X", "f", "supervised_actor", None, None, None,
            "src/rl/ppo_collision.py", "r"
        )


def test_decider_requires_bool_fallback():
    with pytest.raises(ValueError):
        MlConstituent(
            "x", "X", "f", "decider", None, None, None,
            "src/rl/ppo_collision.py", "r"
        )


def test_not_operational_rejects_subaxes():
    with pytest.raises(ValueError):
        MlConstituent(
            "x", "X", "f", "not_operational", "information", None, None,
            "src/rl/ppo_collision.py", "r"
        )


def test_invalid_role_rejected():
    with pytest.raises(ValueError):
        MlConstituent(
            "x", "X", "f", "bogus", None, None, None, "src/rl/ppo_collision.py", "r"
        )


def test_id_must_be_snake_case():
    with pytest.raises(ValueError):
        MlConstituent(
            "bad id", "X", "f", "advisory", "information", None, None,
            "src/rl/ppo_collision.py", "r"
        )


@pytest.mark.parametrize("field_kwargs", [
    {"name": ""}, {"function": "  "}, {"sdacs_module": ""}, {"rationale": ""},
])
def test_non_empty_fields_enforced(field_kwargs):
    base = dict(
        constituent_id="x", name="X", function="f", ai_role="advisory",
        emits="information", oversight_by=None, human_fallback=None,
        sdacs_module="src/rl/ppo_collision.py", rationale="r",
    )
    base.update(field_kwargs)
    with pytest.raises(ValueError):
        MlConstituent(**base)


# --- 결정적 분류 ------------------------------------------------------------

@pytest.mark.parametrize("emits,expected", [
    ("information", "1A"), ("recommendation", "1B"),
])
def test_advisory_classification(emits, expected):
    c = MlConstituent(
        "x", "X", "f", "advisory", emits, None, None, "src/rl/ppo_collision.py", "r"
    )
    assert c.level == expected == classify(c)


@pytest.mark.parametrize("oversight,expected", [("human", "2A"), ("ai", "2B")])
def test_supervised_actor_classification(oversight, expected):
    c = MlConstituent(
        "x", "X", "f", "supervised_actor", None, oversight, None,
        "src/rl/ppo_collision.py", "r"
    )
    assert c.level == expected == classify(c)


@pytest.mark.parametrize("fallback,expected", [(True, "3A"), (False, "3B")])
def test_decider_classification(fallback, expected):
    c = MlConstituent(
        "x", "X", "f", "decider", None, None, fallback, "src/rl/ppo_collision.py", "r"
    )
    assert c.level == expected == classify(c)


def test_not_operational_is_na():
    c = MlConstituent(
        "x", "X", "f", "not_operational", None, None, None,
        "src/training/domain_rand.py", "r"
    )
    assert c.level == "N/A" == classify(c)


def test_classify_is_deterministic():
    for c in CONSTITUENTS:
        assert classify(c) == classify(c) == c.level


# --- POLICY_MATRIX 와 classify 정확 일치 -----------------------------------

def test_policy_matrix_matches_classify():
    """매트릭스 7칸이 classify 의 도출과 정확히 일치해야 한다."""
    builders = {
        ("advisory", "information"): dict(emits="information"),
        ("advisory", "recommendation"): dict(emits="recommendation"),
        ("supervised_actor", "human"): dict(oversight_by="human"),
        ("supervised_actor", "ai"): dict(oversight_by="ai"),
        ("decider", "fallback"): dict(human_fallback=True),
        ("decider", "no_fallback"): dict(human_fallback=False),
        ("not_operational", "-"): {},
    }
    for role, axis, expected_level in POLICY_MATRIX:
        kwargs = dict(
            constituent_id="probe", name="P", function="f", ai_role=role,
            emits=None, oversight_by=None, human_fallback=None,
            sdacs_module="src/rl/ppo_collision.py", rationale="r",
        )
        kwargs.update(builders[(role, axis)])
        assert classify(MlConstituent(**kwargs)) == expected_level


def test_policy_matrix_covers_all_roles():
    assert {row[0] for row in POLICY_MATRIX} == set(AI_ROLES)


def test_policy_matrix_is_complete():
    """매트릭스가 classify 의 7개 잎 경로를 빠짐없이 인코딩(행 삭제 시 회귀)."""
    assert len(POLICY_MATRIX) == 7
    assert len({(row[0], row[1]) for row in POLICY_MATRIX}) == 7


# --- 정직성: 인용 경로 디스크 실재 -----------------------------------------

def test_cited_modules_exist_on_disk():
    """모든 구성요소의 sdacs_module 이 리포에 실재해야 한다(허위 분류 차단)."""
    for c in CONSTITUENTS:
        path = os.path.join(_REPO_ROOT, c.sdacs_module)
        assert os.path.isfile(path), f"{c.constituent_id}: missing {c.sdacs_module}"


def test_catalog_ids_unique():
    ids = [c.constituent_id for c in CONSTITUENTS]
    assert len(ids) == len(set(ids))


# --- 정직 공시: SDACS 운영 ML 은 전부 Level 1 -------------------------------

def test_all_operational_constituents_are_level1():
    """아키텍처 귀결 핀: 운영 ML 은 advisory 뿐 → 전부 1A/1B."""
    for c in operational_constituents():
        assert c.ai_role == "advisory"
        assert c.level in ("1A", "1B")


def test_no_constituent_is_decider():
    """ML 은 절대 안전 결정권(decider)을 갖지 않는다."""
    assert all(c.ai_role != "decider" for c in CONSTITUENTS)


def test_report_all_operational_level1():
    assert classification_report().all_operational_level1 is True


# --- ClassificationReport 불변식 -------------------------------------------

def test_report_counts_consistent():
    r = classification_report()
    assert r.operational + r.not_operational == r.total
    assert sum(r.by_level.values()) == r.operational


def test_report_by_level_readonly():
    r = classification_report()
    with pytest.raises(TypeError):
        r.by_level["1A"] = 99  # type: ignore[index]


def test_report_rejects_count_mismatch():
    with pytest.raises(ValueError):
        ClassificationReport(
            total=5, operational=3, not_operational=1,  # 3+1 != 5
            max_operational_level="1B", by_level={"1B": 3},
        )


def test_report_rejects_unknown_level_key():
    with pytest.raises(ValueError):
        ClassificationReport(
            total=1, operational=1, not_operational=0,
            max_operational_level="1B", by_level={"9Z": 1},
        )


def test_report_rejects_zero_count_level():
    """by_level 은 관측된 Level 만 담는다 — 0 카운트 항목 거부(계약 명확화)."""
    with pytest.raises(ValueError):
        ClassificationReport(
            total=1, operational=1, not_operational=0,
            max_operational_level="1B", by_level={"1B": 1, "1A": 0},
        )


def test_report_rejects_by_level_sum_mismatch():
    with pytest.raises(ValueError):
        ClassificationReport(
            total=2, operational=2, not_operational=0,
            max_operational_level="1B", by_level={"1B": 1},  # sum 1 != operational 2
        )


def test_report_max_level_burden():
    r = classification_report()
    # 최고 운영 Level 은 1B → 의무 강도 2.
    assert r.max_operational_level == "1B"
    assert r.max_assurance_burden == 2


# --- 매트릭스·매니페스트·조회 ----------------------------------------------

def test_matrix_sorted_and_self_describing():
    rows = classification_matrix()
    assert len(rows) == len(CONSTITUENTS)
    for row in rows:
        assert set(row.keys()) == {
            "constituent_id", "name", "function", "ai_role",
            "level", "sdacs_module", "rationale",
        }
        assert row["level"] in AI_LEVELS


def test_matrix_rows_readonly():
    row = classification_matrix()[0]
    with pytest.raises(TypeError):
        row["level"] = "9Z"  # type: ignore[index]


def test_manifest_serializable_and_consistent():
    import json

    m = manifest()
    assert m["phase"] == 452
    assert m["all_operational_level1"] is True
    assert len(m["constituents"]) == len(CONSTITUENTS)
    json.dumps(m, ensure_ascii=False)  # 직렬화 가능


def test_find_constituent_roundtrip():
    for c in CONSTITUENTS:
        assert find_constituent(c.constituent_id) is c
    with pytest.raises(KeyError):
        find_constituent("nope")


def test_constituents_by_level_partition():
    """Level 별 분할의 합이 전체와 같아야 한다."""
    seen = 0
    for level in AI_LEVELS:
        seen += len(constituents_by_level(level))
    assert seen == len(CONSTITUENTS)


def test_constituents_by_level_invalid():
    with pytest.raises(ValueError):
        constituents_by_level("9Z")


# --- CLI -------------------------------------------------------------------

@pytest.mark.parametrize("flag", [
    "--constituents", "--report", "--levels", "--matrix", "--manifest",
])
def test_cli_runs(flag, capsys):
    assert main([flag]) == 0
    out = capsys.readouterr().out
    assert out.strip()


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "분류 요약" in capsys.readouterr().out
