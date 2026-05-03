"""APF property-based 회귀 테스트 (Hypothesis).

A1-05 항목 (AUDIT C-07). 기존 example-based 테스트(`test_apf.py`) 를 보완해서
random 입력에 대해 다음 불변성을 검증:

1. 모든 force 결과는 finite (NaN/Inf 없음).
2. attractive_force 는 항상 goal 방향 (cos angle > 0) — 안정적 수렴.
3. repulsive_force_drone 은 cutoff(d0) 이상에서 정확히 0.
4. repulsive_force_drone 은 거리 단조성 — 같은 방향에서 거리 ↑ → 크기 ↓
   (cutoff 안쪽 + closing speed=0 가정).
5. repulsive_force_obstacle 도 같은 cutoff/단조성 보장.
6. compute_total_force 는 max_force 이내로 클램프.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from simulation.apf_engine.apf import (
    APF_PARAMS,
    APFState,
    attractive_force,
    compute_total_force,
    repulsive_force_drone,
    repulsive_force_obstacle,
)


# 시뮬 공역 ±5km, 고도 0~150m 범위
_coord = st.floats(min_value=-5000.0, max_value=5000.0, allow_nan=False, allow_infinity=False)
_alt = st.floats(min_value=0.0, max_value=150.0, allow_nan=False, allow_infinity=False)


def _vec(coord, alt):
    return st.tuples(coord, coord, alt).map(lambda t: np.array(t, dtype=float))


@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(pos=_vec(_coord, _alt), goal=_vec(_coord, _alt))
def test_attractive_force_is_finite(pos, goal):
    f = attractive_force(pos, goal)
    assert np.all(np.isfinite(f))


@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(pos=_vec(_coord, _alt), goal=_vec(_coord, _alt))
def test_attractive_force_points_toward_goal(pos, goal):
    """드론에서 목표까지 방향과 인력 방향이 정렬 (cos ≥ 0)."""
    diff = goal - pos
    dist = float(np.linalg.norm(diff))
    if dist < 0.1:
        return  # epsilon 영역은 0 반환됨 — 검증 의미 없음
    f = attractive_force(pos, goal)
    fmag = float(np.linalg.norm(f))
    if fmag < 1e-9:
        return
    cos_angle = float(np.dot(diff, f) / (dist * fmag))
    # 부동소수 오차 여유.
    assert cos_angle > 0.999, f"attractive force misaligned: cos={cos_angle}"


@settings(max_examples=80, deadline=None)
@given(
    distance=st.floats(min_value=APF_PARAMS["d0_drone"] + 0.1,
                        max_value=APF_PARAMS["d0_drone"] * 5.0,
                        allow_nan=False),
)
def test_drone_repulsion_is_zero_outside_cutoff(distance):
    """d0 거리를 넘으면 정확히 0 벡터."""
    own = np.array([0.0, 0.0, 50.0])
    other = np.array([distance, 0.0, 50.0])
    zero_vel = np.zeros(3)
    f = repulsive_force_drone(own, other, zero_vel, zero_vel)
    assert np.allclose(f, 0.0)


@settings(max_examples=60, deadline=None)
@given(
    d_close=st.floats(min_value=2.0, max_value=APF_PARAMS["d0_drone"] / 2 - 0.1, allow_nan=False),
    delta=st.floats(min_value=2.0, max_value=APF_PARAMS["d0_drone"] / 2 - 0.1, allow_nan=False),
)
def test_drone_repulsion_monotonic_in_distance(d_close, delta):
    """동일 방향에서 가까운 거리(d_close) 의 척력이 더 먼 거리(d_far) 보다 크다.

    closing speed = 0 (정지) 가정으로 단조성만 검증.
    """
    d_far = d_close + delta
    own = np.array([0.0, 0.0, 50.0])
    near = np.array([d_close, 0.0, 50.0])
    far = np.array([d_far, 0.0, 50.0])
    zero_vel = np.zeros(3)
    f_near = repulsive_force_drone(own, near, zero_vel, zero_vel)
    f_far = repulsive_force_drone(own, far, zero_vel, zero_vel)
    assert float(np.linalg.norm(f_near)) >= float(np.linalg.norm(f_far)), (
        f"non-monotonic: near={d_close} |f|={np.linalg.norm(f_near)}, "
        f"far={d_far} |f|={np.linalg.norm(f_far)}"
    )


@settings(max_examples=80, deadline=None)
@given(
    distance=st.floats(min_value=APF_PARAMS["d0_obs"] + 0.1,
                        max_value=APF_PARAMS["d0_obs"] * 5.0,
                        allow_nan=False),
)
def test_obstacle_repulsion_is_zero_outside_cutoff(distance):
    pos = np.array([0.0, 0.0, 50.0])
    obs = np.array([distance, 0.0, 50.0])
    f = repulsive_force_obstacle(pos, obs)
    assert np.allclose(f, 0.0)


@settings(max_examples=60, deadline=None)
@given(
    d_close=st.floats(min_value=1.0, max_value=APF_PARAMS["d0_obs"] / 2 - 0.1, allow_nan=False),
    delta=st.floats(min_value=1.0, max_value=APF_PARAMS["d0_obs"] / 2 - 0.1, allow_nan=False),
)
def test_obstacle_repulsion_monotonic_in_distance(d_close, delta):
    d_far = d_close + delta
    pos = np.array([0.0, 0.0, 50.0])
    obs_near = np.array([d_close, 0.0, 50.0])
    obs_far = np.array([d_far, 0.0, 50.0])
    f_near = repulsive_force_obstacle(pos, obs_near)
    f_far = repulsive_force_obstacle(pos, obs_far)
    assert float(np.linalg.norm(f_near)) >= float(np.linalg.norm(f_far))


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    pos=_vec(_coord, _alt),
    goal=_vec(_coord, _alt),
    n_others=st.integers(min_value=0, max_value=10),
)
def test_total_force_is_finite_and_bounded(pos, goal, n_others):
    """compute_total_force 결과는 finite + 어떤 PARAMS 의 max_force 이내.

    런타임 모드(normal/windy/high_density) 에 따라 max_force 가 자동 전환되므로
    가장 큰 임계 (HIGH_DENSITY=50.0) 를 상한으로 검증.
    """
    from simulation.apf_engine.apf import APF_PARAMS_HIGH_DENSITY

    rng = np.random.default_rng(seed=42)
    others = []
    for _ in range(n_others):
        op = pos + rng.uniform(-200.0, 200.0, size=3)
        op[2] = max(0.0, min(150.0, float(op[2])))
        others.append(APFState(position=op, velocity=np.zeros(3), drone_id=f"o{_}"))
    own = APFState(position=pos, velocity=np.zeros(3), drone_id="own")
    f = compute_total_force(own, goal, others, obstacles=[])
    assert np.all(np.isfinite(f))
    fmag = float(np.linalg.norm(f))
    upper = APF_PARAMS_HIGH_DENSITY["max_force"]
    assert fmag <= upper + 1e-6, f"force exceeds upper bound {upper}: |f|={fmag}"
