"""ODYSSEY Phase 448 — 시나리오 퍼저 속성 기반 테스트 (Hypothesis).

Phase 447 적대적 퍼저(`simulation/scenario_fuzzer.py`)의 핵심 계약을 example
기반 단위 테스트(`test_scenario_fuzzer.py`)에서 *근방 시나리오 공간 전역* 으로
격상한다. 무작위로 생성한 유효 베이스 시나리오 + 임의 시드·인덱스·설정에 대해
다음 불변식을 검증한다:

1. **스키마 보존**: 유효한 베이스의 모든 변이는 `validate_scenario` 를 통과한다
   — "고정 시나리오 통과"에서 "근방 시나리오 공간 전역 통과"로 격상.
2. **입력 불변성**: `mutate` 는 입력 dict 를 변형하지 않는다(새 객체 반환).
3. **결정성**: 동일 시드는 동일 변이 집합을 생성한다(재현성).
4. **분포 재정규화**: 출력 프로파일 분포 합은 1.0(±tol)이다.
5. **거리 순서**: 출력 route 의 min_distance_km < max_distance_km.
6. **적대적 단방향 편향**: adversarial 모드에서 부하 필드는 ↑, 마진 필드는 ↓.

`@settings(max_examples=...)` 합으로 1,000+ 케이스를 탐색한다 (ODYSSEY KPI:
Phase 440 속성 테스트 케이스 1,000).
"""
from __future__ import annotations

import copy

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from simulation.scenario_fuzzer import FuzzConfig, ScenarioFuzzer
from simulation.scenario_schema import validate_scenario

# 분포 합 허용 오차 (scenario_schema._DISTRIBUTION_SUM_TOL 와 일치)
_DIST_TOL = 0.01
# round(x, 3) 가 유발하는 최대 절대 오차 — 단방향 편향 단언의 허용치
_ROUND_TOL = 1e-3

_PROFILES = (
    "COMMERCIAL_DELIVERY",
    "SURVEILLANCE",
    "EMERGENCY",
    "AGRICULTURE",
    "MEDICAL",
)


@st.composite
def _distribution(draw) -> dict:
    """합이 1.0(±tol)인 유효 프로파일 분포를 생성한다."""
    n = draw(st.integers(min_value=1, max_value=len(_PROFILES)))
    weights = draw(
        st.lists(
            st.floats(min_value=0.05, max_value=1.0),
            min_size=n,
            max_size=n,
        )
    )
    total = sum(weights)
    return {k: round(w / total, 4) for k, w in zip(_PROFILES[:n], weights)}


@st.composite
def _base_scenario(draw) -> dict:
    """construction 으로 항상 유효한 베이스 시나리오를 생성한다."""
    return {
        "scenario": "prop_base",
        "description": "property base scenario",
        "drone_count": draw(st.integers(min_value=1, max_value=2000)),
        "simulation_duration_min": draw(st.integers(min_value=1, max_value=120)),
        "arrival_rate_per_min": draw(
            st.floats(min_value=0.1, max_value=200.0)
        ),
        "area_km2": draw(st.floats(min_value=1.0, max_value=2000.0)),
        "drone_profile_distribution": draw(_distribution()),
        "route_generation": {
            "type": "random_od",
            "min_distance_km": draw(st.floats(min_value=0.5, max_value=5.0)),
            "max_distance_km": draw(st.floats(min_value=6.0, max_value=20.0)),
        },
        "success_criteria": {
            "collision_count": 0,
            "conflict_resolution_rate_min": 0.995,
        },
    }


_FUZZ_CONFIG = st.builds(
    FuzzConfig,
    jitter=st.floats(min_value=0.0, max_value=0.5),
    adversarial=st.booleans(),
    adversarial_bias=st.floats(min_value=0.0, max_value=0.5),
    perturb_distribution=st.booleans(),
)

_SEED = st.integers(min_value=0, max_value=2**32 - 1)
_SLOW_OK = [HealthCheck.too_slow]


@settings(max_examples=400, deadline=None, suppress_health_check=_SLOW_OK)
@given(
    base=_base_scenario(),
    cfg=_FUZZ_CONFIG,
    seed=_SEED,
    index=st.integers(min_value=0, max_value=99),
)
def test_variant_always_schema_valid(base, cfg, seed, index) -> None:
    """유효한 베이스의 임의 변이는 항상 스키마 계약을 만족한다."""
    # 전제: 생성된 베이스 자체가 유효해야 단언이 퍼저 책임을 격리한다.
    assert validate_scenario(base).is_valid

    variant = ScenarioFuzzer(cfg, seed=seed).mutate(base, index=index)
    result = validate_scenario(variant)
    assert result.is_valid, result.errors


@settings(max_examples=200, deadline=None, suppress_health_check=_SLOW_OK)
@given(base=_base_scenario(), cfg=_FUZZ_CONFIG, seed=_SEED)
def test_mutate_does_not_modify_input(base, cfg, seed) -> None:
    """mutate 는 입력 dict 를 변형하지 않는다(불변성)."""
    snapshot = copy.deepcopy(base)
    ScenarioFuzzer(cfg, seed=seed).mutate(base, index=3)
    assert base == snapshot


@settings(max_examples=150, deadline=None, suppress_health_check=_SLOW_OK)
@given(
    base=_base_scenario(),
    cfg=_FUZZ_CONFIG,
    seed=st.integers(min_value=0, max_value=10_000),
    n=st.integers(min_value=0, max_value=8),
)
def test_same_seed_produces_identical_variants(base, cfg, seed, n) -> None:
    """동일 시드·설정은 동일 변이 집합을 생성한다(재현성)."""
    a = ScenarioFuzzer(cfg, seed=seed).generate(base, n)
    b = ScenarioFuzzer(cfg, seed=seed).generate(base, n)
    assert a == b


@settings(max_examples=200, deadline=None, suppress_health_check=_SLOW_OK)
@given(base=_base_scenario(), seed=_SEED)
def test_distribution_renormalized_to_one(base, seed) -> None:
    """분포 변이 시 출력 합은 1.0(±tol)으로 재정규화된다."""
    cfg = FuzzConfig(perturb_distribution=True)
    variant = ScenarioFuzzer(cfg, seed=seed).mutate(base, index=0)
    total = sum(variant["drone_profile_distribution"].values())
    assert abs(total - 1.0) <= _DIST_TOL


@settings(max_examples=200, deadline=None, suppress_health_check=_SLOW_OK)
@given(base=_base_scenario(), cfg=_FUZZ_CONFIG, seed=_SEED)
def test_route_distance_ordering_preserved(base, cfg, seed) -> None:
    """출력 route 의 min_distance_km 는 항상 max_distance_km 보다 작다."""
    variant = ScenarioFuzzer(cfg, seed=seed).mutate(base, index=0)
    route = variant["route_generation"]
    assert route["min_distance_km"] < route["max_distance_km"]


@settings(max_examples=200, deadline=None, suppress_health_check=_SLOW_OK)
@given(
    base=_base_scenario(),
    seed=_SEED,
    jitter=st.floats(min_value=0.0, max_value=0.5),
    bias=st.floats(min_value=0.0, max_value=0.5),
)
def test_adversarial_biases_load_up_margin_down(
    base, seed, jitter, bias
) -> None:
    """adversarial 모드는 부하 필드를 ↑, 안전 마진 필드를 ↓ 단방향 편향한다."""
    cfg = FuzzConfig(jitter=jitter, adversarial=True, adversarial_bias=bias)
    variant = ScenarioFuzzer(cfg, seed=seed).mutate(base, index=0)

    # 부하 필드: 증가 (정수 드론 수는 단조 반올림으로 정확히 ≥).
    assert variant["drone_count"] >= base["drone_count"]
    assert (
        variant["arrival_rate_per_min"]
        >= base["arrival_rate_per_min"] - _ROUND_TOL
    )
    # 마진 필드: 감소 (round(.,3) 오차만큼만 허용).
    assert variant["area_km2"] <= base["area_km2"] + _ROUND_TOL
