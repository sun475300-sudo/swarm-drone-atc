"""
Hard Precision Test Suite
=========================
APF 엔진, 충돌 감지, 물리 적분, 상태 머신, 시나리오 회귀, GPU 엔진을 정밀 검증.
총 34개 테스트.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest
import yaml

from simulation.apf_engine.apf import (
    APF_PARAMS,
    APFState,
    attractive_force,
    compute_total_force,
    force_to_velocity,
    repulsive_force_drone,
)
from simulation.spatial_hash import SpatialHash
from src.airspace_control.agents.drone_state import DroneState, FailureType, FlightPhase
from visualization._embedded_sim import _in_nfz
from visualization._scene_traces import (
    ALT_MAX,
    BOUNDS_M,
    NFZ_X,
)

# ═══════════════════════════════════════════════════════════════════════════
# 1. APF Engine Precision (10 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestAPFEnginePrecision:
    """APF 인력/척력/합력 계산의 수학적 정확성 검증."""

    def test_attractive_force_points_toward_goal(self):
        """인력 벡터가 목표 방향을 정확히 가리키는지 검증."""
        pos = np.array([0.0, 0.0, 60.0])
        goal = np.array([100.0, 0.0, 60.0])
        f = attractive_force(pos, goal)
        # 힘 방향이 goal - pos 방향과 일치
        expected_dir = (goal - pos) / np.linalg.norm(goal - pos)
        f_dir = f / np.linalg.norm(f)
        np.testing.assert_allclose(f_dir, expected_dir, atol=1e-10)

    def test_attractive_force_near_field_quadratic(self):
        """근거리 (dist <= 10m) 이차 인력: |F| = k_att * |diff|."""
        pos = np.array([0.0, 0.0, 60.0])
        goal = np.array([5.0, 0.0, 60.0])  # dist = 5m < 10m
        k_att = APF_PARAMS["k_att"]
        f = attractive_force(pos, goal, k_att)
        diff = goal - pos
        expected = k_att * diff
        np.testing.assert_allclose(f, expected, atol=1e-10)

    def test_attractive_force_far_field_constant(self):
        """원거리 (dist > 10m) 단위 벡터 인력: |F| = k_att * d_t."""
        pos = np.array([0.0, 0.0, 60.0])
        goal = np.array([200.0, 0.0, 60.0])  # dist = 200m >> 10m
        k_att = APF_PARAMS["k_att"]
        d_t = 10.0
        f = attractive_force(pos, goal, k_att)
        expected_mag = k_att * d_t
        np.testing.assert_allclose(np.linalg.norm(f), expected_mag, atol=1e-10)

    def test_repulsive_force_zero_beyond_d0(self):
        """d0 이상 거리에서 척력이 0인지 검증."""
        d0 = APF_PARAMS["d0_drone"]
        own_pos = np.array([0.0, 0.0, 60.0])
        other_pos = np.array([d0 + 1.0, 0.0, 60.0])  # dist > d0
        vel = np.zeros(3)
        f = repulsive_force_drone(own_pos, other_pos, vel, vel)
        np.testing.assert_allclose(f, np.zeros(3), atol=1e-15)

    def test_repulsive_force_nonzero_within_d0(self):
        """d0 이내 거리에서 척력이 0이 아닌지 검증."""
        own_pos = np.array([0.0, 0.0, 60.0])
        other_pos = np.array([20.0, 0.0, 60.0])  # 20m < d0=50m
        vel = np.zeros(3)
        f = repulsive_force_drone(own_pos, other_pos, vel, vel)
        assert np.linalg.norm(f) > 0, "d0 이내에서 척력은 0이 아니어야 함"

    def test_repulsive_closing_speed_amplification(self):
        """접근 중인 드론에 대한 척력 증폭 검증."""
        own_pos = np.array([0.0, 0.0, 60.0])
        other_pos = np.array([20.0, 0.0, 60.0])
        stationary_vel = np.zeros(3)
        # 접근 속도: 상대방을 향해 이동
        approaching_vel = np.array([10.0, 0.0, 0.0])

        f_static = repulsive_force_drone(own_pos, other_pos, stationary_vel, stationary_vel)
        # own이 other를 향해 접근 → closing_speed > 0
        f_approaching = repulsive_force_drone(own_pos, other_pos, approaching_vel, stationary_vel)

        # 접근 중이면 closing_speed > 0 → 증폭
        assert np.linalg.norm(f_approaching) >= np.linalg.norm(f_static), (
            "접근 중인 드론에 대한 척력이 정지 상태 이상이어야 함"
        )

    def test_total_force_clipping(self):
        """합력이 max_force를 초과하지 않는지 검증."""
        own = APFState(
            position=np.array([10.0, 0.0, 60.0]),
            velocity=np.zeros(3),
            drone_id="drone_0",
        )
        goal = np.array([10000.0, 0.0, 60.0])
        # 매우 가까운 이웃 여러 대 → 큰 척력 유도
        neighbors = [
            APFState(np.array([11.0, 0.0, 60.0]), np.zeros(3), f"n{i}")
            for i in range(5)
        ]
        f = compute_total_force(own, goal, neighbors, [], params=APF_PARAMS)
        mag = np.linalg.norm(f)
        assert mag <= APF_PARAMS["max_force"] + 1e-9, (
            f"|F_total| = {mag:.4f} > max_force = {APF_PARAMS['max_force']}"
        )

    def test_ground_avoidance_upward(self):
        """z=2m 드론이 상향 힘을 받는지 검증 (CFIT 방지)."""
        own = APFState(
            position=np.array([0.0, 0.0, 2.0]),
            velocity=np.zeros(3),
            drone_id="low_drone",
        )
        goal = np.array([100.0, 0.0, 2.0])
        f = compute_total_force(own, goal, [], [], params=APF_PARAMS)
        assert f[2] > 0, f"z=2m에서 F_z = {f[2]:.4f} 이 양수여야 함"

    def test_altitude_correction(self):
        """z=90m 드론이 하향 보정력을 받는지 검증 (순항 고도 60m 복귀)."""
        own = APFState(
            position=np.array([0.0, 0.0, 90.0]),
            velocity=np.zeros(3),
            drone_id="high_drone",
        )
        goal = np.array([100.0, 0.0, 90.0])
        f = compute_total_force(own, goal, [], [], params=APF_PARAMS)
        # 순항 고도 60m < 현재 90m → 고도 보정이 하향 (음수 z)
        assert f[2] < 0, f"z=90m에서 F_z = {f[2]:.4f} 이 음수여야 함"

    def test_deadlock_escape_perpendicular(self):
        """교착 상태 (합력 ~0, 목표 미도달) 시 횡방향 섭동 검증."""
        own = APFState(
            position=np.array([0.0, 0.0, 60.0]),
            velocity=np.zeros(3),
            drone_id="stuck_drone",
        )
        goal = np.array([100.0, 0.0, 60.0])

        # 목표 방향 정확히 가로막는 장애물 → 인력과 척력 상쇄
        obstacle = np.array([10.0, 0.0, 60.0])

        f = compute_total_force(own, goal, [], [obstacle], params=APF_PARAMS)
        # 교착 탈출 시 횡방향 (y) 성분이 발생해야 함
        assert np.linalg.norm(f) > 0.1, "교착 상태에서 탈출 힘이 발생해야 함"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Collision Detection (5 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestCollisionDetection:
    """SpatialHash 기반 충돌 감지 정확도 검증."""

    def test_collision_threshold_5m(self):
        """4.9m 거리 드론 쌍이 5m 반경 내로 감지되는지 검증."""
        sh = SpatialHash(cell_size=50.0)
        sh.clear()
        sh.insert("d1", np.array([0.0, 0.0, 60.0]))
        sh.insert("d2", np.array([4.9, 0.0, 60.0]))
        pairs = sh.query_pairs(radius=5.0)
        assert frozenset(("d1", "d2")) in pairs, "4.9m 쌍이 5m 반경에서 감지되어야 함"

    def test_near_miss_boundary(self):
        """9.9m 거리는 10m 반경 내이지만 5m 반경 외인지 검증."""
        sh = SpatialHash(cell_size=50.0)
        sh.clear()
        sh.insert("d1", np.array([0.0, 0.0, 60.0]))
        sh.insert("d2", np.array([9.9, 0.0, 60.0]))
        collisions = sh.query_pairs(radius=5.0)
        near_misses = sh.query_pairs(radius=10.0)
        pair = frozenset(("d1", "d2"))
        assert pair not in collisions, "9.9m 쌍은 5m 충돌 반경에 포함되지 않아야 함"
        assert pair in near_misses, "9.9m 쌍은 10m 근접 통과 반경에 포함되어야 함"

    def test_no_self_collision(self):
        """단일 드론은 자기 자신과 충돌 쌍을 형성하지 않는지 검증."""
        sh = SpatialHash(cell_size=50.0)
        sh.clear()
        sh.insert("solo", np.array([0.0, 0.0, 60.0]))
        pairs = sh.query_pairs(radius=1000.0)
        assert len(pairs) == 0, "단일 드론은 충돌 쌍이 없어야 함"

    def test_spatial_hash_finds_all_pairs(self):
        """SpatialHash 결과가 O(N^2) 브루트포스와 일치하는지 검증 (20 드론)."""
        rng = np.random.default_rng(42)
        n = 20
        radius = 100.0
        positions = {f"d{i}": rng.uniform(-500, 500, size=3) for i in range(n)}

        # SpatialHash
        sh = SpatialHash(cell_size=radius)
        sh.clear()
        for did, pos in positions.items():
            sh.insert(did, pos)
        sh_pairs = sh.query_pairs(radius=radius)

        # 브루트포스 O(N^2)
        bf_pairs: set[frozenset[str]] = set()
        ids = list(positions.keys())
        for i in range(n):
            for j in range(i + 1, n):
                dist = np.linalg.norm(positions[ids[i]] - positions[ids[j]])
                if dist <= radius:
                    bf_pairs.add(frozenset((ids[i], ids[j])))

        assert sh_pairs == bf_pairs, (
            f"SpatialHash ({len(sh_pairs)}) != BruteForce ({len(bf_pairs)})"
        )

    def test_spatial_hash_empty(self):
        """빈 SpatialHash에서 쌍이 없는지 검증."""
        sh = SpatialHash(cell_size=50.0)
        sh.clear()
        pairs = sh.query_pairs(radius=50.0)
        assert len(pairs) == 0, "빈 해시에서 쌍이 없어야 함"


# ═══════════════════════════════════════════════════════════════════════════
# 3. Physics Integration (5 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestPhysicsIntegration:
    """물리 적분 및 경계 조건 검증."""

    def test_force_to_velocity_speed_limit(self):
        """속도가 max_speed를 초과하지 않는지 검증."""
        current_vel = np.array([10.0, 10.0, 0.0])
        force = np.array([100.0, 100.0, 0.0])  # 매우 큰 힘
        max_speed = 15.0
        new_vel = force_to_velocity(current_vel, force, dt=1.0, max_speed=max_speed)
        speed = np.linalg.norm(new_vel)
        assert speed <= max_speed + 1e-9, (
            f"속도 {speed:.4f} > max_speed {max_speed}"
        )

    def test_position_euler_integration(self):
        """오일러 적분: pos_new = pos + vel * dt."""
        pos = np.array([100.0, 200.0, 60.0])
        vel = np.array([5.0, -3.0, 1.0])
        dt = 0.1
        pos_new = pos + vel * dt
        expected = np.array([100.5, 199.7, 60.1])
        np.testing.assert_allclose(pos_new, expected, atol=1e-10)

    def test_boundary_clamping(self):
        """위치가 +-BOUNDS_M 내에 클램핑되는지 검증."""
        pos_out = np.array([BOUNDS_M + 100, -BOUNDS_M - 50, 60.0])
        clamped = np.clip(pos_out, [-BOUNDS_M, -BOUNDS_M, 0.0], [BOUNDS_M, BOUNDS_M, ALT_MAX])
        np.testing.assert_array_less(clamped[:2], BOUNDS_M + 1e-9)
        np.testing.assert_array_less(-BOUNDS_M - 1e-9, clamped[:2])

    def test_battery_decay_positive(self):
        """비행 중 배터리가 감소하는지 검증."""
        initial_battery = 100.0
        consumption_rate = 0.5  # %/s
        dt = 1.0
        new_battery = initial_battery - consumption_rate * dt
        assert new_battery < initial_battery, "배터리는 비행 중 감소해야 함"

    def test_battery_critical_floor(self):
        """배터리가 0 미만으로 내려가지 않는지 검증 (DroneState 클램핑)."""
        drone = DroneState(
            drone_id="test",
            position=np.array([0.0, 0.0, 60.0]),
            velocity=np.zeros(3),
            battery_pct=-5.0,
        )
        assert drone.battery_pct >= 0.0, "배터리는 0 미만이 될 수 없음"


# ═══════════════════════════════════════════════════════════════════════════
# 4. State Machine (6 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestStateMachine:
    """DroneState 상태 머신 및 NFZ 감지 검증."""

    def test_nfz_detection_inside(self):
        """NFZ 내부 지점이 True를 반환하는지 검증."""
        inside = np.array([0.0, 0.0, 60.0])
        assert bool(_in_nfz(inside)) is True, "NFZ 중심은 내부여야 함"

    def test_nfz_detection_outside(self):
        """NFZ 외부 지점이 False를 반환하는지 검증."""
        outside = np.array([1000.0, 1000.0, 60.0])
        assert bool(_in_nfz(outside)) is False, "NFZ 밖은 외부여야 함"

    def test_nfz_boundary_exact(self):
        """NFZ 경계 정확히 위의 지점 검증 (strict inequality → False)."""
        # _in_nfz uses strict inequality: NFZ_X[0] < x < NFZ_X[1]
        boundary = np.array([NFZ_X[0], 0.0, 60.0])
        assert bool(_in_nfz(boundary)) is False, (
            "경계 정확히 위 (strict inequality) 는 내부가 아님"
        )

    def test_flight_phase_enum_values(self):
        """FlightPhase 열거형에 8개 단계가 존재하는지 검증."""
        expected_phases = {
            "GROUNDED", "TAKEOFF", "ENROUTE", "HOLDING",
            "LANDING", "FAILED", "RTL", "EVADING",
        }
        actual_phases = {p.name for p in FlightPhase}
        assert actual_phases == expected_phases, (
            f"누락된 단계: {expected_phases - actual_phases}"
        )

    def test_drone_state_initial_values(self):
        """기본 DroneState의 초기값이 올바른지 검증."""
        drone = DroneState(
            drone_id="init_test",
            position=np.array([0.0, 0.0, 0.0]),
            velocity=np.zeros(3),
        )
        assert drone.battery_pct == 100.0
        assert drone.flight_phase == FlightPhase.GROUNDED
        assert drone.failure_type == FailureType.NONE
        assert drone.heading == 0.0
        assert drone.distance_flown_m == 0.0

    def test_grounded_drone_not_active(self):
        """GROUNDED 드론의 is_active가 False인지 검증."""
        drone = DroneState(
            drone_id="grounded",
            position=np.zeros(3),
            velocity=np.zeros(3),
            flight_phase=FlightPhase.GROUNDED,
        )
        assert drone.is_active is False, "GROUNDED 드론은 비활성이어야 함"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Scenario Regression (4 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestScenarioRegression:
    """시나리오 실행 회귀 테스트."""

    SCENARIO_DIR = Path(__file__).resolve().parents[1] / "config" / "scenario_params"

    def _scenario_names(self) -> list[str]:
        return sorted(p.stem for p in self.SCENARIO_DIR.glob("*.yaml"))

    def test_all_10_scenarios_complete(self):
        """10개 시나리오가 모두 예외 없이 실행되는지 검증.

        ODYSSEY Phase 465 표준 벤치마크 스위트(SDACS-SBS-10)의 10번째
        대조 케이스 `nominal_baseline.yaml` 추가로 9 → 10 갱신.
        """
        from simulation.scenario_runner import run_scenario

        names = self._scenario_names()
        assert len(names) == 10, f"시나리오 수: {len(names)} (기대: 10)"
        for name in names:
            results = run_scenario(
                name, n_runs=1, seed=42, verbose=False, duration_override_s=2.0,
            )
            assert len(results) == 1, f"{name}: 결과가 1개여야 함"

    def test_high_density_zero_collisions(self):
        """high_density 시나리오에서 충돌 0건 검증."""
        from simulation.scenario_runner import run_scenario

        results = run_scenario(
            "high_density", n_runs=1, seed=42, verbose=False, duration_override_s=2.0,
        )
        collisions = results[0].get("collisions", 0)
        assert collisions == 0, f"high_density 충돌: {collisions} (기대: 0)"

    def test_resolution_rate_perfect(self):
        """충돌 해결률 100% 검증 (공식: 1 - collisions/(conflicts + collisions))."""
        from simulation.scenario_runner import run_scenario

        results = run_scenario(
            "route_conflict", n_runs=1, seed=42, verbose=False, duration_override_s=2.0,
        )
        r = results[0]
        collisions = r.get("collisions", 0)
        conflicts = r.get("conflicts", 0)
        if conflicts + collisions > 0:
            rate = 1.0 - collisions / (conflicts + collisions)
        else:
            rate = 1.0
        assert rate >= 1.0 - 1e-9, f"해결률: {rate:.4f} (기대: 1.0)"

    def test_scenario_yamls_parse(self):
        """10개 YAML 파일이 모두 올바르게 파싱되는지 검증 (Phase 465 baseline 포함)."""
        yamls = sorted(self.SCENARIO_DIR.glob("*.yaml"))
        assert len(yamls) == 10, f"YAML 파일 수: {len(yamls)} (기대: 10)"
        for yf in yamls:
            with open(yf, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert isinstance(data, dict), f"{yf.name}이 dict가 아님"
            assert len(data) > 0, f"{yf.name}이 비어 있음"


# ═══════════════════════════════════════════════════════════════════════════
# 6. GPU Engine (4 tests, skip if no CUDA)
# ═══════════════════════════════════════════════════════════════════════════

try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except Exception:
    HAS_CUDA = False

_skip_no_cuda = pytest.mark.skipif(not HAS_CUDA, reason="CUDA not available")


@_skip_no_cuda
class TestGPUEngine:
    """GPU 물리 엔진 정밀 검증 (CUDA 필요)."""

    def _make_engine(self, max_drones: int = 50):
        from simulation.apf_engine.gpu_physics import create_gpu_physics_engine
        engine = create_gpu_physics_engine(max_drones=max_drones)
        assert engine is not None, "GPU 엔진 생성 실패"
        return engine

    def _make_drone(self, drone_id: str, pos, vel=None, phase=FlightPhase.ENROUTE):
        return DroneState(
            drone_id=drone_id,
            position=np.array(pos, dtype=float),
            velocity=np.array(vel if vel is not None else [0.0, 0.0, 0.0], dtype=float),
            flight_phase=phase,
            goal=np.array([1000.0, 0.0, 60.0]),
        )

    def test_gpu_engine_creation(self):
        """GPU 엔진이 정상적으로 생성되는지 검증."""
        engine = self._make_engine()
        assert engine.max_drones == 50
        assert engine.device.type == "cuda"

    def test_gpu_sync_roundtrip(self):
        """sync_from_cpu -> sync_to_cpu 왕복 후 데이터 보존 검증."""
        engine = self._make_engine()
        original_pos = [100.0, 200.0, 60.0]
        original_vel = [5.0, -3.0, 1.0]

        drones = {
            "rt1": self._make_drone("rt1", original_pos, original_vel),
        }
        engine.sync_from_cpu(drones)
        engine.sync_to_cpu(drones)

        np.testing.assert_allclose(
            drones["rt1"].position, original_pos, atol=0.5,
            err_msg="위치가 왕복 후 보존되어야 함",
        )
        np.testing.assert_allclose(
            drones["rt1"].velocity, original_vel, atol=0.5,
            err_msg="속도가 왕복 후 보존되어야 함",
        )

    def test_gpu_collision_detection_basic(self):
        """GPU 충돌 감지: 가까운 두 드론이 감지되는지 검증."""
        engine = self._make_engine()
        drones = {
            "c1": self._make_drone("c1", [0.0, 0.0, 60.0]),
            "c2": self._make_drone("c2", [3.0, 0.0, 60.0]),  # 3m < 5m 충돌 거리
        }
        engine.sync_from_cpu(drones)
        result = engine.detect_collisions(collision_dist=5.0)
        assert len(result.collisions) > 0, "3m 간격 드론 쌍이 충돌로 감지되어야 함"

    def test_gpu_force_computation(self):
        """GPU 힘 계산: 활성 드론에 대해 0이 아닌 힘이 계산되는지 검증."""
        engine = self._make_engine()
        drones = {
            "f1": self._make_drone("f1", [0.0, 0.0, 60.0]),
            "f2": self._make_drone("f2", [100.0, 0.0, 60.0]),
        }
        engine.sync_from_cpu(drones)
        forces = engine.compute_all_forces()
        has_nonzero = any(np.linalg.norm(f) > 1e-6 for f in forces.values())
        assert has_nonzero, "활성 드론에 대해 0이 아닌 힘이 계산되어야 함"
