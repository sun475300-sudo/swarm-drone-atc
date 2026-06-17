"""어드바이저리 지연(advisory_latency) 측정 회귀 테스트.

버그: SimulationAnalytics.record_advisory_latency가 정의만 되어 있고 어디서도
호출되지 않아 advisory_latency_p50/p99가 항상 0.0으로 보고되었다.

수정 후에는 드론이 ResolutionAdvisory를 수신할 때 종단 전달 지연
(env.now - msg.sent_time)이 기록되어, 어드바이저리가 실제로 발부된 런에서는
지연 분위수가 0보다 커야 한다(통신 버스 지연 모델 반영).
"""
from __future__ import annotations

import pytest

from simulation.simulator import SwarmSimulator

pytestmark = pytest.mark.e2e


def test_advisory_latency_recorded_when_advisories_issued():
    """어드바이저리가 발부되면 지연 분위수가 0보다 커야 한다."""
    sim = SwarmSimulator(scenario_cfg={"drones": {"default_count": 30}}, seed=42)
    result = sim.run(120.0)

    # 밀도가 충분하면 어드바이저리가 발부된다(전제 검증).
    assert result.advisories_issued > 0, (
        f"테스트 전제: 어드바이저리가 발부되어야 함(got {result.advisories_issued})"
    )
    # 핵심 회귀 단언: 지연이 실제로 측정되어야 한다(버그 상태에서는 0.0 고정).
    assert result.advisory_latency_p99 > 0.0, (
        "advisory_latency_p99가 0 — 지연 측정 미배선 회귀 의심"
    )
    assert result.advisory_latency_p50 >= 0.0
    # 통신 지연 모델(평균 20ms) 기준, 비정상적으로 큰 값이 아니어야 함.
    assert result.advisory_latency_p99 < 5.0, (
        f"advisory_latency_p99 비정상적으로 큼: {result.advisory_latency_p99:.3f}s"
    )
