"""ODYSSEY Phase 461 — ASTM F38 군집 관제 시험 방법 모듈 단위 테스트."""
from __future__ import annotations

import pytest

from simulation import swarm_test_method as stm


# --- TestMethod 검증 ---------------------------------------------------------
def test_registry_is_nonempty():
    assert len(stm.methods()) >= 7


def test_get_method_by_id():
    m = stm.get_method("SM-TM-01")
    assert m.metric_key == "conflict_resolution_rate"
    assert m.direction == stm.DIRECTION_GE


def test_get_method_unknown_raises():
    with pytest.raises(KeyError):
        stm.get_method("SM-TM-99")


def test_method_rejects_blank_fields():
    with pytest.raises(ValueError):
        stm.TestMethod("", "t", "k", "ratio", 1.0, stm.DIRECTION_GE, "r")


def test_method_rejects_bad_direction():
    with pytest.raises(ValueError):
        stm.TestMethod("X", "t", "k", "ratio", 1.0, "UP", "r")


def test_method_rejects_nan_threshold():
    with pytest.raises(ValueError):
        stm.TestMethod("X", "t", "k", "ratio", float("nan"), stm.DIRECTION_GE, "r")


def test_method_rejects_infinite_threshold():
    with pytest.raises(ValueError):
        stm.TestMethod("X", "t", "k", "ratio", float("inf"), stm.DIRECTION_GE, "r")
    with pytest.raises(ValueError):
        stm.TestMethod("X", "t", "k", "ratio", float("-inf"), stm.DIRECTION_LE, "r")


def test_method_is_frozen():
    m = stm.get_method("SM-TM-01")
    with pytest.raises(AttributeError):
        m.threshold = 0.0  # type: ignore[misc]


# --- evaluate_method 판정 ----------------------------------------------------
def test_ge_pass_at_and_above_threshold():
    m = stm.get_method("SM-TM-01")  # GE 0.95
    assert stm.evaluate_method(m, 0.95).verdict == stm.PASS
    assert stm.evaluate_method(m, 0.99).verdict == stm.PASS


def test_ge_fail_below_threshold():
    m = stm.get_method("SM-TM-01")
    out = stm.evaluate_method(m, 0.90)
    assert out.verdict == stm.FAIL
    assert not out.is_pass


def test_le_pass_at_and_below_threshold():
    m = stm.get_method("SM-TM-06")  # LE 3.0 s
    assert stm.evaluate_method(m, 3.0).verdict == stm.PASS
    assert stm.evaluate_method(m, 1.5).verdict == stm.PASS


def test_le_fail_above_threshold():
    m = stm.get_method("SM-TM-06")
    assert stm.evaluate_method(m, 4.0).verdict == stm.FAIL


def test_missing_measurement_is_inconclusive_not_pass():
    m = stm.get_method("SM-TM-01")
    out = stm.evaluate_method(m, None)
    assert out.verdict == stm.INCONCLUSIVE
    assert not out.is_pass


def test_zero_collision_le_zero():
    m = stm.get_method("SM-TM-02")  # LE 0
    assert stm.evaluate_method(m, 0.0).verdict == stm.PASS
    assert stm.evaluate_method(m, 1.0).verdict == stm.FAIL


def test_evaluate_is_deterministic():
    m = stm.get_method("SM-TM-03")
    first = stm.evaluate_method(m, 5.0)
    second = stm.evaluate_method(m, 5.0)
    assert first == second


# --- evaluate_suite ----------------------------------------------------------
def test_suite_conformant_on_sdacs_baseline():
    result = stm.evaluate_suite(stm.SDACS_BASELINE)
    assert result.is_conformant
    assert result.failed == 0
    assert result.inconclusive == 0
    assert result.passed == len(stm.methods())


def test_suite_non_conformant_on_missing_metric():
    measured = dict(stm.SDACS_BASELINE)
    del measured["conflict_resolution_rate"]
    result = stm.evaluate_suite(measured)
    assert not result.is_conformant
    assert result.inconclusive == 1


def test_suite_non_conformant_on_failure():
    measured = dict(stm.SDACS_BASELINE)
    measured["collisions"] = 3.0
    result = stm.evaluate_suite(measured)
    assert not result.is_conformant
    assert result.failed == 1


def test_empty_suite_not_conformant():
    result = stm.evaluate_suite({})
    assert not result.is_conformant
    assert result.passed == 0
    assert result.inconclusive == len(stm.methods())


def test_suite_summary_text():
    result = stm.evaluate_suite(stm.SDACS_BASELINE)
    assert "CONFORMANT" in result.summary()


def test_suite_outcomes_cover_all_methods():
    result = stm.evaluate_suite(stm.SDACS_BASELINE)
    assert len(result.outcomes) == len(stm.methods())


# --- validate_registry -------------------------------------------------------
def test_registry_is_valid():
    result = stm.validate_registry()
    assert result.is_valid
    assert result.errors == ()


def test_all_methods_marked_proposed():
    assert all(m.proposed for m in stm.methods())


def test_suite_result_rejects_inconsistent_counts():
    result = stm.evaluate_suite(stm.SDACS_BASELINE)
    with pytest.raises(ValueError):
        stm.SuiteResult(outcomes=result.outcomes, passed=0, failed=0, inconclusive=0)


def test_metric_keys_are_unique():
    keys = [m.metric_key for m in stm.methods()]
    assert len(keys) == len(set(keys))


def test_method_ids_are_unique():
    ids = [m.method_id for m in stm.methods()]
    assert len(ids) == len(set(ids))


# --- manifest / markdown -----------------------------------------------------
def test_manifest_is_json_serializable():
    import json

    blob = json.dumps(stm.manifest())
    assert "ODYSSEY-461" in blob
    assert stm.manifest()["method_count"] == len(stm.methods())


def test_manifest_marks_proposed():
    assert stm.manifest()["proposed"] is True


def test_markdown_table_has_all_methods():
    table = stm.markdown_table()
    for m in stm.methods():
        assert m.method_id in table


def test_markdown_escapes_pipe():
    # _escape_md 는 파이프를 이스케이프해 표를 깨지 않는다.
    assert stm._escape_md("a|b") == "a\\|b"


# --- CLI ---------------------------------------------------------------------
def test_cli_validate_returns_zero():
    assert stm._cli(["--validate"]) == 0


def test_cli_evaluate_returns_zero():
    assert stm._cli(["--evaluate"]) == 0


def test_cli_list_default_returns_zero():
    assert stm._cli([]) == 0


def test_cli_manifest_returns_zero():
    assert stm._cli(["--manifest"]) == 0


def test_cli_markdown_returns_zero():
    assert stm._cli(["--markdown"]) == 0
