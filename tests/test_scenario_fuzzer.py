"""ODYSSEY Phase 447 — 적대적 시나리오 퍼저 단위 테스트."""
from __future__ import annotations

import copy

import pytest

from simulation.scenario_fuzzer import FuzzConfig, ScenarioFuzzer
from simulation.scenario_schema import validate_scenario


@pytest.fixture
def base_scenario() -> dict:
    """대표 베이스 시나리오 (high_density 형태)."""
    return {
        "scenario": "s01_normal_high_density",
        "description": "정상 고밀도 교통",
        "drone_count": 100,
        "simulation_duration_min": 10,
        "arrival_rate_per_min": 20,
        "area_km2": 100,
        "drone_profile_distribution": {
            "COMMERCIAL_DELIVERY": 0.6,
            "SURVEILLANCE": 0.3,
            "EMERGENCY": 0.1,
        },
        "route_generation": {
            "type": "random_od",
            "min_distance_km": 1.0,
            "max_distance_km": 8.0,
        },
        "success_criteria": {
            "collision_count": 0,
            "conflict_resolution_rate_min": 0.995,
        },
    }


def test_same_seed_produces_identical_variants(base_scenario: dict) -> None:
    """동일 시드는 동일 변이 집합을 생성한다(재현성)."""
    a = ScenarioFuzzer(seed=7).generate(base_scenario, 5)
    b = ScenarioFuzzer(seed=7).generate(base_scenario, 5)
    assert a == b


def test_different_seed_produces_different_variants(base_scenario: dict) -> None:
    """다른 시드는 다른 변이를 생성한다."""
    a = ScenarioFuzzer(seed=1).generate(base_scenario, 5)
    b = ScenarioFuzzer(seed=2).generate(base_scenario, 5)
    assert a != b


def test_input_is_not_mutated(base_scenario: dict) -> None:
    """입력 dict 는 변형되지 않는다(불변성)."""
    snapshot = copy.deepcopy(base_scenario)
    ScenarioFuzzer(seed=3).generate(base_scenario, 10)
    assert base_scenario == snapshot


def test_variants_pass_schema_validation(base_scenario: dict) -> None:
    """생성된 모든 변이는 스키마 검증을 통과한다."""
    for cfg in (FuzzConfig(), FuzzConfig(adversarial=True)):
        variants = ScenarioFuzzer(cfg, seed=11).generate(base_scenario, 30)
        for v in variants:
            result = validate_scenario(v)
            assert result.is_valid, (v["scenario"], result.errors)


def test_positive_int_and_float_clamping(base_scenario: dict) -> None:
    """드론 수는 양의 정수, 면적/도착률은 양수로 유지된다."""
    variants = ScenarioFuzzer(FuzzConfig(jitter=0.9), seed=5).generate(
        base_scenario, 50
    )
    for v in variants:
        assert isinstance(v["drone_count"], int) and v["drone_count"] >= 1
        assert v["arrival_rate_per_min"] > 0
        assert v["area_km2"] > 0


def test_distribution_renormalized_to_one(base_scenario: dict) -> None:
    """프로파일 분포 합은 1.0(±0.01)으로 재정규화된다."""
    variants = ScenarioFuzzer(seed=9).generate(base_scenario, 20)
    for v in variants:
        total = sum(v["drone_profile_distribution"].values())
        assert abs(total - 1.0) <= 0.01


def test_route_distance_min_less_than_max(base_scenario: dict) -> None:
    """경로 최소거리 < 최대거리가 항상 보장된다."""
    variants = ScenarioFuzzer(FuzzConfig(jitter=0.8), seed=13).generate(
        base_scenario, 50
    )
    for v in variants:
        rg = v["route_generation"]
        assert rg["min_distance_km"] < rg["max_distance_km"]


def test_success_criteria_preserved(base_scenario: dict) -> None:
    """합격 임계값(success_criteria)은 변이되지 않는다."""
    variants = ScenarioFuzzer(seed=17).generate(base_scenario, 10)
    for v in variants:
        assert v["success_criteria"] == base_scenario["success_criteria"]


def test_unique_variant_names(base_scenario: dict) -> None:
    """각 변이는 고유한 scenario 이름을 가진다."""
    variants = ScenarioFuzzer(seed=21).generate(base_scenario, 12)
    names = [v["scenario"] for v in variants]
    assert len(names) == len(set(names))


def test_adversarial_increases_average_load(base_scenario: dict) -> None:
    """적대적 모드는 평균 부하(드론 수)를 베이스 이상으로 편향한다."""
    adv = ScenarioFuzzer(FuzzConfig(adversarial=True), seed=4).generate(
        base_scenario, 40
    )
    mean_count = sum(v["drone_count"] for v in adv) / len(adv)
    assert mean_count >= base_scenario["drone_count"]


def test_adversarial_reduces_average_margin(base_scenario: dict) -> None:
    """적대적 모드는 평균 공역 면적(안전 마진)을 베이스 이하로 편향한다."""
    adv = ScenarioFuzzer(FuzzConfig(adversarial=True), seed=8).generate(
        base_scenario, 40
    )
    mean_area = sum(v["area_km2"] for v in adv) / len(adv)
    assert mean_area <= base_scenario["area_km2"]


def test_generate_zero_returns_empty(base_scenario: dict) -> None:
    """n=0 은 빈 리스트를 반환한다."""
    assert ScenarioFuzzer(seed=1).generate(base_scenario, 0) == []


def test_generate_negative_raises(base_scenario: dict) -> None:
    """음수 n 은 ValueError 를 발생시킨다."""
    with pytest.raises(ValueError):
        ScenarioFuzzer(seed=1).generate(base_scenario, -1)


def test_scenario_without_optional_fields(base_scenario: dict) -> None:
    """선택 필드가 없는 최소 시나리오도 처리한다."""
    minimal = {
        "scenario": "minimal",
        "description": "최소 시나리오",
        "simulation_duration_min": 5,
        "drone_count": 10,
    }
    variants = ScenarioFuzzer(seed=2).generate(minimal, 5)
    for v in variants:
        assert validate_scenario(v).is_valid
