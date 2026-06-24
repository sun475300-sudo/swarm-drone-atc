"""심화: 시뮬레이션 핵심 불변식 테스트 (다중 시드/결정성/지연/안전 메트릭).

수정 사항(경로효율 leg 완료 판정, advisory 지연 측정)의 견고성을 다양한
조건에서 검증한다. 모든 단언은 '항상 성립해야 하는 불변식' 형태이다.
"""
from __future__ import annotations

import numpy as np
import pytest

import simulation.analytics as analytics_mod
from simulation.simulator import SwarmSimulator

pytestmark = pytest.mark.e2e


def _run_capture(seed: int, n: int, dur: float):
    """완료 구간(actual, planned)을 후킹 캡처하며 시뮬레이션을 실행한다."""
    captured: list[tuple[float, float]] = []
    original = analytics_mod.SimulationAnalytics.record_completed_leg

    def _spy(self, drone_id, actual_m, planned_m):
        captured.append((actual_m, planned_m))
        return original(self, drone_id, actual_m, planned_m)

    analytics_mod.SimulationAnalytics.record_completed_leg = _spy
    try:
        sim = SwarmSimulator(scenario_cfg={"drones": {"default_count": n}}, seed=seed)
        result = sim.run(dur)
    finally:
        analytics_mod.SimulationAnalytics.record_completed_leg = original
    return result, captured


@pytest.fixture(scope="module")
def multiseed():
    """여러 시드의 (결과, 완료구간) 캡처를 1회 계산해 공유."""
    out = []
    for seed in (1, 7, 13, 21, 42):
        out.append((seed, *_run_capture(seed, 8, 600.0)))
    return out


def test_route_efficiency_band_all_seeds(multiseed):
    """완료 구간이 있는 모든 시드에서 경로효율 평균이 합리적 밴드에 있어야 한다."""
    checked = 0
    for seed, result, _ in multiseed:
        if result.completed_legs > 0:
            assert 0.9 <= result.route_efficiency_mean <= 1.6, (
                f"seed={seed}: eff={result.route_efficiency_mean:.4f}"
            )
            checked += 1
    assert checked >= 3, "완료 구간이 있는 시드가 충분치 않음"


def test_no_instant_takeoff_completion_all_seeds(multiseed):
    """어떤 시드에서도 이륙 직후 조기완료(actual<planned*5%)가 없어야 한다."""
    for seed, _, legs in multiseed:
        meaningful = [(a, p) for a, p in legs if p > 10.0 and a > 0.0]
        instant = [(a, p) for a, p in meaningful if a < 0.05 * p]
        assert not instant, f"seed={seed}: 조기완료 {len(instant)}건 (예: {instant[:1]})"


def test_completed_leg_actual_vs_planned_consistent(multiseed):
    """완료 구간의 실제거리는 계획거리와 같은 자릿수여야 한다(수직상승분만 ≠)."""
    for seed, _, legs in multiseed:
        for a, p in legs:
            if p > 1000.0:  # 의미있는 장거리 구간
                assert a > 0.5 * p, f"seed={seed}: actual={a:.1f} << planned={p:.1f}"


def test_determinism_same_seed_identical(multiseed):
    """동일 시드 재실행 시 핵심 메트릭이 완전히 동일해야 한다(재현성)."""
    r1, _ = _run_capture(42, 30, 90.0)
    r2, _ = _run_capture(42, 30, 90.0)
    assert r1.collision_count == r2.collision_count
    assert r1.conflicts_total == r2.conflicts_total
    assert r1.completed_legs == r2.completed_legs
    assert r1.route_efficiency_mean == pytest.approx(r2.route_efficiency_mean, rel=1e-9)
    assert r1.advisory_latency_p99 == pytest.approx(r2.advisory_latency_p99, rel=1e-9)


def test_safety_metric_ranges(multiseed):
    """충돌/충돌해결률/지연 메트릭은 정의역 내에 있어야 한다."""
    for seed, result, _ in multiseed:
        assert result.collision_count >= 0
        assert result.conflicts_total >= 0
        assert 0.0 <= result.conflict_resolution_rate_pct <= 100.0
        assert result.advisory_latency_p50 >= 0.0
        assert result.advisory_latency_p99 >= result.advisory_latency_p50


def test_advisory_latency_populated_and_bounded():
    """어드바이저리가 발부되면 지연이 측정되고 통신모델 한도 내여야 한다."""
    result, _ = _run_capture(42, 40, 120.0)
    if result.advisories_issued > 0:
        assert result.advisory_latency_p99 > 0.0
        assert result.advisory_latency_p99 < 5.0


def test_resolution_rate_formula():
    """해결률 = 1 - collisions/(conflicts+collisions) 공식이 결과와 일치해야 한다."""
    result, _ = _run_capture(42, 50, 90.0)
    total = result.conflicts_total + result.collision_count
    if total > 0:
        expected = 100.0 * (1.0 - result.collision_count / total)
        assert result.conflict_resolution_rate_pct == pytest.approx(expected, rel=1e-6)
