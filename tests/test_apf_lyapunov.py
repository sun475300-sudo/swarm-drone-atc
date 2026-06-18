"""ODYSSEY Phase 443 — APF Lyapunov 수렴성 검증 테스트.

``simulation/apf_lyapunov.py`` 의 핵심 주장을 핀으로 고정한다:

  G1. 포텐셜의 음의 기울기가 실제 APF 엔진 힘과 일치 (gradient consistency).
  G2. 인력 포텐셜이 Lyapunov 조건(양정치·C¹·radially unbounded)을 만족.
  G3. 척력 포텐셜이 FIRAS 성질(≥0, d≥d0 에서 0, d→0 에서 발산)을 만족.
  G4. 과감쇠 흐름 dU/dt ≤ 0, 장애물 없으면 목표로 단조 수렴.
  G5. 장애물이 있어도 U 는 단조 비증가 (임계점 수렴).
"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.apf_engine.apf import (
    APF_PARAMS,
    attractive_force,
    repulsive_force_drone,
    repulsive_force_obstacle,
)
from simulation.apf_lyapunov import (
    ATTRACTIVE_TRANSITION_M,
    attractive_potential,
    conservative_force,
    lyapunov_derivative,
    repulsive_potential_drone,
    repulsive_potential_obstacle,
    total_potential,
)


def _numerical_gradient(fn, x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """중심 차분으로 ∇fn(x) 근사."""
    grad = np.zeros(3)
    for i in range(3):
        xp = x.copy()
        xm = x.copy()
        xp[i] += eps
        xm[i] -= eps
        grad[i] = (fn(xp) - fn(xm)) / (2.0 * eps)
    return grad


# ─────────────────────────── G1. 기울기 일치 (핵심) ───────────────────────────

def test_attractive_force_is_negative_gradient_quadratic_region():
    # Arrange — 전환점 안쪽 (r ≤ d_t)
    goal = np.array([100.0, 200.0, 60.0])
    pos = np.array([95.0, 197.0, 60.0])  # r ≈ 5.8 < 10
    # Act
    num_grad = _numerical_gradient(lambda x: attractive_potential(x, goal), pos)
    engine_force = attractive_force(pos, goal)
    # Assert — F_att = -∇V_att
    assert np.allclose(-num_grad, engine_force, atol=1e-3)


def test_attractive_force_is_negative_gradient_conic_region():
    # Arrange — 전환점 바깥 (r > d_t)
    goal = np.array([1000.0, 0.0, 60.0])
    pos = np.array([100.0, 50.0, 60.0])  # r ≫ 10
    # Act
    num_grad = _numerical_gradient(lambda x: attractive_potential(x, goal), pos)
    engine_force = attractive_force(pos, goal)
    # Assert
    assert np.allclose(-num_grad, engine_force, atol=1e-3)


def test_drone_repulsion_is_negative_gradient_of_potential():
    # Arrange — 속도 0 → apf 의 보존(속도-무관) 성분만
    own = np.array([0.0, 0.0, 60.0])
    other = np.array([20.0, 10.0, 60.0])  # dist ≈ 22.4 < d0=50
    zero = np.zeros(3)
    # Act
    num_grad = _numerical_gradient(lambda x: repulsive_potential_drone(x, other), own)
    engine_force = repulsive_force_drone(own, other, zero, zero)
    # Assert
    assert np.allclose(-num_grad, engine_force, atol=1e-3)


def test_obstacle_repulsion_is_negative_gradient_of_potential():
    # Arrange
    pos = np.array([0.0, 0.0, 60.0])
    obs = np.array([12.0, 5.0, 60.0])  # dist ≈ 13 < d0=30
    # Act
    num_grad = _numerical_gradient(lambda x: repulsive_potential_obstacle(x, obs), pos)
    engine_force = repulsive_force_obstacle(pos, obs)
    # Assert
    assert np.allclose(-num_grad, engine_force, atol=1e-3)


def test_conservative_force_matches_engine_attractive_deadband():
    # apf.attractive_force 는 r<0.1m 에서 0 — conservative_force 도 동일해야 한다.
    goal = np.array([100.0, 100.0, 60.0])
    inside = goal + np.array([0.05, 0.0, 0.0])  # r = 0.05 < 0.1
    assert np.allclose(conservative_force(inside, goal), attractive_force(inside, goal))
    assert np.allclose(conservative_force(inside, goal), np.zeros(3))
    # 데드밴드 바로 바깥은 엔진과 일치(비영).
    outside = goal + np.array([0.2, 0.0, 0.0])  # r = 0.2 > 0.1
    assert np.allclose(conservative_force(outside, goal), attractive_force(outside, goal))
    assert np.linalg.norm(conservative_force(outside, goal)) > 0.0


def test_transition_constant_matches_engine_continuity():
    # ATTRACTIVE_TRANSITION_M 이 엔진의 실제 전환점과 일치하는지 경험적으로 핀 고정:
    # 전환점에서 힘 크기가 연속(이차 k·r → 원뿔 k·d_t)이어야 한다.
    goal = np.zeros(3)
    d_t = ATTRACTIVE_TRANSITION_M
    just_inside = float(np.linalg.norm(attractive_force(np.array([d_t - 1e-4, 0, 0]), goal)))
    just_outside = float(np.linalg.norm(attractive_force(np.array([d_t + 1e-4, 0, 0]), goal)))
    assert just_inside == pytest.approx(just_outside, abs=1e-2)


def test_conservative_force_equals_negative_gradient_of_total_potential():
    # Arrange — 인력 + 척력 합성장
    goal = np.array([300.0, 100.0, 60.0])
    pos = np.array([50.0, 40.0, 60.0])
    neighbors = [np.array([70.0, 55.0, 60.0])]      # dist < d0_drone
    obstacles = [np.array([60.0, 50.0, 60.0])]      # dist < d0_obs
    # Act
    num_grad = _numerical_gradient(
        lambda x: total_potential(x, goal, neighbors, obstacles), pos
    )
    force = conservative_force(pos, goal, neighbors, obstacles)
    # Assert — F = -∇U
    assert np.allclose(-num_grad, force, atol=1e-2)


# ─────────────────────────── G2. 인력 Lyapunov 조건 ───────────────────────────

def test_attractive_potential_positive_definite():
    goal = np.array([10.0, 20.0, 30.0])
    assert attractive_potential(goal, goal) == 0.0
    for offset in ([1, 0, 0], [0, 50, 0], [100, 100, 100]):
        pos = goal + np.array(offset, dtype=float)
        assert attractive_potential(pos, goal) > 0.0


def test_attractive_potential_continuous_at_transition():
    # C⁰: 전환점 양쪽 극한값 일치
    goal = np.zeros(3)
    d_t = ATTRACTIVE_TRANSITION_M
    inside = attractive_potential(np.array([d_t - 1e-6, 0, 0]), goal)
    outside = attractive_potential(np.array([d_t + 1e-6, 0, 0]), goal)
    assert inside == pytest.approx(outside, abs=1e-3)
    # 전환점 값 = (k/2) d_t²
    assert attractive_potential(np.array([d_t, 0, 0]), goal) == pytest.approx(
        0.5 * APF_PARAMS["k_att"] * d_t * d_t
    )


def test_attractive_potential_radially_unbounded():
    goal = np.zeros(3)
    prev = -1.0
    for r in (50.0, 500.0, 5000.0):
        v = attractive_potential(np.array([r, 0, 0]), goal)
        assert v > prev  # 단조 증가 → r→∞ 에서 발산
        prev = v


# ─────────────────────────── G3. 척력 FIRAS 성질 ───────────────────────────

def test_repulsive_potential_zero_beyond_cutoff():
    pos = np.zeros(3)
    far = np.array([APF_PARAMS["d0_drone"] + 1.0, 0, 0])
    assert repulsive_potential_drone(pos, far) == 0.0
    at_cutoff = np.array([APF_PARAMS["d0_drone"], 0, 0])
    assert repulsive_potential_drone(pos, at_cutoff) == 0.0


def test_repulsive_potential_monotone_increasing_as_distance_shrinks():
    pos = np.zeros(3)
    d0 = APF_PARAMS["d0_drone"]
    vals = [repulsive_potential_drone(pos, np.array([d, 0, 0])) for d in (40.0, 20.0, 5.0, 1.0)]
    assert vals == sorted(vals)  # 가까울수록 포텐셜 ↑


def test_repulsive_potential_nonnegative():
    pos = np.zeros(3)
    for d in (1.0, 5.0, 25.0, 49.0):
        assert repulsive_potential_drone(pos, np.array([d, 0, 0])) >= 0.0


# ─────────────────────────── G4·G5. Lyapunov 하강·수렴 ───────────────────────────

def test_lyapunov_derivative_nonpositive_along_conservative_flow():
    # 과감쇠 흐름 ẋ = F_보존 → dU/dt = -‖∇U‖² ≤ 0
    goal = np.array([400.0, 0.0, 60.0])
    pos = np.array([0.0, 30.0, 60.0])
    obstacles = [np.array([150.0, 10.0, 60.0])]
    velocity = conservative_force(pos, goal, None, obstacles)
    rate = lyapunov_derivative(pos, goal, velocity, None, obstacles)
    assert rate <= 1e-9


def test_obstacle_free_descent_converges_to_goal():
    # 장애물 없는 과감쇠 경사하강 → 목표로 단조 수렴
    goal = np.array([300.0, 0.0, 60.0])
    pos = np.array([0.0, 0.0, 60.0])
    dt = 0.05
    prev_u = total_potential(pos, goal)
    for _ in range(5000):
        f = conservative_force(pos, goal)
        pos = pos + dt * f
        u = total_potential(pos, goal)
        assert u <= prev_u + 1e-6  # 단조 비증가
        prev_u = u
    assert np.linalg.norm(goal - pos) < 1.0  # 목표 도달


def test_potential_monotone_nonincreasing_with_obstacle():
    # 장애물이 있어도 U 는 단조 비증가 (임계점 수렴 보장)
    goal = np.array([300.0, 0.0, 60.0])
    pos = np.array([0.0, 5.0, 60.0])
    obstacles = [np.array([150.0, 0.0, 60.0])]
    dt = 0.02
    prev_u = total_potential(pos, goal, None, obstacles)
    for _ in range(3000):
        f = conservative_force(pos, goal, None, obstacles)
        pos = pos + dt * f
        u = total_potential(pos, goal, None, obstacles)
        assert u <= prev_u + 1e-6
        prev_u = u
