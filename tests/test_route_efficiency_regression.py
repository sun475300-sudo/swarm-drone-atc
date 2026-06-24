"""경로 효율(route_efficiency) 회귀 테스트.

버그: 플래너가 이륙 구간을 출발점 좌표로 중복 waypoint(start@0m, start@60m)로
생성하여, 드론이 ENROUTE 진입 첫 틱에 동일좌표 waypoint를 연쇄 소비하면서
leg가 '즉시 완료' 처리되던 문제. 이로 인해 완료 구간의 실제거리가 수직
상승분(60m)뿐이고 route_efficiency가 비현실적으로 낮게(≈0.01) 집계되었다.

수정 후에는 leg 완료가 '목표(goal) 도달' 기준으로만 판정되어야 하며,
완료 구간의 경로 효율(actual/planned)이 1.0 근방의 합리적 범위에 있어야 한다.
"""
from __future__ import annotations

import pytest

from simulation.simulator import SwarmSimulator

pytestmark = pytest.mark.e2e


def _run(seed: int = 7, n_drones: int = 8, duration_s: float = 800.0):
    """기본 전체 공역에서 leg가 실제로 완료될 만큼 충분히 긴 런을 수행한다."""
    sim = SwarmSimulator(
        scenario_cfg={"drones": {"default_count": n_drones}},
        seed=seed,
    )
    return sim.run(duration_s)


def test_completed_legs_reflect_real_flight():
    """완료 구간의 경로 효율이 1.0 근방이어야 한다(이륙 직후 조기완료 금지).

    버그 상태에서는 가짜 완료(actual≈60m)가 섞여 평균이 0.9 미만으로 떨어진다.
    """
    result = _run()
    assert result.completed_legs >= 5, (
        f"충분한 완료 구간이 필요(got {result.completed_legs})"
    )
    # 핵심 회귀 단언: 평균 경로 효율이 합리적 범위(이륙 조기완료 시 ≈0.01~0.67로 하락)
    assert 0.9 <= result.route_efficiency_mean <= 1.6, (
        f"route_efficiency_mean 비정상: {result.route_efficiency_mean:.4f} "
        "(이륙 직후 leg 조기완료 회귀 의심)"
    )
    # 단일 구간이 비정상적으로 부풀지 않아야 함
    assert result.route_efficiency_max <= 2.0, (
        f"route_efficiency_max 비정상: {result.route_efficiency_max:.4f}"
    )


def test_no_instant_takeoff_completion():
    """어떤 완료 구간도 '수직 상승분(≈60m)만 비행' 상태로 완료되지 않아야 한다.

    record_completed_leg를 후킹하여 actual/planned 비율을 직접 검사한다.
    버그 상태: 다수 구간이 actual≈60m, planned≈수천 m → ratio≈0.01.
    """
    import simulation.analytics as analytics_mod

    captured: list[tuple[float, float]] = []
    original = analytics_mod.SimulationAnalytics.record_completed_leg

    def _spy(self, drone_id, actual_m, planned_m):  # noqa: ANN001
        captured.append((actual_m, planned_m))
        return original(self, drone_id, actual_m, planned_m)

    analytics_mod.SimulationAnalytics.record_completed_leg = _spy
    try:
        _run()
    finally:
        analytics_mod.SimulationAnalytics.record_completed_leg = original

    meaningful = [(a, p) for a, p in captured if p > 10.0 and a > 0.0]
    assert meaningful, "완료 구간이 기록되지 않음"
    # 이륙 직후 조기완료(actual이 planned의 5% 미만)는 없어야 한다
    instant = [(a, p) for a, p in meaningful if a < 0.05 * p]
    assert not instant, (
        f"이륙 직후 조기완료 구간 {len(instant)}건 발견 "
        f"(예: actual={instant[0][0]:.1f}m, planned={instant[0][1]:.1f}m)"
    )
