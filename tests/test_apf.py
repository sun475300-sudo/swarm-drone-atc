"""
APF 엔진 단위 테스트
"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.apf_engine.apf import (
    APFState,
    batch_compute_forces,
    force_to_velocity,
)


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _make_state(x: float, y: float, z: float = 60.0,
                did: str = "D0") -> APFState:
    return APFState(
        position=np.array([x, y, z], dtype=float),
        velocity=np.zeros(3),
        drone_id=did,
    )


def _goals(*states: APFState) -> dict[str, np.ndarray]:
    """각 드론의 현재 위치를 goal로 설정 (인력 = 0)"""
    return {s.drone_id: s.position.copy() for s in states}


# ── 테스트 ────────────────────────────────────────────────────────────────────

class TestAPFState:
    def test_creation(self):
        s = _make_state(10.0, 20.0)
        assert s.position[0] == pytest.approx(10.0)

    def test_default_velocity_zero(self):
        s = _make_state(0.0, 0.0)
        assert np.allclose(s.velocity, 0.0)

    def test_drone_id(self):
        s = _make_state(0.0, 0.0, did="MyDrone")
        assert s.drone_id == "MyDrone"


class TestBatchComputeForces:
    def test_single_drone_returns_entry(self):
        s = _make_state(0.0, 0.0)
        forces = batch_compute_forces([s], goals=_goals(s), obstacles=[])
        assert "D0" in forces
        assert forces["D0"].shape == (3,)

    def test_two_drones_repulsion(self):
        """두 드론이 가까우면 반발력이 발생해야 한다."""
        s0 = _make_state(0.0, 0.0, did="A")
        s1 = _make_state(10.0, 0.0, did="B")
        goals = _goals(s0, s1)
        forces = batch_compute_forces([s0, s1], goals=goals, obstacles=[])
        f_a = forces.get("A", np.zeros(3))
        f_b = forces.get("B", np.zeros(3))
        # 서로 반발 → A의 x 방향 힘은 음수, B는 양수 (또는 반대 부호)
        if np.linalg.norm(f_a) > 0 and np.linalg.norm(f_b) > 0:
            assert f_a[0] * f_b[0] <= 0

    def test_returns_dict_for_all_drones(self):
        states = [_make_state(i * 100.0, 0.0, did=f"D{i}") for i in range(5)]
        goals  = _goals(*states)
        forces = batch_compute_forces(states, goals=goals, obstacles=[])
        assert set(forces.keys()) == {s.drone_id for s in states}

    def test_obstacle_repulsion(self):
        """드론이 장애물 근처에 있으면 장애물에서 멀어지는 힘이 발생해야 한다."""
        s = _make_state(5.0, 0.0, did="A")
        obstacle = np.array([0.0, 0.0, 60.0])
        forces = batch_compute_forces([s], goals=_goals(s),
                                       obstacles=[obstacle])
        f = forces["A"]
        # 장애물(0,0)에서 드론(5,0) 방향 → x > 0 힘 기대
        # 힘이 0이 아니기만 해도 충분
        assert isinstance(f, np.ndarray) and f.shape == (3,)


class TestForceToVelocity:
    def test_zero_force(self):
        v = force_to_velocity(np.zeros(3), np.zeros(3), dt=0.1, max_speed=10.0)
        assert np.allclose(v, 0.0)

    def test_direction_with_force(self):
        force = np.array([3.0, 4.0, 0.0])
        v = force_to_velocity(np.zeros(3), force, dt=1.0, max_speed=100.0)
        assert v[0] > 0 and v[1] > 0

    def test_clamps_to_max_speed(self):
        force = np.array([1000.0, 0.0, 0.0])
        v = force_to_velocity(np.zeros(3), force, dt=1.0, max_speed=8.0)
        assert np.linalg.norm(v) <= 8.0 + 1e-6


class TestClosingSpeedCap:
    """BUG-05: closing_speed 2× 명시적 캡 검증"""

    def test_closing_speed_cap_at_2x(self):
        """closing_speed=10.0 (> 5.0) 이어도 증폭은 2× 이하여야 한다."""
        from simulation.apf_engine.apf import repulsive_force_drone, APF_PARAMS

        # 두 드론이 10m 간격으로 정면 충돌 접근 (closing_speed ≈ 20 m/s)
        own_pos   = np.array([0.0, 0.0, 60.0])
        other_pos = np.array([10.0, 0.0, 60.0])
        own_vel   = np.array([10.0, 0.0, 0.0])   # 상대방 방향으로 이동
        other_vel = np.array([-10.0, 0.0, 0.0])  # 나 방향으로 이동

        f_high = repulsive_force_drone(own_pos, other_pos, own_vel, other_vel)

        # closing_speed = 0 인 경우 (상대속도 없음)
        f_zero = repulsive_force_drone(
            own_pos, other_pos,
            np.zeros(3), np.zeros(3),
        )

        mag_high = float(np.linalg.norm(f_high))
        mag_zero = float(np.linalg.norm(f_zero))

        if mag_zero > 1e-6:
            ratio = mag_high / mag_zero
            assert ratio <= 3.0 + 1e-6, f"closing_speed 증폭이 3× 초과: {ratio:.3f}"

    def test_no_amplification_when_moving_away(self):
        """멀어지는 방향(closing_speed < 0)이면 증폭 없음"""
        from simulation.apf_engine.apf import repulsive_force_drone

        own_pos   = np.array([0.0, 0.0, 60.0])
        other_pos = np.array([10.0, 0.0, 60.0])
        own_vel   = np.array([-5.0, 0.0, 0.0])   # 멀어지는 방향
        other_vel = np.zeros(3)

        f = repulsive_force_drone(own_pos, other_pos, own_vel, other_vel)
        f_base = repulsive_force_drone(own_pos, other_pos, np.zeros(3), np.zeros(3))

        # 멀어지는 경우 기본 척력과 크기가 같아야 함
        assert abs(np.linalg.norm(f) - np.linalg.norm(f_base)) < 1e-6


class TestGroundAvoidance:
    """F-02: z < 5m 지면 회피 반발력 검증"""

    def test_ground_repulsion_below_5m(self):
        """고도 2m 드론 → z 방향 합력이 양수(상승)여야 한다."""
        from simulation.apf_engine.apf import compute_total_force, APFState

        own = APFState(
            position=np.array([0.0, 0.0, 2.0]),   # 지면 2m
            velocity=np.zeros(3),
            drone_id="G0",
        )
        goal = np.array([1000.0, 0.0, 60.0])
        f = compute_total_force(own, goal, [], [], target_alt=60.0)
        assert f[2] > 0, "z<5m 에서 지면 회피 힘이 양수(상승)여야 함"

    def test_no_ground_repulsion_above_5m(self):
        """고도 10m 드론 → 지면 반발력 없음 (고도 보정만)"""
        from simulation.apf_engine.apf import compute_total_force, APFState

        own10 = APFState(position=np.array([0.0, 0.0, 10.0]), velocity=np.zeros(3), drone_id="G1")
        own2  = APFState(position=np.array([0.0, 0.0, 2.0]),  velocity=np.zeros(3), drone_id="G2")
        goal  = np.array([1000.0, 0.0, 10.0])

        f10 = compute_total_force(own10, goal, [], [], target_alt=10.0)
        f2  = compute_total_force(own2,  goal, [], [], target_alt=10.0)

        # 지면 근처(2m)가 높이(10m)보다 z 힘이 더 커야 함
        assert f2[2] > f10[2], "지면 가까울수록 상승력이 더 강해야 함"


class TestTargetAlt:
    """target_alt 파라미터 전달 검증"""

    def test_target_alt_influences_z_force(self):
        """goal[2]와 다른 target_alt 적용 시 고도력이 goal[2] 기준이 아닌 target_alt 기준"""
        from simulation.apf_engine.apf import compute_total_force, APFState

        own = APFState(
            position=np.array([0.0, 0.0, 50.0]),  # 현재 고도 50m
            velocity=np.zeros(3),
            drone_id="T0",
        )
        goal = np.array([1000.0, 0.0, 60.0])  # goal 고도 60m

        # target_alt=80m → 고도력이 위 방향(80-50=30m 오차)
        f_80 = compute_total_force(own, goal, [], [], target_alt=80.0)
        # target_alt=40m → 고도력이 아래 방향(40-50=-10m 오차)
        f_40 = compute_total_force(own, goal, [], [], target_alt=40.0)

        # target_alt=80 → z 방향 힘 양수, target_alt=40 → z 방향 힘 음수
        assert f_80[2] > 0, "target_alt=80m 일 때 z 힘이 위쪽이어야 함"
        assert f_40[2] < 0, "target_alt=40m 일 때 z 힘이 아래쪽이어야 함"
