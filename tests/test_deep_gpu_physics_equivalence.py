"""심화: GPU 물리엔진(GPUPhysicsEngine) 검증 — numpy APF와의 동치성.

샌드박스/CI에 GPU가 없어도 PyTorch만 있으면 GPUPhysicsEngine은 CPU 텐서로
동작한다(_select_device가 CPU 폴백). 본 테스트는 GPU 엔진의 텐서 연산 경로가
레퍼런스 numpy APF(batch_compute_forces)와 동일한 물리력을 산출하는지 검증한다.

torch 미설치 환경에서는 전체 스킵한다.
"""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")  # torch 없으면 모듈 전체 스킵

from simulation.apf_engine.apf import (  # noqa: E402
    APF_PARAMS,
    APFState,
    batch_compute_forces,
)
from simulation.apf_engine.gpu_physics import GPUPhysicsEngine  # noqa: E402
from src.airspace_control.agents.drone_state import DroneState, FlightPhase  # noqa: E402

pytestmark = pytest.mark.unit

CPU = torch.device("cpu")


def _make_drones(n: int, spread: float, seed: int) -> dict[str, DroneState]:
    rng = np.random.default_rng(seed)
    ds: dict[str, DroneState] = {}
    for i in range(n):
        d = DroneState(
            drone_id=f"D{i:03d}",
            position=rng.uniform(-spread, spread, 3).astype(float),
            velocity=rng.uniform(-2, 2, 3).astype(float),
            profile_name="COMMERCIAL_DELIVERY",
            flight_phase=FlightPhase.EVADING,
            battery_pct=80.0,
        )
        d.position[2] = 60.0
        d.goal = rng.uniform(-spread, spread, 3).astype(float)
        d.goal[2] = 60.0
        ds[d.drone_id] = d
    return ds


def _gpu_forces(ds):
    eng = GPUPhysicsEngine(max_drones=max(64, len(ds)), device=CPU)
    eng.sync_from_cpu(ds)
    return eng.compute_all_forces(
        wind_speeds={k: 0.0 for k in ds}, nfz_obstacles=[], params=APF_PARAMS
    )


def _numpy_forces(ds):
    states = [
        APFState(position=d.position.copy(), velocity=d.velocity.copy(), drone_id=d.drone_id)
        for d in ds.values()
    ]
    goals = {d.drone_id: d.goal.copy() for d in ds.values()}
    return batch_compute_forces(
        states, goals, [], params=APF_PARAMS,
        wind_speeds={k: 0.0 for k in ds}, neighbor_states=states,
    )


@pytest.mark.parametrize("n,spread,seed", [(1, 2000, 0), (20, 2000, 1), (60, 800, 2), (120, 1000, 3)])
def test_gpu_matches_numpy_apf(n, spread, seed):
    """GPU 엔진 힘 벡터가 numpy APF와 일치(fp32 오차 한도 내)해야 한다."""
    ds = _make_drones(n, spread, seed)
    gpu_f = _gpu_forces(ds)
    np_f = _numpy_forces(ds)
    assert set(gpu_f) == set(np_f)
    max_delta = 0.0
    for k in ds:
        g = np.asarray(gpu_f[k], dtype=float)
        p = np.asarray(np_f[k], dtype=float)
        max_delta = max(max_delta, float(np.linalg.norm(g - p)))
    assert max_delta < 0.05, f"GPU vs numpy 최대 힘 편차 {max_delta:.4f} 과다 (n={n})"


def test_gpu_forces_bounded_by_max_force():
    """모든 힘은 유한하고 max_force 한도 내여야 한다."""
    ds = _make_drones(80, 600.0, seed=5)
    gpu_f = _gpu_forces(ds)
    for k, f in gpu_f.items():
        f = np.asarray(f, dtype=float)
        assert np.all(np.isfinite(f)), f"{k}: 비유한 힘"
        assert np.linalg.norm(f) <= APF_PARAMS["max_force"] + 1e-3, f"{k}: 힘 한도 초과"


def test_gpu_isolated_drone_attracts_to_goal():
    """이웃이 없는 단일 드론의 힘은 목표 방향을 향해야 한다(인력)."""
    d = DroneState(
        drone_id="solo",
        position=np.array([0.0, 0.0, 60.0]),
        velocity=np.zeros(3),
        profile_name="COMMERCIAL_DELIVERY",
        flight_phase=FlightPhase.EVADING,
        battery_pct=90.0,
    )
    d.goal = np.array([1000.0, 0.0, 60.0])
    gpu_f = _gpu_forces({"solo": d})
    f = np.asarray(gpu_f["solo"], dtype=float)
    # 목표는 +x 방향 → 힘의 x성분이 지배적으로 양(+)이어야 한다
    assert f[0] > 0.0
    assert abs(f[0]) > abs(f[1]) and abs(f[0]) > abs(f[2])


def test_gpu_engine_runs_without_cuda():
    """CUDA 없이도 CPU 디바이스로 엔진이 초기화·동작해야 한다."""
    eng = GPUPhysicsEngine(max_drones=16, device=CPU)
    assert eng.device.type == "cpu"
    assert eng._use_cuda is False
