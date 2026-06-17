"""
시나리오 포맷 버전 마이그레이션 도구 테스트 (ODYSSEY Phase 485)
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from simulation.scenario_migration import (
    CURRENT_VERSION,
    LEGACY_VERSION,
    MigrationResult,
    detect_version,
    migrate_file,
    migrate_scenario,
)
from simulation.scenario_schema import validate_scenario

_SCENARIO_DIR = Path(__file__).resolve().parent.parent / "config" / "scenario_params"


# ── detect_version ─────────────────────────────────────────────────────────

def test_unstamped_scenario_detected_as_legacy():
    assert detect_version({"scenario": "x"}) == LEGACY_VERSION


def test_stamped_scenario_returns_its_version():
    assert detect_version({"schema_version": "2.0"}) == "2.0"
    assert detect_version({"schema_version": "3.1"}) == "3.1"


def test_detect_version_rejects_non_dict():
    with pytest.raises(ValueError):
        detect_version(["not", "a", "dict"])  # type: ignore[arg-type]


def test_detect_version_rejects_non_string_stamp():
    with pytest.raises(ValueError):
        detect_version({"schema_version": 2.0})


# ── duration 정규화 ─────────────────────────────────────────────────────────

def test_duration_min_converted_to_seconds():
    result = migrate_scenario({"scenario": "s", "simulation_duration_min": 10})
    assert result.scenario["simulation_duration_s"] == 600.0
    assert "simulation_duration_min" not in result.scenario


def test_existing_seconds_preserved_and_min_dropped():
    raw = {"scenario": "s", "simulation_duration_s": 120, "simulation_duration_min": 99}
    result = migrate_scenario(raw)
    # 초가 이미 있으면 권위 — 분은 버려진다
    assert result.scenario["simulation_duration_s"] == 120
    assert "simulation_duration_min" not in result.scenario


# ── count 정규화 ────────────────────────────────────────────────────────────

def test_total_drone_count_collapsed_to_drone_count():
    result = migrate_scenario({"scenario": "s", "total_drone_count": 240})
    assert result.scenario["drone_count"] == 240
    assert "total_drone_count" not in result.scenario


def test_base_drone_count_collapsed():
    result = migrate_scenario({"scenario": "s", "base_drone_count": 50})
    assert result.scenario["drone_count"] == 50
    assert "base_drone_count" not in result.scenario


def test_nested_base_traffic_count_collapsed():
    raw = {"scenario": "s", "base_traffic": {"drone_count": 30, "rate": 5}}
    result = migrate_scenario(raw)
    assert result.scenario["drone_count"] == 30
    # base_traffic 의 다른 필드는 보존
    assert result.scenario["base_traffic"] == {"rate": 5}


def test_base_traffic_dropped_when_only_count():
    raw = {"scenario": "s", "base_traffic": {"drone_count": 30}}
    result = migrate_scenario(raw)
    assert "base_traffic" not in result.scenario


def test_drone_count_has_precedence_over_total():
    raw = {"scenario": "s", "drone_count": 10, "total_drone_count": 999}
    result = migrate_scenario(raw)
    assert result.scenario["drone_count"] == 10
    assert "total_drone_count" not in result.scenario
    # 잉여 total_drone_count 제거가 changes 에 기록됨
    assert any("total_drone_count" in c and "제거" in c for c in result.changes)


def test_non_integer_count_rejected():
    # 어드바이저 HIGH: float count 무음 절삭 금지 — 스키마는 양의 정수 요구
    with pytest.raises(ValueError):
        migrate_scenario({"scenario": "s", "total_drone_count": 3.7})


def test_bool_count_rejected():
    with pytest.raises(ValueError):
        migrate_scenario({"scenario": "s", "drone_count": True})


# ── 스탬프 ───────────────────────────────────────────────────────────────────

def test_legacy_gets_stamped_current():
    result = migrate_scenario({"scenario": "s", "drone_count": 5})
    assert result.scenario["schema_version"] == CURRENT_VERSION
    assert result.from_version == LEGACY_VERSION
    assert result.to_version == CURRENT_VERSION
    assert result.migrated is True


# ── 멱등성 ───────────────────────────────────────────────────────────────────

def test_migration_is_idempotent():
    raw = {"scenario": "s", "simulation_duration_min": 10, "total_drone_count": 50}
    once = migrate_scenario(raw).scenario
    twice = migrate_scenario(once)
    assert twice.scenario == once
    assert twice.migrated is False
    assert twice.changes == ()


def test_already_canonical_unchanged():
    canonical = {
        "scenario": "s",
        "schema_version": CURRENT_VERSION,
        "drone_count": 100,
        "simulation_duration_s": 600.0,
    }
    result = migrate_scenario(canonical)
    assert result.migrated is False
    assert result.scenario == canonical


def test_v2_stamped_but_dirty_records_cleanup():
    # 어드바이저 HIGH: v2.0 스탬프지만 잉여 키가 남은 경우 — 정리가
    # changes/migrated 에 반드시 반영되어 출력 차이가 표면화돼야 한다.
    dirty = {
        "scenario": "s",
        "schema_version": CURRENT_VERSION,
        "drone_count": 10,
        "base_drone_count": 5,
        "simulation_duration_s": 600.0,
        "simulation_duration_min": 99,
    }
    result = migrate_scenario(dirty)
    assert result.migrated is True
    assert result.changes != ()
    assert "base_drone_count" not in result.scenario
    assert "simulation_duration_min" not in result.scenario
    assert result.scenario["drone_count"] == 10
    # 정리된 출력은 멱등
    assert migrate_scenario(result.scenario).migrated is False


# ── 불변성 ───────────────────────────────────────────────────────────────────

def test_original_dict_not_mutated():
    raw = {"scenario": "s", "simulation_duration_min": 10}
    migrate_scenario(raw)
    assert raw == {"scenario": "s", "simulation_duration_min": 10}


# ── 결정성 ───────────────────────────────────────────────────────────────────

def test_migration_is_deterministic():
    raw = {"scenario": "s", "simulation_duration_min": 15, "base_drone_count": 50}
    a = migrate_scenario(raw)
    b = migrate_scenario(raw)
    assert a.scenario == b.scenario
    assert a.changes == b.changes


# ── 출력은 스키마 계약 충족 ────────────────────────────────────────────────────

@pytest.mark.parametrize("path", sorted(_SCENARIO_DIR.glob("*.yaml")), ids=lambda p: p.stem)
def test_all_repo_scenarios_migrate_to_valid_canonical(path):
    result = migrate_file(path)
    migrated = result.scenario
    # canonical 규약
    assert migrated["schema_version"] == CURRENT_VERSION
    assert "simulation_duration_min" not in migrated
    assert "total_drone_count" not in migrated
    assert "base_drone_count" not in migrated
    # 스키마 계약 (러너 호환) — 경고 없이 유효
    res = validate_scenario(migrated)
    assert res.is_valid, res.errors
    assert res.warnings == ()


def test_multi_city_count_restored_for_runner():
    # total_drone_count 만 갖던 multi_city 가 drone_count 로 정규화되어
    # 러너가 드론 수를 읽을 수 있게 됨. 기대값은 소스 YAML 에서 직접 읽어
    # YAML 변경 시에도 어설션이 동조하도록 한다.
    path = _SCENARIO_DIR / "multi_city.yaml"
    expected = yaml.safe_load(path.read_text(encoding="utf-8"))["total_drone_count"]
    result = migrate_file(path)
    assert result.scenario["drone_count"] == expected
    assert "total_drone_count" not in result.scenario


# ── 파일 라운드트립 ────────────────────────────────────────────────────────────

def test_migrate_file_writes_canonical_yaml(tmp_path):
    src = tmp_path / "in.yaml"
    src.write_text(
        "scenario: t\nsimulation_duration_min: 5\ntotal_drone_count: 20\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.yaml"
    migrate_file(src, out_path=out)
    reloaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert reloaded["schema_version"] == CURRENT_VERSION
    assert reloaded["simulation_duration_s"] == 300.0
    assert reloaded["drone_count"] == 20
    # 재변환해도 동일 (라운드트립 멱등)
    assert migrate_scenario(reloaded).migrated is False


def test_migrate_file_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        migrate_file(tmp_path / "nope.yaml")


def test_migrate_file_non_mapping_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        migrate_file(bad)


# ── MigrationResult ─────────────────────────────────────────────────────────

def test_result_summary_reports_change_count():
    result = migrate_scenario({"scenario": "s", "simulation_duration_min": 10})
    assert "→" in result.summary()
    assert isinstance(result, MigrationResult)


def test_result_summary_canonical_no_change():
    canonical = {"scenario": "s", "schema_version": CURRENT_VERSION}
    summary = migrate_scenario(canonical).summary()
    assert "변경 없음" in summary
