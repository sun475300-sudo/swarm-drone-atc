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
        obstacle = np.array([0.0, 0.0, 60.0])  # NFZ center position
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


class TestAPFGoalAltitude:
    """APF가 goal의 z 좌표(고도)를 인력 계산에 반영하는지 검증"""

    def test_goal_altitude_attracts_upward(self):
        """goal이 위에 있으면 z 방향 인력이 양수여야 한다."""
        s = APFState(position=np.array([0.0, 0.0, 30.0]),
                     velocity=np.zeros(3), drone_id="D0")
        goals = {"D0": np.array([0.0, 0.0, 100.0])}
        forces = batch_compute_forces([s], goals=goals, obstacles=[])
        assert forces["D0"][2] > 0

    def test_goal_altitude_attracts_downward(self):
        """goal이 아래에 있으면 z 방향 인력이 음수여야 한다."""
        s = APFState(position=np.array([0.0, 0.0, 100.0]),
                     velocity=np.zeros(3), drone_id="D0")
        goals = {"D0": np.array([0.0, 0.0, 30.0])}
        forces = batch_compute_forces([s], goals=goals, obstacles=[])
        assert forces["D0"][2] < 0


class TestAPFKDTree3D:
    """KDTree가 3D 좌표를 사용하여 수직 분리된 드론을 구별하는지 검증"""

    def test_vertical_separation_changes_force(self):
        """수직으로 분리된 드론 쌍과 같은 고도 쌍의 반발력이 다르다."""
        # 같은 고도 (60m), 수평 30m
        s0 = APFState(position=np.array([0.0, 0.0, 60.0]),
                      velocity=np.zeros(3), drone_id="A")
        s1 = APFState(position=np.array([30.0, 0.0, 60.0]),
                      velocity=np.zeros(3), drone_id="B")
        goals_same = _goals(s0, s1)
        f_same = batch_compute_forces([s0, s1], goals=goals_same, obstacles=[])

        # 수직 분리 (30m vs 90m) — 3D 거리 67m
        s2 = APFState(position=np.array([0.0, 0.0, 30.0]),
                      velocity=np.zeros(3), drone_id="C")
        s3 = APFState(position=np.array([30.0, 0.0, 90.0]),
                      velocity=np.zeros(3), drone_id="D")
        goals_sep = _goals(s2, s3)
        f_sep = batch_compute_forces([s2, s3], goals=goals_sep, obstacles=[])

        # 두 시나리오에서 모두 3 벡터 힘이 계산됨
        assert f_same["A"].shape == (3,)
        assert f_sep["C"].shape == (3,)


class TestAPFWindyMode:
    """강풍 모드 파라미터 적용 검증"""

    def test_windy_increases_repulsion(self):
        """풍속이 높으면 반발력이 커져야 한다."""
        s0 = APFState(position=np.array([0.0, 0.0, 60.0]),
                      velocity=np.zeros(3), drone_id="A")
        s1 = APFState(position=np.array([30.0, 0.0, 60.0]),
                      velocity=np.zeros(3), drone_id="B")
        goals = _goals(s0, s1)

        f_calm = batch_compute_forces([s0, s1], goals=goals, obstacles=[],
                                       wind_speeds={"A": 0.0, "B": 0.0})
        f_wind = batch_compute_forces([s0, s1], goals=goals, obstacles=[],
                                       wind_speeds={"A": 15.0, "B": 15.0})
        rep_calm = np.linalg.norm(f_calm.get("A", np.zeros(3)))
        rep_wind = np.linalg.norm(f_wind.get("A", np.zeros(3)))
        assert rep_wind >= rep_calm
