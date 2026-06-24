"""ODYSSEY Phase 466 — 텔레메트리 스키마 검증기 테스트.

`jsonschema` 설치 여부와 무관하게 동작하도록 폴백 검증 경로를 직접 검사하고,
공개 API(`validate_telemetry`)는 정본/폴백 어느 쪽이 활성화돼도 동일한
유효/무효 판정을 내야 함을 확인한다.
"""
from __future__ import annotations

import copy
import json

import pytest

from simulation.telemetry_validator import (
    CANONICAL_EXAMPLE,
    ValidationResult,
    _validate_fallback,
    load_schema,
    validate_telemetry,
    validate_telemetry_file,
)

pytestmark = pytest.mark.unit


def _valid() -> dict:
    return copy.deepcopy(CANONICAL_EXAMPLE)


class TestCanonicalExample:
    def test_example_is_valid_via_public_api(self):
        result = validate_telemetry(_valid())
        assert result.is_valid
        assert result.errors == ()
        assert result.summary() == "VALID"

    def test_example_passes_fallback_path(self):
        # jsonschema 미설치 환경을 모사 — 폴백이 표준 예제를 통과시켜야 한다.
        assert _validate_fallback(_valid()) == []

    def test_example_matches_schema_required_keys(self):
        schema = load_schema()
        assert set(schema["required"]) <= CANONICAL_EXAMPLE.keys()


class TestTopLevel:
    def test_rejects_non_mapping(self):
        assert _validate_fallback([1, 2, 3])

    @pytest.mark.parametrize("missing", ["t", "drones", "stats", "backend"])
    def test_rejects_missing_required_field(self, missing):
        payload = _valid()
        del payload[missing]
        result = validate_telemetry(payload)
        assert not result.is_valid
        assert any(missing in e for e in result.errors)

    def test_rejects_negative_time(self):
        payload = _valid()
        payload["t"] = -0.1
        assert not validate_telemetry(payload).is_valid

    def test_rejects_non_string_backend(self):
        payload = _valid()
        payload["backend"] = 42
        assert not validate_telemetry(payload).is_valid


class TestDrones:
    def test_rejects_non_array_drones(self):
        payload = _valid()
        payload["drones"] = {}
        assert not validate_telemetry(payload).is_valid

    def test_empty_drones_is_valid(self):
        payload = _valid()
        payload["drones"] = []
        assert validate_telemetry(payload).is_valid

    @pytest.mark.parametrize("key", ["id", "pos", "vel", "phase", "battery"])
    def test_rejects_missing_drone_key(self, key):
        payload = _valid()
        del payload["drones"][0][key]
        assert not validate_telemetry(payload).is_valid

    def test_rejects_empty_drone_id(self):
        payload = _valid()
        payload["drones"][0]["id"] = ""
        assert not validate_telemetry(payload).is_valid

    @pytest.mark.parametrize("bad", [[1.0, 2.0], [1.0, 2.0, 3.0, 4.0], "xyz"])
    def test_rejects_wrong_length_pos(self, bad):
        payload = _valid()
        payload["drones"][0]["pos"] = bad
        assert not validate_telemetry(payload).is_valid

    def test_rejects_non_numeric_vel_component(self):
        payload = _valid()
        payload["drones"][0]["vel"] = [1.0, "x", 0.0]
        assert not validate_telemetry(payload).is_valid

    @pytest.mark.parametrize("bad", [-1.0, 100.1])
    def test_rejects_out_of_range_battery(self, bad):
        payload = _valid()
        payload["drones"][0]["battery"] = bad
        assert not validate_telemetry(payload).is_valid

    def test_battery_bounds_inclusive(self):
        for value in (0, 100):
            payload = _valid()
            payload["drones"][0]["battery"] = value
            assert validate_telemetry(payload).is_valid


class TestStats:
    def test_rejects_non_mapping_stats(self):
        payload = _valid()
        payload["stats"] = []
        assert not validate_telemetry(payload).is_valid

    @pytest.mark.parametrize("key", ["collisions", "near_misses", "conflicts", "advisories"])
    def test_rejects_missing_stat(self, key):
        payload = _valid()
        del payload["stats"][key]
        assert not validate_telemetry(payload).is_valid

    def test_rejects_negative_counter(self):
        payload = _valid()
        payload["stats"]["collisions"] = -1
        assert not validate_telemetry(payload).is_valid

    def test_rejects_float_counter(self):
        payload = _valid()
        payload["stats"]["conflicts"] = 3.5
        assert not validate_telemetry(payload).is_valid

    def test_rejects_bool_counter(self):
        # bool 은 int 의 하위형이지만 카운터로 허용하지 않는다.
        payload = _valid()
        payload["stats"]["collisions"] = True
        assert not validate_telemetry(payload).is_valid


class TestFileAndResult:
    def test_missing_file(self):
        result = validate_telemetry_file("/nonexistent/telemetry.json")
        assert not result.is_valid
        assert any("파일 없음" in e for e in result.errors)

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{ not json", encoding="utf-8")
        result = validate_telemetry_file(str(p))
        assert not result.is_valid

    def test_valid_file_roundtrip(self, tmp_path):
        p = tmp_path / "snap.json"
        p.write_text(json.dumps(CANONICAL_EXAMPLE), encoding="utf-8")
        assert validate_telemetry_file(str(p)).is_valid

    def test_result_is_frozen(self):
        result = ValidationResult(is_valid=True, errors=())
        with pytest.raises(Exception):
            result.is_valid = False  # type: ignore[misc]
