"""ODYSSEY Phase 465 — 표준 벤치마크 스위트 테스트.

`SDACS-SBS-10` 의 핵심 계약을 검증한다: 정확히 10종·식별자 유일·결정적 순서·
10종 전부 scenario_schema 적합·통제 축 상호 배타·매니페스트 JSON 직렬화 가능.
"""
from __future__ import annotations

import json

import pytest

from simulation.standard_scenarios import (
    BENCHMARK_SET,
    SUITE_ID,
    SUITE_VERSION,
    BenchmarkScenario,
    all_scenarios,
    benchmark_manifest,
    get_scenario,
    load_config,
    validate_suite,
)

pytestmark = pytest.mark.unit


class TestSuiteShape:
    def test_exactly_ten_scenarios(self):
        assert len(BENCHMARK_SET) == 10

    def test_ids_are_b01_to_b10_in_order(self):
        ids = [entry.benchmark_id for entry in BENCHMARK_SET]
        assert ids == [f"B{n:02d}" for n in range(1, 11)]

    def test_ids_are_unique(self):
        ids = [entry.benchmark_id for entry in BENCHMARK_SET]
        assert len(set(ids)) == len(ids)

    def test_control_axes_are_mutually_exclusive(self):
        axes = [entry.axis for entry in BENCHMARK_SET]
        assert len(set(axes)) == 10

    def test_all_scenarios_returns_same_set(self):
        assert all_scenarios() == BENCHMARK_SET

    def test_entries_are_immutable(self):
        with pytest.raises(Exception):
            BENCHMARK_SET[0].axis = "mutated"  # type: ignore[misc]


class TestSchemaConformance:
    def test_every_scenario_validates_against_schema(self):
        results = validate_suite()
        assert all(results.values()), [b for b, ok in results.items() if not ok]

    def test_validate_suite_covers_all_ten(self):
        results = validate_suite()
        assert len(results) == 10

    def test_every_source_file_exists(self):
        for entry in BENCHMARK_SET:
            assert entry.path().exists(), entry.source


class TestLookup:
    def test_get_scenario_returns_matching_entry(self):
        entry = get_scenario("B07")
        assert entry.axis == "intrusion_security"

    def test_get_scenario_unknown_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_scenario("B99")

    def test_load_config_reads_scenario_name(self):
        config = load_config(get_scenario("B10"))
        assert config["scenario"] == "s10_nominal_low_density_baseline"


class TestDeterminism:
    def test_manifest_is_deterministic(self):
        assert benchmark_manifest() == benchmark_manifest()

    def test_all_scenarios_order_is_stable(self):
        first = [e.benchmark_id for e in all_scenarios()]
        second = [e.benchmark_id for e in all_scenarios()]
        assert first == second


class TestManifest:
    def test_manifest_is_json_serializable(self):
        dumped = json.dumps(benchmark_manifest(), ensure_ascii=False)
        assert SUITE_ID in dumped

    def test_manifest_header_fields(self):
        manifest = benchmark_manifest()
        assert manifest["suite_id"] == SUITE_ID
        assert manifest["version"] == SUITE_VERSION
        assert manifest["count"] == 10
        assert len(manifest["scenarios"]) == 10

    def test_manifest_entries_carry_axis_and_schema_flag(self):
        for item in benchmark_manifest()["scenarios"]:
            assert item["axis"]
            assert item["schema_valid"] is True
            assert item["scenario"]
            assert item["primary_kpi"]

    def test_manifest_flags_kpi_gap_machine_readably(self):
        # 표제 KPI 가 success_criteria 에 실제로 있을 때만 플래그가 True.
        for item in benchmark_manifest()["scenarios"]:
            criteria = item["success_criteria"] or {}
            expected = item["primary_kpi"] in criteria
            assert item["primary_kpi_in_criteria"] is expected
