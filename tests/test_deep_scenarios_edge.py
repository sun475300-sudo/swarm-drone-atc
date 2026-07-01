"""심화: 10개 시나리오 전수 실행 + 엣지케이스(고장/바람/통신두절/단일드론/로그).

수정 사항이 모든 공식 시나리오와 극단 설정에서 크래시 없이 동작하고
메트릭이 정의역 내에 있는지 검증한다.
"""
from __future__ import annotations

import pytest

from simulation.scenario_runner import list_scenarios, run_scenario
from simulation.simulator import SwarmSimulator

pytestmark = pytest.mark.e2e

SCENARIOS = list_scenarios()


def _assert_metrics_sane(row: dict, ctx: str):
    assert "error" not in row, f"{ctx}: 예외 발생 — {row.get('error')}"
    assert row["collision_count"] >= 0, f"{ctx}: 음수 충돌"
    assert row["conflicts_total"] >= 0, f"{ctx}: 음수 충돌예측"
    assert 0.0 <= row["conflict_resolution_rate_pct"] <= 100.0, f"{ctx}: 해결률 범위 이탈"
    assert row["advisory_latency_p50"] >= 0.0
    assert row["advisory_latency_p99"] >= row["advisory_latency_p50"]
    assert row["route_efficiency_mean"] >= 0.0
    if row["completed_legs"] > 0:
        assert 0.8 <= row["route_efficiency_mean"] <= 2.0, (
            f"{ctx}: eff={row['route_efficiency_mean']:.3f}"
        )


def test_scenario_set_has_ten():
    assert len(SCENARIOS) == 10, f"시나리오 수: {len(SCENARIOS)}"


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_each_scenario_runs_and_metrics_sane(scenario):
    """각 시나리오가 크래시 없이 실행되고 메트릭이 정의역 내."""
    rows = run_scenario(scenario, n_runs=1, seed=42, verbose=False, duration_override_s=45.0)
    assert len(rows) == 1
    _assert_metrics_sane(rows[0], scenario)


def test_single_drone_no_collision():
    """드론 1기 → 충돌 0, 정상 종료."""
    sim = SwarmSimulator(scenario_cfg={"drones": {"default_count": 1}}, seed=42)
    r = sim.run(120.0)
    assert r.collision_count == 0
    assert r.n_drones == 1
    assert r.conflict_resolution_rate_pct == 100.0


def test_failure_injection_runs():
    """고장 주입 활성화 시 크래시 없이 동작하고 메트릭 정상."""
    cfg = {
        "drones": {"default_count": 25},
        "failure_injection": {"drone_failure_rate": 0.8, "comms_loss_rate": 0.0},
    }
    r = sim_result(cfg)
    assert r.collision_count >= 0
    assert 0.0 <= r.conflict_resolution_rate_pct <= 100.0


def test_comms_loss_runs():
    """통신두절 주입 활성화 시 정상 동작."""
    cfg = {
        "drones": {"default_count": 25},
        "failure_injection": {"drone_failure_rate": 0.0, "comms_loss_rate": 0.8},
    }
    r = sim_result(cfg)
    assert r.collision_count >= 0


def test_wind_enabled_runs():
    """강풍 weather 모델 활성화 시 정상 동작 + 경로효율 정의역."""
    cfg = {
        "drones": {"default_count": 20},
        "weather": {"wind_models": [
            {"type": "uniform", "velocity": [12.0, 0.0, 0.0]},
        ]},
    }
    r = sim_result(cfg)
    assert r.collision_count >= 0
    assert r.route_efficiency_mean >= 0.0


def test_rogue_drones_run():
    """로그(미등록) 드론 포함 시 정상 동작."""
    cfg = {"drones": {"default_count": 20}, "scenario": {"drones": {"n_rogue": 4}}}
    r = sim_result(cfg)
    assert r.n_drones == 20
    assert r.collision_count >= 0


def sim_result(cfg, seed: int = 42, dur: float = 50.0):
    return SwarmSimulator(scenario_cfg=cfg, seed=seed).run(dur)
