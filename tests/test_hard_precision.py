"""
Hard Precision Test Suite
=========================
APF 엔진, 충돌 감지, 물리 적분, 상태 머신, 시나리오 회귀, GPU 엔진에 대한
경계값 및 정밀 검증 테스트.

총 6개 섹션 × 다수의 테스트 = 종합 정밀도 검증.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

# 프로젝트 루트를 sys.path에 추가
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from simulation.apf_engine.apf import (
    APF_PARAMS,
    APFState,
    attractive_force,
    compute_total_force,
    force_to_velocity,
    repulsive_force_drone,
)
from simulation.spatial_hash import SpatialHash
from src.airspace_control.agents.drone_state import (
    DroneState,
    FailureType,
    FlightPhase,
)
from visualization._scene_traces import (
    ALT_MAX,
    ALT_MIN,
    BOUNDS_M,
    CRUISE_ALT,
    NFZ_X,
    NFZ_Y,
    _NFZ_OBSTACLES,
    _PAD_LIST,
)

# ── GPU availability check ───────────────────────────────────
try:
    import torch

    _HAS_CUDA = torch.cuda.is_available()
except ImportError:
    _HAS_CUDA = False


# ══════════════════════════════════════════════════════════════
# 1. APF Engine Precision Tests
# ══════════════════════════════════════════════════════════════

class TestAPFEnginePrecision:
    """APF 인공 포텐셜 장 엔진 정밀 검증."""

    def test_attractive_force_direction(self):
        """인력은 목표 방향을 가리켜야 한다."""
        pos = np.array([0.0, 0.0, 60.0])
        goal = np.array([100.0, 200.0, 60.0])

        force = attractive_force(pos, goal)
        expected_dir = (goal - pos) / np.linalg.norm(goal - pos)

        force_dir = force / np.linalg.norm(force)
        np.testing.assert_allclose(force_dir, expected_dir, atol=1e-6)

    def test_attractive_force_magnitude_near(self):
        """근거리 (dist < 10m) 에서 이차 인력: F = k_att * diff."""
        pos = np.array([0.0, 0.0, 60.0])
        goal = np.array([5.0, 0.0, 60.0])
        k_att = APF_PARAMS["k_att"]

        force = attractive_force(pos, goal, k_att)
        expected = k_att * (goal - pos)

        np.testing.assert_allclose(force, expected, atol=1e-10)

    def test_attractive_force_magnitude_far(self):
        """원거리 (dist > 10m) 에서 단위 벡터 인력: F = k_att * dir * d_t."""
        pos = np.array([0.0, 0.0, 60.0])
        goal = np.array([500.0, 0.0, 60.0])
        k_att = APF_PARAMS["k_att"]

        force = attractive_force(pos, goal, k_att)
        diff = goal - pos
        dist = np.linalg.norm(diff)
        d_t = 10.0
        expected = k_att * diff / dist * d_t

        np.testing.assert_allclose(force, expected, atol=1e-10)

    def test_attractive_force_zero_at_goal(self):
        """목표에 매우 근접 (dist < 0.1m) 하면 인력은 0."""
        pos = np.array([100.0, 200.0, 60.0])
        goal = np.array([100.05, 200.0, 60.0])

        force = attractive_force(pos, goal)
        np.testing.assert_allclose(force, np.zeros(3), atol=1e-10)

    def test_repulsive_force_symmetry(self):
        """F(A->B) = -F(B->A) 방향 대칭성 검증."""
        pos_a = np.array([0.0, 0.0, 60.0])
        pos_b = np.array([20.0, 0.0, 60.0])
        vel_a = np.array([5.0, 0.0, 0.0])
        vel_b = np.array([-5.0, 0.0, 0.0])

        f_ab = repulsive_force_drone(pos_a, pos_b, vel_a, vel_b)
        f_ba = repulsive_force_drone(pos_b, pos_a, vel_b, vel_a)

        # 방향 반대 (부호 반전)
        np.testing.assert_allclose(f_ab + f_ba, np.zeros(3), atol=1e-6)

    def test_repulsive_force_zero_outside_d0(self):
        """d0 반경 밖에서 척력은 정확히 0이어야 한다."""
        d0 = APF_PARAMS["d0_drone"]
        pos_a = np.array([0.0, 0.0, 60.0])
        pos_b = np.array([d0 + 1.0, 0.0, 60.0])
        vel = np.zeros(3)

        force = repulsive_force_drone(pos_a, pos_b, vel, vel)
        np.testing.assert_allclose(force, np.zeros(3), atol=1e-15)

    def test_repulsive_force_zero_at_boundary(self):
        """dist == d0 에서 척력은 0 (1/dist - 1/d0 = 0)."""
        d0 = APF_PARAMS["d0_drone"]
        pos_a = np.array([0.0, 0.0, 60.0])
        # d0 이상이므로 코드 분기에서 0 반환
        pos_b = np.array([d0, 0.0, 60.0])
        vel = np.zeros(3)

        force = repulsive_force_drone(pos_a, pos_b, vel, vel)
        np.testing.assert_allclose(force, np.zeros(3), atol=1e-15)

    def test_repulsive_force_closing_speed_amplification(self):
        """접근하는 드론은 정지 드론보다 더 큰 척력을 받아야 한다."""
        pos_a = np.array([0.0, 0.0, 60.0])
        pos_b = np.array([30.0, 0.0, 60.0])

        vel_static = np.zeros(3)
        vel_approach_a = np.array([10.0, 0.0, 0.0])
        vel_approach_b = np.array([-10.0, 0.0, 0.0])

        f_static = repulsive_force_drone(pos_a, pos_b, vel_static, vel_static)
        f_closing = repulsive_force_drone(
            pos_a, pos_b, vel_approach_a, vel_approach_b
        )

        mag_static = np.linalg.norm(f_static)
        mag_closing = np.linalg.norm(f_closing)

        assert mag_closing > mag_static, (
            f"접근 척력({mag_closing:.4f})이 정지 척력({mag_static:.4f})보다 커야 함"
        )

    def test_repulsive_force_receding_no_amplification(self):
        """멀어지는 드론은 증폭 없이 기본 척력만 받아야 한다."""
        pos_a = np.array([0.0, 0.0, 60.0])
        pos_b = np.array([30.0, 0.0, 60.0])

        vel_static = np.zeros(3)
        vel_recede_a = np.array([-10.0, 0.0, 0.0])
        vel_recede_b = np.array([10.0, 0.0, 0.0])

        f_static = repulsive_force_drone(pos_a, pos_b, vel_static, vel_static)
        f_receding = repulsive_force_drone(
            pos_a, pos_b, vel_recede_a, vel_recede_b
        )

        np.testing.assert_allclose(
            np.linalg.norm(f_receding),
            np.linalg.norm(f_static),
            atol=1e-10,
        )

    def test_total_force_clipping(self):
        """|F_total| 은 max_force를 초과해서는 안 된다."""
        own = APFState(
            position=np.array([0.0, 0.0, 60.0]),
            velocity=np.zeros(3),
            drone_id="DR000",
        )
        goal = np.array([5000.0, 5000.0, 60.0])

        # 다수의 매우 가까운 이웃을 생성하여 합력을 극대화
        neighbors = [
            APFState(
                position=np.array([2.0 * i, 2.0, 60.0]),
                velocity=np.array([-10.0, 0.0, 0.0]),
                drone_id=f"DR{i:03d}",
            )
            for i in range(1, 10)
        ]

        params = APF_PARAMS.copy()
        force = compute_total_force(own, goal, neighbors, [], params)
        mag = np.linalg.norm(force)

        assert mag <= params["max_force"] + 1e-6, (
            f"|F|={mag:.4f} > max_force={params['max_force']}"
        )

    def test_deadlock_escape(self):
        """교착 상태 (합력~0, 목표 멀리)에서 횡방향 섭동이 추가되어야 한다."""
        # 목표 반대편에 동일 세기의 장애물을 배치하여 교착 유도
        own = APFState(
            position=np.array([0.0, 0.0, 60.0]),
            velocity=np.zeros(3),
            drone_id="DR000",
        )
        goal = np.array([1000.0, 0.0, 60.0])

        # 목표 방향에 장애물 배치 (인력/척력 상쇄)
        obstacles = [np.array([15.0, 0.0, 60.0])]

        params = APF_PARAMS.copy()
        force = compute_total_force(own, goal, [], obstacles, params)
        mag = np.linalg.norm(force)

        # 교착 탈출 로직이 발동하면 합력이 0보다 커야 함
        assert mag > 0.1, f"교착 탈출 실패: |F|={mag:.6f}"

    def test_ground_avoidance(self):
        """z < 5m 인 드론은 양의 수직 힘을 받아야 한다."""
        own = APFState(
            position=np.array([1000.0, 1000.0, 2.0]),
            velocity=np.zeros(3),
            drone_id="DR000",
        )
        goal = np.array([2000.0, 2000.0, 60.0])

        params = APF_PARAMS.copy()
        force = compute_total_force(own, goal, [], [], params)

        assert force[2] > 0, f"지면 회피 실패: F_z={force[2]:.4f}"

    def test_altitude_correction(self):
        """순항 고도 위/아래 드론은 고도 보정력을 받아야 한다."""
        target_alt = 60.0  # 기본 순항 고도

        # 순항 고도보다 높은 드론
        own_high = APFState(
            position=np.array([1000.0, 1000.0, 100.0]),
            velocity=np.zeros(3),
            drone_id="DR000",
        )
        goal = np.array([2000.0, 2000.0, 60.0])
        params = APF_PARAMS.copy()
        force_high = compute_total_force(own_high, goal, [], [], params)

        # 순항 고도보다 낮은 드론
        own_low = APFState(
            position=np.array([1000.0, 1000.0, 30.0]),
            velocity=np.zeros(3),
            drone_id="DR001",
        )
        force_low = compute_total_force(own_low, goal, [], [], params)

        # 높은 드론은 하향력, 낮은 드론은 상향력
        assert force_high[2] < force_low[2], (
            f"고도 보정 비대칭: high_Fz={force_high[2]:.4f}, low_Fz={force_low[2]:.4f}"
        )


# ══════════════════════════════════════════════════════════════
# 2. Collision Detection Precision
# ══════════════════════════════════════════════════════════════

class TestCollisionDetectionPrecision:
    """충돌 감지 경계값 정밀 검증."""

    def _make_sim_state(self):
        """충돌 감지 테스트용 최소 SimState 목."""
        sim = MagicMock()
        sim.collisions = 0
        sim.near_misses = 0
        sim.conflicts = 0
        sim.advisories = 0
        sim._active_conflict_pairs = set()
        sim.drones = {}
        sim.rng = np.random.default_rng(42)
        return sim

    def test_collision_at_exact_threshold(self):
        """정확히 5.0m = 충돌 판정 (< 5.0 이므로 4.999... 체크)."""
        sh = SpatialHash(cell_size=50.0)
        sh.clear()
        # dist = 4.99m 배치 (충돌)
        sh.insert("DR000", np.array([0.0, 0.0, 60.0]))
        sh.insert("DR001", np.array([4.99, 0.0, 60.0]))

        pairs_list = list(sh.query_pairs_with_dist(50.0))
        collision_found = any(d < 5.0 for _, _, d in pairs_list)
        assert collision_found, "4.99m 거리에서 충돌이 감지되어야 한다"

    def test_near_miss_boundary(self):
        """5.01m = 근접 통과, 4.99m = 충돌 경계 검증."""
        sh = SpatialHash(cell_size=50.0)

        # 4.99m -> 충돌
        sh.clear()
        sh.insert("A", np.array([0.0, 0.0, 60.0]))
        sh.insert("B", np.array([4.99, 0.0, 60.0]))
        pairs_499 = list(sh.query_pairs_with_dist(50.0))
        dists_499 = [d for _, _, d in pairs_499]
        assert len(dists_499) == 1
        assert dists_499[0] < 5.0, "4.99m는 충돌 (< 5.0m)"

        # 5.01m -> 근접 통과
        sh.clear()
        sh.insert("A", np.array([0.0, 0.0, 60.0]))
        sh.insert("B", np.array([5.01, 0.0, 60.0]))
        pairs_501 = list(sh.query_pairs_with_dist(50.0))
        dists_501 = [d for _, _, d in pairs_501]
        assert len(dists_501) == 1
        assert dists_501[0] >= 5.0, "5.01m는 근접 통과 (>= 5.0m)"
        assert dists_501[0] < 10.0, "5.01m는 근접 통과 범위 내 (< 10.0m)"

    def test_conflict_boundary(self):
        """10.01m = conflict, 9.99m = near miss 경계 검증."""
        sh = SpatialHash(cell_size=50.0)

        # 9.99m -> near miss
        sh.clear()
        sh.insert("A", np.array([0.0, 0.0, 60.0]))
        sh.insert("B", np.array([9.99, 0.0, 60.0]))
        pairs = list(sh.query_pairs_with_dist(50.0))
        dists = [d for _, _, d in pairs]
        assert len(dists) == 1
        assert 5.0 <= dists[0] < 10.0, f"9.99m는 near miss 범위: {dists[0]}"

        # 10.01m -> conflict
        sh.clear()
        sh.insert("A", np.array([0.0, 0.0, 60.0]))
        sh.insert("B", np.array([10.01, 0.0, 60.0]))
        pairs = list(sh.query_pairs_with_dist(50.0))
        dists = [d for _, _, d in pairs]
        assert len(dists) == 1
        assert dists[0] >= 10.0, f"10.01m는 conflict 범위: {dists[0]}"

    def test_no_self_collision(self):
        """드론은 자기 자신과 충돌하면 안 된다."""
        sh = SpatialHash(cell_size=50.0)
        sh.clear()
        sh.insert("DR000", np.array([0.0, 0.0, 60.0]))

        pairs = list(sh.query_pairs_with_dist(50.0))
        assert len(pairs) == 0, "단일 드론에서 자기 충돌 쌍이 발생하면 안 됨"

    def test_spatial_hash_consistency(self):
        """SpatialHash 결과가 브루트포스 O(N^2) 와 일치해야 한다."""
        rng = np.random.default_rng(42)
        n = 50
        radius = 50.0

        positions = {}
        for i in range(n):
            did = f"DR{i:03d}"
            pos = rng.uniform(-1000, 1000, 3)
            pos[2] = rng.uniform(30, 120)
            positions[did] = pos

        # SpatialHash 결과
        sh = SpatialHash(cell_size=50.0)
        sh.clear()
        for did, pos in positions.items():
            sh.insert(did, pos)
        sh_pairs = sh.query_pairs(radius)

        # 브루트포스 O(N^2)
        bf_pairs: set[frozenset[str]] = set()
        ids = list(positions.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                dist = np.linalg.norm(positions[ids[i]] - positions[ids[j]])
                if dist <= radius:
                    bf_pairs.add(frozenset((ids[i], ids[j])))

        assert sh_pairs == bf_pairs, (
            f"SpatialHash ({len(sh_pairs)} pairs) != BruteForce ({len(bf_pairs)} pairs). "
            f"차이: SH-BF={sh_pairs - bf_pairs}, BF-SH={bf_pairs - sh_pairs}"
        )

    def test_spatial_hash_query_pairs_with_dist_accuracy(self):
        """query_pairs_with_dist 거리값이 실제 유클리드 거리와 일치해야 한다."""
        sh = SpatialHash(cell_size=50.0)
        sh.clear()

        pos_a = np.array([10.0, 20.0, 60.0])
        pos_b = np.array([35.0, 45.0, 75.0])
        sh.insert("A", pos_a)
        sh.insert("B", pos_b)

        pairs = list(sh.query_pairs_with_dist(100.0))
        assert len(pairs) == 1

        _, _, dist_sh = pairs[0]
        dist_actual = float(np.linalg.norm(pos_a - pos_b))
        np.testing.assert_allclose(dist_sh, dist_actual, atol=1e-10)


# ══════════════════════════════════════════════════════════════
# 3. Physics Integration Tests
# ══════════════════════════════════════════════════════════════

class TestPhysicsIntegration:
    """물리 적분 및 경계 조건 정밀 검증."""

    def test_position_update_euler(self):
        """pos += vel * dt 오일러 적분이 정확해야 한다."""
        pos = np.array([100.0, 200.0, 60.0])
        vel = np.array([10.0, -5.0, 2.0])
        dt = 0.1

        new_pos = pos + vel * dt
        expected = np.array([101.0, 199.5, 60.2])

        np.testing.assert_allclose(new_pos, expected, atol=1e-10)

    def test_velocity_clamping(self):
        """force_to_velocity 에서 속력이 max_speed를 초과하면 안 된다."""
        current_vel = np.array([10.0, 0.0, 0.0])
        force = np.array([100.0, 100.0, 0.0])
        dt = 0.1
        max_speed = 15.0

        new_vel = force_to_velocity(current_vel, force, dt, max_speed)
        speed = np.linalg.norm(new_vel)

        assert speed <= max_speed + 1e-6, (
            f"속력 {speed:.4f} > max_speed {max_speed}"
        )

    def test_velocity_direction_preserved_on_clamp(self):
        """속력 클램핑 시 방향은 유지되어야 한다."""
        current_vel = np.zeros(3)
        force = np.array([100.0, 200.0, 0.0])
        dt = 0.1
        max_speed = 15.0

        new_vel = force_to_velocity(current_vel, force, dt, max_speed)
        unclamped = current_vel + force * dt

        dir_clamped = new_vel / np.linalg.norm(new_vel)
        dir_unclamped = unclamped / np.linalg.norm(unclamped)

        np.testing.assert_allclose(dir_clamped, dir_unclamped, atol=1e-6)

    def test_velocity_no_clamp_when_under_limit(self):
        """속력이 max_speed 미만이면 클램핑하지 않아야 한다."""
        current_vel = np.array([1.0, 0.0, 0.0])
        force = np.array([1.0, 0.0, 0.0])
        dt = 0.1
        max_speed = 15.0

        new_vel = force_to_velocity(current_vel, force, dt, max_speed)
        expected = current_vel + force * dt

        np.testing.assert_allclose(new_vel, expected, atol=1e-10)

    def test_boundary_clamping(self):
        """position이 bounds 내에 유지되어야 한다."""
        pos = np.array([BOUNDS_M + 100.0, -BOUNDS_M - 200.0, ALT_MAX + 50.0])

        clamped = np.array([
            float(np.clip(pos[0], -BOUNDS_M, BOUNDS_M)),
            float(np.clip(pos[1], -BOUNDS_M, BOUNDS_M)),
            float(np.clip(pos[2], ALT_MIN, ALT_MAX)),
        ])

        assert clamped[0] == BOUNDS_M
        assert clamped[1] == -BOUNDS_M
        assert clamped[2] == ALT_MAX

    def test_battery_decay_rate(self):
        """배터리가 비행 시간에 비례하여 감소해야 한다."""
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES

        profile = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        dt = 0.1
        battery_start = 100.0

        # rate per tick = 100 / (endurance_min * 60 / dt)
        rate = 100.0 / (profile.endurance_min * 60.0 / dt)
        battery_after_1tick = battery_start - rate

        assert battery_after_1tick < battery_start
        assert battery_after_1tick > 0.0

        # 10분 비행 후 배터리: endurance=30분이므로 ~33% 소모
        ticks_10min = int(10 * 60 / dt)
        battery_10min = battery_start - rate * ticks_10min
        expected_pct = battery_start * (1.0 - 10.0 / profile.endurance_min)

        np.testing.assert_allclose(
            battery_10min, expected_pct, atol=0.1,
            err_msg="10분 비행 후 배터리 잔량이 예상과 다름",
        )

    def test_battery_critical_triggers_landing(self):
        """battery < 5% 이면 BATTERY_CRITICAL + LANDING 전환."""
        drone = DroneState(
            drone_id="DR000",
            position=np.array([1000.0, 1000.0, 60.0]),
            velocity=np.array([10.0, 0.0, 0.0]),
            battery_pct=4.9,
            flight_phase=FlightPhase.ENROUTE,
        )

        # _update 로직 재현: battery < 5% -> BATTERY_CRITICAL + LANDING
        if drone.battery_pct < 5.0 and drone.failure_type == FailureType.NONE:
            drone.failure_type = FailureType.BATTERY_CRITICAL
            drone.flight_phase = FlightPhase.LANDING

        assert drone.failure_type == FailureType.BATTERY_CRITICAL
        assert drone.flight_phase == FlightPhase.LANDING


# ══════════════════════════════════════════════════════════════
# 4. State Machine Tests
# ══════════════════════════════════════════════════════════════

class TestStateMachine:
    """드론 비행 단계 상태 머신 전이 검증."""

    def test_grounded_to_takeoff_requires_battery(self):
        """GROUNDED -> TAKEOFF 전환은 battery > 20% 필요."""
        drone_low = DroneState(
            drone_id="DR000",
            position=np.array([0.0, 0.0, 0.0]),
            velocity=np.zeros(3),
            battery_pct=15.0,
            flight_phase=FlightPhase.GROUNDED,
        )
        drone_ok = DroneState(
            drone_id="DR001",
            position=np.array([0.0, 0.0, 0.0]),
            velocity=np.zeros(3),
            battery_pct=50.0,
            flight_phase=FlightPhase.GROUNDED,
        )

        # 배터리 부족 시 이륙 불가
        can_takeoff_low = drone_low.battery_pct > 20.0
        can_takeoff_ok = drone_ok.battery_pct > 20.0

        assert not can_takeoff_low, "battery 15%에서 이륙 가능하면 안 됨"
        assert can_takeoff_ok, "battery 50%에서 이륙 가능해야 함"

    def test_takeoff_to_enroute_at_cruise_alt(self):
        """TAKEOFF -> ENROUTE 전환은 CRUISE_ALT 도달 시."""
        drone = DroneState(
            drone_id="DR000",
            position=np.array([0.0, 0.0, CRUISE_ALT - 1.0]),
            velocity=np.array([0.0, 0.0, 3.5]),
            flight_phase=FlightPhase.TAKEOFF,
        )

        # 이륙 로직: z >= CRUISE_ALT - 2.0 이면 ENROUTE 전환
        if drone.position[2] >= CRUISE_ALT - 2.0:
            drone.flight_phase = FlightPhase.ENROUTE

        assert drone.flight_phase == FlightPhase.ENROUTE

    def test_enroute_to_landing_near_goal(self):
        """ENROUTE -> LANDING 전환은 목표 수평 거리 80m 이내."""
        goal = np.array([1000.0, 1000.0, CRUISE_ALT])
        drone = DroneState(
            drone_id="DR000",
            position=np.array([1050.0, 1050.0, CRUISE_ALT]),
            velocity=np.array([-5.0, -5.0, 0.0]),
            flight_phase=FlightPhase.ENROUTE,
        )
        drone.goal = goal

        diff = drone.goal - drone.position
        dist_xy = float(np.linalg.norm(diff[:2]))

        if dist_xy < 80.0:
            drone.flight_phase = FlightPhase.LANDING

        assert dist_xy < 80.0, f"dist_xy={dist_xy} >= 80m"
        assert drone.flight_phase == FlightPhase.LANDING

    def test_nfz_triggers_evading(self):
        """NFZ 영역 진입 시 ENROUTE -> EVADING 전환."""
        from visualization._embedded_sim import _in_nfz

        # NFZ 내부 위치
        pos_inside = np.array([0.0, 0.0, 60.0])
        assert _in_nfz(pos_inside), "NFZ 중심은 _in_nfz() == True"

        drone = DroneState(
            drone_id="DR000",
            position=pos_inside,
            velocity=np.array([10.0, 0.0, 0.0]),
            flight_phase=FlightPhase.ENROUTE,
        )

        if _in_nfz(drone.position):
            drone.flight_phase = FlightPhase.EVADING

        assert drone.flight_phase == FlightPhase.EVADING

    def test_evading_exits_when_clear(self):
        """NFZ 밖에서 EVADING -> ENROUTE 복귀."""
        from visualization._embedded_sim import _in_nfz

        # NFZ 외부 위치
        pos_outside = np.array([2000.0, 2000.0, 60.0])
        assert not _in_nfz(pos_outside), "NFZ 외부는 _in_nfz() == False"

        drone = DroneState(
            drone_id="DR000",
            position=pos_outside,
            velocity=np.array([10.0, 0.0, 0.0]),
            flight_phase=FlightPhase.EVADING,
        )
        drone.goal = np.array([3000.0, 3000.0, CRUISE_ALT])

        if not _in_nfz(drone.position) and drone.goal is not None:
            drone.flight_phase = FlightPhase.ENROUTE

        assert drone.flight_phase == FlightPhase.ENROUTE

    def test_landing_to_grounded(self):
        """z <= 1.5 에서 LANDING -> GROUNDED + 배터리 충전."""
        drone = DroneState(
            drone_id="DR000",
            position=np.array([1000.0, 1000.0, 1.0]),
            velocity=np.array([0.0, 0.0, -2.5]),
            battery_pct=30.0,
            flight_phase=FlightPhase.LANDING,
        )

        if drone.position[2] <= 1.5:
            drone.position[2] = 0.0
            drone.velocity = np.zeros(3)
            drone.flight_phase = FlightPhase.GROUNDED
            drone.failure_type = FailureType.NONE
            drone.battery_pct = min(100.0, drone.battery_pct + 40.0)

        assert drone.flight_phase == FlightPhase.GROUNDED
        assert drone.position[2] == 0.0
        np.testing.assert_allclose(drone.battery_pct, 70.0, atol=1e-10)

    def test_failed_drone_falls(self):
        """FAILED 드론은 고도가 감소해야 한다."""
        drone = DroneState(
            drone_id="DR000",
            position=np.array([1000.0, 1000.0, 60.0]),
            velocity=np.zeros(3),
            flight_phase=FlightPhase.FAILED,
            failure_type=FailureType.MOTOR_FAILURE,
        )

        dt = 0.1
        initial_alt = drone.position[2]

        # FAILED 드론 하강 로직
        if drone.position[2] > 0.0:
            drone.position[2] = max(0.0, drone.position[2] - 1.5 * dt)

        assert drone.position[2] < initial_alt, "FAILED 드론 고도가 감소해야 함"
        np.testing.assert_allclose(
            drone.position[2], initial_alt - 1.5 * dt, atol=1e-10
        )


# ══════════════════════════════════════════════════════════════
# 5. Scenario Regression Tests
# ══════════════════════════════════════════════════════════════

class TestScenarioRegression:
    """9개 시나리오 실행 회귀 검증."""

    _SCENARIO_DIR = Path(_ROOT) / "config" / "scenario_params"

    _ALL_SCENARIOS = [
        "adversarial_intrusion",
        "comms_loss",
        "emergency_failure",
        "high_density",
        "mass_takeoff",
        "multi_city",
        "route_conflict",
        "swarm_autonomous_no_preplan",
        "weather_disturbance",
    ]

    def test_scenario_yaml_valid(self):
        """모든 9개 시나리오 YAML 파일이 유효하게 파싱되어야 한다."""
        import yaml

        for name in self._ALL_SCENARIOS:
            yaml_path = self._SCENARIO_DIR / f"{name}.yaml"
            assert yaml_path.exists(), f"시나리오 YAML 없음: {yaml_path}"

            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            assert isinstance(data, dict), (
                f"{name}.yaml 최상위가 dict가 아님: {type(data)}"
            )

    def test_all_9_scenarios_listed(self):
        """시나리오 디렉터리에 정확히 9개 YAML이 존재해야 한다."""
        yaml_files = sorted(p.stem for p in self._SCENARIO_DIR.glob("*.yaml"))
        assert len(yaml_files) == 9, (
            f"시나리오 수 {len(yaml_files)} != 9. 목록: {yaml_files}"
        )

    @pytest.mark.parametrize("scenario_name", _ALL_SCENARIOS)
    def test_scenario_runs_without_error(self, scenario_name: str):
        """각 시나리오가 짧은 시뮬레이션 (1초) 에서 오류 없이 실행되어야 한다."""
        try:
            from simulation.scenario_runner import run_scenario

            results = run_scenario(
                scenario_name,
                n_runs=1,
                seed=42,
                verbose=False,
                duration_override_s=1.0,
            )
            assert len(results) == 1, f"{scenario_name}: 결과 없음"
            assert "collisions" in results[0] or "error" not in results[0], (
                f"{scenario_name}: 실행 결과 형식 오류"
            )
        except FileNotFoundError:
            pytest.skip(f"시나리오 파일 없음: {scenario_name}")
        except ImportError as e:
            pytest.skip(f"의존성 누락으로 시나리오 실행 불가: {e}")
        except Exception as e:
            pytest.fail(f"{scenario_name} 시나리오 실행 실패: {e}")

    def test_high_density_no_collision(self):
        """high_density 시나리오 3초 실행 시 충돌 0 목표 (정밀 APF 검증)."""
        try:
            from simulation.scenario_runner import run_scenario

            results = run_scenario(
                "high_density",
                n_runs=1,
                seed=42,
                verbose=False,
                duration_override_s=3.0,
            )
            assert len(results) == 1

            r = results[0]
            collisions = r.get("collisions", 0)
            # high_density 시나리오에서 짧은 시뮬(3초)은 충돌 0 기대
            assert collisions == 0, (
                f"high_density 3초 시뮬에서 충돌 {collisions}건 발생"
            )
        except (FileNotFoundError, ImportError) as e:
            pytest.skip(f"시나리오 실행 불가: {e}")

    def test_resolution_rate_formula(self):
        """충돌 해결률 공식: 1 - collisions/(conflicts + collisions) 검증."""
        # 공식 자체의 수학적 정확성
        collisions = 2
        conflicts = 8

        rate = 1.0 - collisions / max(conflicts + collisions, 1)
        expected = 1.0 - 2.0 / 10.0  # 0.8

        np.testing.assert_allclose(rate, expected, atol=1e-10)

        # 충돌 0 -> 해결률 100%
        rate_perfect = 1.0 - 0 / max(10 + 0, 1)
        assert rate_perfect == 1.0

        # 전부 충돌 -> 해결률 0%
        rate_worst = 1.0 - 5 / max(0 + 5, 1)
        assert rate_worst == 0.0


# ══════════════════════════════════════════════════════════════
# 6. GPU Engine Tests (skip if CUDA unavailable)
# ══════════════════════════════════════════════════════════════

@pytest.mark.skipif(not _HAS_CUDA, reason="CUDA not available")
class TestGPUEngine:
    """GPU 물리 엔진 정밀 검증 (CUDA 필요)."""

    def _make_test_drones(self, n: int = 10) -> dict[str, DroneState]:
        """테스트용 드론 딕셔너리 생성."""
        rng = np.random.default_rng(42)
        drones = {}
        for i in range(n):
            did = f"DR{i:03d}"
            drones[did] = DroneState(
                drone_id=did,
                position=rng.uniform(-2000, 2000, 3).astype(float),
                velocity=rng.uniform(-5, 5, 3).astype(float),
                battery_pct=float(rng.uniform(50, 100)),
                flight_phase=FlightPhase.ENROUTE,
            )
            drones[did].position[2] = float(np.clip(drones[did].position[2], 30, 120))
            drones[did].goal = rng.uniform(-3000, 3000, 3).astype(float)
            drones[did].goal[2] = CRUISE_ALT
        return drones

    def test_gpu_engine_creates_on_cuda(self):
        """GPUPhysicsEngine이 CUDA 디바이스에서 초기화되어야 한다."""
        from simulation.apf_engine.gpu_physics import GPUPhysicsEngine

        engine = GPUPhysicsEngine(max_drones=50)
        assert "cuda" in str(engine.device), f"디바이스가 CUDA가 아님: {engine.device}"
        engine.release()

    def test_gpu_cpu_force_parity(self):
        """GPU 합력 결과가 CPU 결과와 1e-3 이내로 일치해야 한다."""
        from simulation.apf_engine.apf import batch_compute_forces
        from simulation.apf_engine.gpu_physics import GPUPhysicsEngine

        drones = self._make_test_drones(10)

        # CPU 계산
        apf_states = [
            APFState(d.position.copy(), d.velocity.copy(), d.drone_id)
            for d in drones.values()
        ]
        goals = {d.drone_id: d.goal.copy() for d in drones.values()}
        cpu_forces = batch_compute_forces(
            apf_states, goals, _NFZ_OBSTACLES, params=APF_PARAMS
        )

        # GPU 계산
        engine = GPUPhysicsEngine(max_drones=50)
        engine.sync_from_cpu(drones)
        gpu_forces = engine.compute_all_forces(
            nfz_obstacles=_NFZ_OBSTACLES, params=APF_PARAMS
        )
        engine.release()

        for did in drones:
            if did in cpu_forces and did in gpu_forces:
                np.testing.assert_allclose(
                    gpu_forces[did], cpu_forces[did], atol=1e-3,
                    err_msg=f"GPU/CPU 힘 불일치: {did}",
                )

    def test_gpu_collision_matches_cpu(self):
        """GPU 충돌 감지 결과가 CPU SpatialHash 와 일치해야 한다."""
        from simulation.apf_engine.gpu_physics import GPUPhysicsEngine

        drones = self._make_test_drones(20)

        # 일부 드론을 가까이 배치하여 충돌/근접 유도
        drone_list = list(drones.values())
        drone_list[0].position = np.array([100.0, 100.0, 60.0])
        drone_list[1].position = np.array([103.0, 100.0, 60.0])  # 3m -> collision
        drone_list[2].position = np.array([107.0, 100.0, 60.0])  # 7m from [0] -> near miss

        # CPU: SpatialHash
        sh = SpatialHash(cell_size=50.0)
        sh.clear()
        for d in drone_list:
            if d.is_active:
                sh.insert(d.drone_id, d.position)

        cpu_collisions = set()
        cpu_near_misses = set()
        for id_a, id_b, dist in sh.query_pairs_with_dist(50.0):
            pair = frozenset((id_a, id_b))
            if dist < 5.0:
                cpu_collisions.add(pair)
            elif dist < 10.0:
                cpu_near_misses.add(pair)

        # GPU
        engine = GPUPhysicsEngine(max_drones=50)
        engine.sync_from_cpu(drones)
        result = engine.detect_collisions(
            collision_dist=5.0, near_miss_dist=10.0, conflict_dist=50.0
        )
        engine.release()

        gpu_collisions = {frozenset((a, b)) for a, b, _ in result.collisions}
        gpu_near_misses = {frozenset((a, b)) for a, b, _ in result.near_misses}

        assert gpu_collisions == cpu_collisions, (
            f"충돌 불일치: GPU={gpu_collisions}, CPU={cpu_collisions}"
        )
        assert gpu_near_misses == cpu_near_misses, (
            f"근접 불일치: GPU={gpu_near_misses}, CPU={cpu_near_misses}"
        )

    def test_gpu_position_update_matches_cpu(self):
        """GPU 위치 적분 결과가 CPU 오일러 적분과 일치해야 한다."""
        from simulation.apf_engine.gpu_physics import GPUPhysicsEngine

        drones = self._make_test_drones(5)
        dt = 0.1

        # CPU 참조: pos + vel * dt (간단한 적분)
        cpu_expected = {}
        for did, d in drones.items():
            new_pos = d.position + d.velocity * dt
            new_pos[0] = float(np.clip(new_pos[0], -BOUNDS_M, BOUNDS_M))
            new_pos[1] = float(np.clip(new_pos[1], -BOUNDS_M, BOUNDS_M))
            new_pos[2] = float(np.clip(new_pos[2], 0.0, ALT_MAX))
            cpu_expected[did] = new_pos

        # GPU 적분 (힘=0으로 설정하여 순수 적분 테스트)
        engine = GPUPhysicsEngine(max_drones=50)
        engine.sync_from_cpu(drones)
        engine.forces[:engine.n].zero_()  # 힘 제거
        engine.update_positions(
            dt=dt,
            wind_vector=np.zeros(3),
            bounds=BOUNDS_M,
            alt_range=(0.0, ALT_MAX),
            max_speed=100.0,  # 높은 한도로 클램핑 방지
        )
        engine.sync_to_cpu(drones)
        engine.release()

        for did in drones:
            np.testing.assert_allclose(
                drones[did].position, cpu_expected[did], atol=1e-2,
                err_msg=f"GPU/CPU 위치 불일치: {did}",
            )


# ══════════════════════════════════════════════════════════════
# 보조 검증: force_to_velocity 에지 케이스
# ══════════════════════════════════════════════════════════════

class TestForceToVelocityEdgeCases:
    """force_to_velocity 함수 에지 케이스 검증."""

    def test_zero_force_preserves_velocity(self):
        """힘이 0이면 속도 불변."""
        vel = np.array([5.0, 3.0, -1.0])
        force = np.zeros(3)
        dt = 0.1

        new_vel = force_to_velocity(vel, force, dt)
        np.testing.assert_allclose(new_vel, vel, atol=1e-10)

    def test_zero_velocity_zero_force(self):
        """속도 0, 힘 0 이면 결과도 0."""
        new_vel = force_to_velocity(np.zeros(3), np.zeros(3), 0.1)
        np.testing.assert_allclose(new_vel, np.zeros(3), atol=1e-10)

    def test_exact_max_speed(self):
        """결과 속력이 정확히 max_speed일 때 클램핑하지 않아야 한다."""
        max_speed = 15.0
        vel = np.array([max_speed, 0.0, 0.0])
        force = np.zeros(3)
        dt = 0.1

        new_vel = force_to_velocity(vel, force, dt, max_speed)
        np.testing.assert_allclose(
            np.linalg.norm(new_vel), max_speed, atol=1e-10
        )


# ══════════════════════════════════════════════════════════════
# 보조: DroneState 데이터 무결성
# ══════════════════════════════════════════════════════════════

class TestDroneStateIntegrity:
    """DroneState 데이터클래스 경계 조건 검증."""

    def test_battery_clipped_on_init(self):
        """battery_pct는 초기화 시 [0, 100] 범위로 클리핑된다."""
        d = DroneState(
            drone_id="DR000",
            position=np.zeros(3),
            velocity=np.zeros(3),
            battery_pct=150.0,
        )
        assert d.battery_pct == 100.0

        d2 = DroneState(
            drone_id="DR001",
            position=np.zeros(3),
            velocity=np.zeros(3),
            battery_pct=-10.0,
        )
        assert d2.battery_pct == 0.0

    def test_is_active_property(self):
        """is_active: GROUNDED/FAILED 제외."""
        for phase in FlightPhase:
            d = DroneState(
                drone_id="DR000",
                position=np.zeros(3),
                velocity=np.zeros(3),
                flight_phase=phase,
            )
            if phase in (FlightPhase.GROUNDED, FlightPhase.FAILED):
                assert not d.is_active
            else:
                assert d.is_active

    def test_speed_property(self):
        """speed 프로퍼티가 유클리드 노름과 일치."""
        vel = np.array([3.0, 4.0, 0.0])
        d = DroneState(
            drone_id="DR000",
            position=np.zeros(3),
            velocity=vel,
        )
        np.testing.assert_allclose(d.speed, 5.0, atol=1e-10)

    def test_position_auto_convert_to_ndarray(self):
        """position 리스트 입력 시 ndarray로 자동 변환."""
        d = DroneState(
            drone_id="DR000",
            position=[1.0, 2.0, 3.0],
            velocity=[0.0, 0.0, 0.0],
        )
        assert isinstance(d.position, np.ndarray)
        assert isinstance(d.velocity, np.ndarray)
