"""
GENESIS Phase 322 — .sdacs-scenario 스키마 검증기 테스트
========================================================
config/scenario_params/*.yaml 실측 시나리오가 계약을 만족하는지,
그리고 잘못된 입력이 정확히 거부되는지 검증한다.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from simulation.scenario_schema import (
    validate_scenario,
    validate_scenario_file,
)

_ROOT = Path(__file__).resolve().parent.parent
_SCENARIO_DIR = _ROOT / "config" / "scenario_params"
_SCHEMA_PATH = _ROOT / "docs" / "schemas" / "sdacs-scenario.schema.json"


def _valid_minimal() -> dict:
    """검증을 통과하는 최소 시나리오 dict 를 반환한다."""
    return {
        "scenario": "s_test_minimal",
        "description": "테스트용 최소 시나리오",
        "simulation_duration_min": 10,
    }


# ── 실측 시나리오 회귀 ──────────────────────────────────────────────────────

def _flat_scenario_files() -> list[Path]:
    return sorted(_SCENARIO_DIR.glob("*.yaml"))


def test_scenario_dir_has_files():
    """시나리오 디렉터리에 검증 대상 파일이 존재한다."""
    assert _flat_scenario_files(), "config/scenario_params/*.yaml 이 비어 있음"


@pytest.mark.parametrize(
    "path", _flat_scenario_files(), ids=lambda p: p.stem
)
def test_real_scenarios_are_valid(path: Path):
    """모든 실측 flat 시나리오는 .sdacs-scenario 계약을 만족한다."""
    result = validate_scenario_file(path)
    assert result.is_valid, f"{path.name} 검증 실패: {result.errors}"


# ── 필수 필드 ───────────────────────────────────────────────────────────────

def test_missing_scenario_id_is_invalid():
    """scenario 식별자가 없으면 거부된다."""
    raw = _valid_minimal()
    del raw["scenario"]
    result = validate_scenario(raw)
    assert not result.is_valid
    assert any("scenario" in e for e in result.errors)


def test_missing_description_is_invalid():
    """description 이 없으면 거부된다."""
    raw = _valid_minimal()
    del raw["description"]
    result = validate_scenario(raw)
    assert not result.is_valid
    assert any("description" in e for e in result.errors)


def test_empty_description_is_invalid():
    """description 이 공백만이면 거부된다."""
    raw = _valid_minimal()
    raw["description"] = "   "
    result = validate_scenario(raw)
    assert not result.is_valid


def test_missing_duration_is_invalid():
    """시뮬레이션 시간이 둘 다 없으면 거부된다."""
    raw = _valid_minimal()
    del raw["simulation_duration_min"]
    result = validate_scenario(raw)
    assert not result.is_valid
    assert any("시간" in e for e in result.errors)


def test_duration_in_seconds_is_valid():
    """초 단위 시간만 있어도 유효하다."""
    raw = _valid_minimal()
    del raw["simulation_duration_min"]
    raw["simulation_duration_s"] = 600
    result = validate_scenario(raw)
    assert result.is_valid


def test_non_positive_duration_is_invalid():
    """0 이하 시간은 거부된다."""
    raw = _valid_minimal()
    raw["simulation_duration_min"] = 0
    result = validate_scenario(raw)
    assert not result.is_valid


# ── 타입·범위 ───────────────────────────────────────────────────────────────

def test_negative_drone_count_is_invalid():
    """음수 드론 수는 거부된다."""
    raw = _valid_minimal()
    raw["drone_count"] = -5
    result = validate_scenario(raw)
    assert not result.is_valid


def test_bool_drone_count_is_invalid():
    """bool 은 정수로 위장하므로 명시적으로 거부된다."""
    raw = _valid_minimal()
    raw["drone_count"] = True
    result = validate_scenario(raw)
    assert not result.is_valid


def test_mapping_field_must_be_mapping():
    """매핑이어야 하는 필드에 리스트가 오면 거부된다."""
    raw = _valid_minimal()
    raw["weather"] = ["bad"]
    result = validate_scenario(raw)
    assert not result.is_valid


def test_non_dict_top_level_is_invalid():
    """최상위가 dict 가 아니면 거부된다."""
    result = validate_scenario(["not", "a", "dict"])
    assert not result.is_valid


# ── 프로파일 분포 ───────────────────────────────────────────────────────────

def test_distribution_summing_to_one_is_valid():
    """합이 1.0 인 분포는 유효하다."""
    raw = _valid_minimal()
    raw["drone_profile_distribution"] = {"A": 0.6, "B": 0.3, "C": 0.1}
    result = validate_scenario(raw)
    assert result.is_valid


def test_distribution_not_summing_to_one_is_invalid():
    """합이 1.0 에서 벗어난 분포는 거부된다."""
    raw = _valid_minimal()
    raw["drone_profile_distribution"] = {"A": 0.6, "B": 0.6}
    result = validate_scenario(raw)
    assert not result.is_valid


def test_distribution_within_tolerance_is_valid():
    """허용 오차(±0.01) 내 분포는 유효하다."""
    raw = _valid_minimal()
    raw["drone_profile_distribution"] = {"A": 0.333, "B": 0.333, "C": 0.334}
    result = validate_scenario(raw)
    assert result.is_valid


# ── 경고 ────────────────────────────────────────────────────────────────────

def test_unknown_key_produces_warning_not_error():
    """알 수 없는 키는 경고일 뿐 유효성을 깨지 않는다."""
    raw = _valid_minimal()
    raw["mystery_field"] = 123
    result = validate_scenario(raw)
    assert result.is_valid
    assert any("mystery_field" in w for w in result.warnings)


# ── 파일 IO ─────────────────────────────────────────────────────────────────

def test_missing_file_is_invalid():
    """존재하지 않는 파일은 거부된다."""
    result = validate_scenario_file(_SCENARIO_DIR / "does_not_exist.yaml")
    assert not result.is_valid


def test_result_summary_is_string():
    """summary() 는 사람이 읽는 문자열을 반환한다."""
    result = validate_scenario(_valid_minimal())
    assert isinstance(result.summary(), str)
    assert "VALID" in result.summary()


def test_result_is_frozen():
    """ValidationResult 는 불변(frozen)이다."""
    result = validate_scenario(_valid_minimal())
    with pytest.raises(Exception):
        result.is_valid = False  # type: ignore[misc]


# ── JSON Schema 파일 정합성 ─────────────────────────────────────────────────

def test_schema_file_exists_and_parses():
    """동봉된 JSON Schema 파일이 존재하고 파싱된다."""
    assert _SCHEMA_PATH.exists(), "sdacs-scenario.schema.json 이 없음"
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["required"] == ["scenario", "description"]
    assert schema["type"] == "object"
