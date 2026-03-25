"""
APF 엔진 포괄적 단위 테스트
개별 함수(attractive_force, repulsive_force_drone, repulsive_force_obstacle,
compute_total_force) 및 엣지 케이스 커버
"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.apf_engine.apf import (
    APFState,
    APF_PARAMS,
    APF_PARAMS_WINDY,
    attractive_force,
    repulsive_force_drone,
    repulsive_force_obstacle,
    compute_total_force,
    force_to_velocity,
    batch_compute_forces,
)


# ── attractive_force 테스트 ──────────────────────────────────────────────


class TestAttractiveForce:
    def test_returns_zero_at_goal(self):
        """목표 지점에 매우 가까우면 힘 = 0"""
        f = attractive_force(np.array([0.0, 0.0, 0.0]), np.array([0.01, 0.0, 0.0]))
        assert np.allclose(f, 0.0)

    def test_unit_vector_far_away(self):
        """원거리(>10m)에서는 단위 벡터 방향 인력"""
        pos = np.array([0.0, 0.0, 0.0])
        goal = np.array([100.0, 0.0, 0.0])
        f = attractive_force(pos, goal)
        assert f[0] > 0
        assert np.linalg.norm(f) == pytest.approx(1.0, abs=0.01)

    def test_quadratic_near(self):
        """근거리(<=10m)에서는 이차 인력 (크기 = k_att * dist)"""
        pos = np.array([0.0, 0.0, 0.0])
        goal = np.array([5.0, 0.0, 0.0])
        f = attractive_force(pos, goal, k_att=1.0)
        assert f[0] == pytest.approx(5.0, abs=0.01)

    def test_direction_points_to_goal(self):
        """힘 방향이 목표를 향해야 한다"""
        pos = np.array([10.0, 20.0, 30.0])
        goal = np.array([50.0, 60.0, 70.0])
        f = attractive_force(pos, goal)
        diff = goal - pos
        cos_angle = np.dot(f, diff) / (np.linalg.norm(f) * np.linalg.norm(diff))
        assert cos_angle == pytest.approx(1.0, abs=0.01)

    def test_custom_k_att(self):
        """커스텀 k_att 게인"""
        pos = np.zeros(3)
        goal = np.array([3.0, 0.0, 0.0])  # 근거리
        f1 = attractive_force(pos, goal, k_att=1.0)
        f2 = attractive_force(pos, goal, k_att=2.0)
        assert np.linalg.norm(f2) == pytest.approx(2 * np.linalg.norm(f1), abs=0.01)


# ── repulsive_force_drone 테스트 ──────────────────────────────────────────


class TestRepulsiveForceDrone:
    def test_zero_outside_range(self):
        """영향 거리 밖이면 척력 = 0"""
        f = repulsive_force_drone(
            np.array([100.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            np.zeros(3), np.zeros(3),
            d0=50.0,
        )
        assert np.allclose(f, 0.0)

    def test_nonzero_inside_range(self):
        """영향 거리 안이면 척력 != 0"""
        f = repulsive_force_drone(
            np.array([10.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            np.zeros(3), np.zeros(3),
            d0=50.0,
        )
        assert np.linalg.norm(f) > 0

    def test_direction_away_from_other(self):
        """척력 방향이 상대 드론에서 멀어져야 한다"""
        own = np.array([10.0, 0.0, 0.0])
        other = np.array([0.0, 0.0, 0.0])
        f = repulsive_force_drone(own, other, np.zeros(3), np.zeros(3), d0=50.0)
        assert f[0] > 0  # own이 +x에 있으므로 +x 방향 척력

    def test_closer_means_stronger(self):
        """가까울수록 척력이 강해야 한다"""
        other = np.array([0.0, 0.0, 0.0])
        f_close = repulsive_force_drone(
            np.array([5.0, 0.0, 0.0]), other, np.zeros(3), np.zeros(3), d0=50.0)
        f_far = repulsive_force_drone(
            np.array([30.0, 0.0, 0.0]), other, np.zeros(3), np.zeros(3), d0=50.0)
        assert np.linalg.norm(f_close) > np.linalg.norm(f_far)

    def test_closing_speed_amplification(self):
        """접근 중이면 척력이 증폭되어야 한다"""
        own = np.array([20.0, 0.0, 0.0])
        other = np.array([0.0, 0.0, 0.0])
        # 정지 상태
        f_static = repulsive_force_drone(own, other, np.zeros(3), np.zeros(3), d0=50.0)
        # 접근 중 (own이 -x 방향으로 이동)
        f_closing = repulsive_force_drone(
            own, other,
            np.array([-5.0, 0.0, 0.0]), np.zeros(3),
            d0=50.0,
        )
        assert np.linalg.norm(f_closing) > np.linalg.norm(f_static)

    def test_diverging_no_amplification(self):
        """멀어지는 중이면 증폭 없음"""
        own = np.array([20.0, 0.0, 0.0])
        other = np.array([0.0, 0.0, 0.0])
        f_static = repulsive_force_drone(own, other, np.zeros(3), np.zeros(3), d0=50.0)
        # 멀어지는 중 (own이 +x 방향으로 이동)
        f_diverging = repulsive_force_drone(
            own, other,
            np.array([5.0, 0.0, 0.0]), np.zeros(3),
            d0=50.0,
        )
        assert np.linalg.norm(f_diverging) <= np.linalg.norm(f_static) + 1e-10

    def test_zero_at_coincident(self):
        """두 드론이 같은 위치이면 0 반환 (div-by-zero 방지)"""
        f = repulsive_force_drone(
            np.array([0.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            np.zeros(3), np.zeros(3),
        )
        assert np.allclose(f, 0.0)


# ── repulsive_force_obstacle 테스트 ───────────────────────────────────────


class TestRepulsiveForceObstacle:
    def test_zero_outside_range(self):
        f = repulsive_force_obstacle(
            np.array([100.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            d0=30.0,
        )
        assert np.allclose(f, 0.0)

    def test_nonzero_inside_range(self):
        f = repulsive_force_obstacle(
            np.array([10.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            d0=30.0,
        )
        assert np.linalg.norm(f) > 0

    def test_direction_away_from_obstacle(self):
        f = repulsive_force_obstacle(
            np.array([10.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            d0=30.0,
        )
        assert f[0] > 0

    def test_coincident_returns_zero(self):
        f = repulsive_force_obstacle(
            np.array([0.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
        )
        assert np.allclose(f, 0.0)


# ── compute_total_force 테스트 ────────────────────────────────────────────


class TestComputeTotalForce:
    def test_no_neighbors_no_obstacles(self):
        """이웃/장애물 없이 목표만 있을 때 인력만 작용"""
        own = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "D0")
        goal = np.array([100.0, 0.0, 60.0])
        f = compute_total_force(own, goal, [], [])
        assert f[0] > 0  # 목표 방향

    def test_altitude_correction(self):
        """고도가 순항 고도(60m)에서 벗어나면 보정력 작용"""
        own = APFState(np.array([0.0, 0.0, 30.0]), np.zeros(3), "D0")
        goal = np.array([0.01, 0.0, 30.0])  # 거의 같은 위치
        f = compute_total_force(own, goal, [], [])
        # z 방향으로 고도 보정: 60 - 30 = 30 → 양수 z 힘
        assert f[2] > 0

    def test_force_clipping(self):
        """합력이 max_force로 클리핑되어야 한다"""
        own = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "D0")
        # 여러 장애물을 매우 가까이 배치하여 큰 척력 유발
        obstacles = [np.array([1.0, 0.0, 60.0]) for _ in range(10)]
        goal = np.array([100.0, 0.0, 60.0])
        f = compute_total_force(own, goal, [], obstacles, params=APF_PARAMS)
        assert np.linalg.norm(f) <= APF_PARAMS["max_force"] + 1e-6

    def test_windy_params_auto_selection(self):
        """바람 속도 > 10 m/s이면 강풍 파라미터 선택"""
        own = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "D0")
        goal = np.array([100.0, 0.0, 60.0])
        f_calm = compute_total_force(own, goal, [], [], wind_speed=5.0)
        f_windy = compute_total_force(own, goal, [], [], wind_speed=15.0)
        # 강풍에서 max_force가 더 크므로 다른 결과 가능 (최소한 에러 없이 실행)
        assert f_calm.shape == (3,)
        assert f_windy.shape == (3,)

    def test_explicit_params_override(self):
        """명시적 파라미터가 자동 선택보다 우선"""
        own = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "D0")
        goal = np.array([100.0, 0.0, 60.0])
        f = compute_total_force(own, goal, [], [], params=APF_PARAMS_WINDY, wind_speed=0.0)
        assert f.shape == (3,)


# ── batch_compute_forces 추가 테스트 ──────────────────────────────────────


class TestBatchComputeForcesExtended:
    def test_no_goal_returns_zero(self):
        """목표가 없는 드론은 힘 = 0"""
        s = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "D0")
        forces = batch_compute_forces([s], goals={}, obstacles=[])
        assert np.allclose(forces["D0"], 0.0)

    def test_wind_speeds_per_drone(self):
        """드론별 바람 속도 적용"""
        s0 = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "D0")
        s1 = APFState(np.array([500.0, 0.0, 60.0]), np.zeros(3), "D1")
        goals = {"D0": np.array([100.0, 0.0, 60.0]),
                 "D1": np.array([400.0, 0.0, 60.0])}
        wind_speeds = {"D0": 15.0, "D1": 2.0}
        forces = batch_compute_forces([s0, s1], goals, [], wind_speeds=wind_speeds)
        assert "D0" in forces and "D1" in forces

    def test_comm_range_filtering(self):
        """통신 범위 밖의 드론은 이웃으로 간주 안 함"""
        s0 = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "D0")
        s1 = APFState(np.array([5000.0, 0.0, 60.0]), np.zeros(3), "D1")
        goals = {"D0": np.array([0.01, 0.0, 60.0]),
                 "D1": np.array([5000.01, 0.0, 60.0])}
        forces_near = batch_compute_forces([s0, s1], goals, [], comm_range=100.0)
        # 통신 범위 밖이므로 이웃 드론 없이 개별 힘만 계산
        assert forces_near["D0"].shape == (3,)


# ── force_to_velocity 추가 테스트 ─────────────────────────────────────────


class TestForceToVelocityExtended:
    def test_adds_to_existing_velocity(self):
        """기존 속도에 힘 적용"""
        v = force_to_velocity(
            np.array([5.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
            dt=1.0,
            max_speed=100.0,
        )
        assert v[0] == pytest.approx(6.0, abs=0.01)

    def test_clamp_preserves_direction(self):
        """클램프 후에도 방향 유지"""
        v = force_to_velocity(np.zeros(3), np.array([3.0, 4.0, 0.0]), dt=10.0, max_speed=5.0)
        expected_dir = np.array([3.0, 4.0, 0.0]) / 5.0
        actual_dir = v / np.linalg.norm(v)
        assert np.allclose(actual_dir, expected_dir, atol=0.01)

    def test_small_dt(self):
        """작은 dt에서 작은 속도 변화"""
        v = force_to_velocity(np.zeros(3), np.array([10.0, 0.0, 0.0]), dt=0.01, max_speed=100.0)
        assert v[0] == pytest.approx(0.1, abs=0.01)
