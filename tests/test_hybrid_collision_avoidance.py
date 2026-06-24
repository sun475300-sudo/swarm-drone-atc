"""GENESIS Phase 362: Hybrid Collision Avoidance 테스트.

pytest 기반 단위 테스트 — SimPy 프로세스 미사용.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.autonomy.hybrid_collision_avoidance import (
    DEFAULT_MAX_FORCE,
    EpisodeResult,
    HybridAction,
    HybridCollisionAvoidance,
    HybridConfig,
    _attractive_force,
    _repulsive_force,
)


# ============================================================
# HybridConfig 검증
# ============================================================


class TestHybridConfig:
    """HybridConfig frozen dataclass 검증."""

    def test_default_config_valid(self) -> None:
        """기본 설정은 유효해야 한다."""
        cfg = HybridConfig()
        assert cfg.apf_weight == 0.7
        assert cfg.rl_weight == 0.3
        assert cfg.safety_override_dist_m == 5.0
        assert cfg.rl_action_scale == 2.0

    def test_weights_must_sum_to_one(self) -> None:
        """가중치 합이 1.0이 아니면 ValueError."""
        with pytest.raises(ValueError, match="가중치 합이 1.0"):
            HybridConfig(apf_weight=0.5, rl_weight=0.3)

    def test_negative_apf_weight_raises(self) -> None:
        """음수 APF 가중치는 ValueError."""
        with pytest.raises(ValueError, match="가중치는 0 이상"):
            HybridConfig(apf_weight=-0.1, rl_weight=1.1)

    def test_negative_rl_weight_raises(self) -> None:
        """음수 RL 가중치는 ValueError."""
        with pytest.raises(ValueError, match="가중치는 0 이상"):
            HybridConfig(apf_weight=1.1, rl_weight=-0.1)

    def test_zero_safety_dist_raises(self) -> None:
        """safety_override_dist_m=0 은 ValueError."""
        with pytest.raises(ValueError, match="양수여야 합니다"):
            HybridConfig(safety_override_dist_m=0.0)

    def test_negative_safety_dist_raises(self) -> None:
        """음수 safety_override_dist_m 은 ValueError."""
        with pytest.raises(ValueError, match="양수여야 합니다"):
            HybridConfig(safety_override_dist_m=-1.0)

    def test_config_is_frozen(self) -> None:
        """frozen dataclass는 수정 불가."""
        cfg = HybridConfig()
        with pytest.raises(AttributeError):
            cfg.apf_weight = 0.5  # type: ignore[misc]


# ============================================================
# APF-only 모드
# ============================================================


class TestAPFOnlyMode:
    """RL action이 None일 때 APF 단독 동작."""

    def test_apf_only_when_no_rl_action(self) -> None:
        """rl_action=None → mode='apf_only'."""
        hca = HybridCollisionAvoidance()
        result = hca.compute(
            drone_pos=np.array([0.0, 0.0, 0.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([50.0, 0.0, 0.0]),
            neighbor_positions=[],
            neighbor_velocities=[],
            rl_action=None,
        )
        assert result.mode == "apf_only"
        assert result.blend_ratio == 1.0
        assert result.rl_contribution == (0.0, 0.0, 0.0)

    def test_apf_only_produces_nonzero_force_toward_goal(self) -> None:
        """목표가 있으면 그 방향으로 힘 발생."""
        hca = HybridCollisionAvoidance()
        result = hca.compute(
            drone_pos=np.array([0.0, 0.0, 0.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([50.0, 0.0, 0.0]),
            neighbor_positions=[],
            neighbor_velocities=[],
        )
        assert result.force[0] > 0  # x 방향 인력


# ============================================================
# Safety Override 모드
# ============================================================


class TestSafetyOverride:
    """이웃이 safety_override_dist_m 이내일 때 APF 100% 제어."""

    def test_safety_override_activates_when_close(self) -> None:
        """이웃이 4m 거리 → safety_override (기본 임계: 5m)."""
        hca = HybridCollisionAvoidance()
        result = hca.compute(
            drone_pos=np.array([0.0, 0.0, 0.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([50.0, 0.0, 0.0]),
            neighbor_positions=[np.array([4.0, 0.0, 0.0])],
            neighbor_velocities=[np.zeros(3)],
            rl_action=np.array([1.0, 0.0, 0.0]),
        )
        assert result.mode == "safety_override"
        assert result.blend_ratio == 1.0

    def test_safety_override_ignores_rl(self) -> None:
        """safety override 시 RL 기여가 총 합력에 반영되지 않는다."""
        hca = HybridCollisionAvoidance()
        # RL이 목표와 반대(음의 x)로 큰 행동 제안
        result = hca.compute(
            drone_pos=np.array([0.0, 0.0, 0.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([50.0, 0.0, 0.0]),
            neighbor_positions=[np.array([3.0, 0.0, 0.0])],
            neighbor_velocities=[np.zeros(3)],
            rl_action=np.array([-1.0, -1.0, -1.0]),
        )
        # force == APF contribution (after clamping)
        assert result.mode == "safety_override"
        # rl_contribution은 계산되지만 블렌딩에 반영 안 됨
        assert result.blend_ratio == 1.0


# ============================================================
# Hybrid 블렌딩 모드
# ============================================================


class TestHybridBlending:
    """정상 거리에서 APF + RL 블렌딩."""

    def test_hybrid_mode_when_neighbors_far(self) -> None:
        """이웃이 충분히 멀면 hybrid 모드."""
        hca = HybridCollisionAvoidance()
        result = hca.compute(
            drone_pos=np.array([0.0, 0.0, 0.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([50.0, 0.0, 0.0]),
            neighbor_positions=[np.array([30.0, 30.0, 0.0])],
            neighbor_velocities=[np.zeros(3)],
            rl_action=np.array([0.5, 0.0, 0.0]),
        )
        assert result.mode == "hybrid"
        assert result.blend_ratio == 0.7

    def test_hybrid_blending_with_known_values(self) -> None:
        """알려진 입력으로 블렌딩 수식 검증."""
        cfg = HybridConfig(apf_weight=0.6, rl_weight=0.4, safety_override_dist_m=2.0)
        hca = HybridCollisionAvoidance(config=cfg)

        # 이웃 없이 순수 인력 + RL 블렌딩
        result = hca.compute(
            drone_pos=np.array([0.0, 0.0, 0.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([5.0, 0.0, 0.0]),  # 근거리 → 이차 인력
            neighbor_positions=[],
            neighbor_velocities=[],
            rl_action=np.array([1.0, 0.0, 0.0]),
        )
        assert result.mode == "hybrid"

        # APF 인력: k_att * diff = 1.0 * [5,0,0] = [5,0,0]
        # RL: clip(1.0)*scale(2.0) = [2,0,0]
        # 블렌딩: 0.6*[5,0,0] + 0.4*[2,0,0] = [3.8, 0, 0]
        assert abs(result.force[0] - 3.8) < 1e-6
        assert abs(result.force[1]) < 1e-6
        assert abs(result.force[2]) < 1e-6


# ============================================================
# Force Clamping
# ============================================================


class TestForceClamping:
    """최대 합력 클램핑 검증."""

    def test_force_clamped_to_max(self) -> None:
        """큰 힘이 DEFAULT_MAX_FORCE로 클램프된다."""
        hca = HybridCollisionAvoidance()
        # 매우 가까운 이웃 → 큰 척력
        result = hca.compute(
            drone_pos=np.array([0.0, 0.0, 0.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([100.0, 0.0, 0.0]),
            neighbor_positions=[np.array([0.5, 0.0, 0.0])],
            neighbor_velocities=[np.zeros(3)],
            rl_action=None,
        )
        force_mag = np.linalg.norm(result.force)
        assert force_mag <= DEFAULT_MAX_FORCE + 1e-9

    def test_small_force_not_clamped(self) -> None:
        """작은 힘은 클램핑 없이 유지된다."""
        hca = HybridCollisionAvoidance()
        result = hca.compute(
            drone_pos=np.array([0.0, 0.0, 0.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([5.0, 0.0, 0.0]),
            neighbor_positions=[],
            neighbor_velocities=[],
            rl_action=None,
        )
        force_mag = np.linalg.norm(result.force)
        # k_att * diff = [5,0,0] → mag=5 < max_force=10
        assert force_mag < DEFAULT_MAX_FORCE


# ============================================================
# Episode Evaluation
# ============================================================


class TestEpisodeEvaluation:
    """에피소드 평가 메서드 검증."""

    def test_determinism_same_seed(self) -> None:
        """동일 시드 → 동일 결과."""
        hca = HybridCollisionAvoidance()
        r1 = hca.evaluate_episode(n_drones=5, n_steps=50, seed=123)
        r2 = hca.evaluate_episode(n_drones=5, n_steps=50, seed=123)
        assert r1 == r2

    def test_different_seed_different_result(self) -> None:
        """다른 시드 → 다른 결과 (높은 확률)."""
        hca = HybridCollisionAvoidance()
        r1 = hca.evaluate_episode(n_drones=10, n_steps=100, seed=1)
        r2 = hca.evaluate_episode(n_drones=10, n_steps=100, seed=999)
        # mean_min_dist가 다를 확률이 매우 높음
        assert r1.mean_min_dist_m != r2.mean_min_dist_m

    def test_episode_result_is_frozen(self) -> None:
        """EpisodeResult는 frozen dataclass."""
        hca = HybridCollisionAvoidance()
        result = hca.evaluate_episode(n_drones=3, n_steps=10, seed=42)
        with pytest.raises(AttributeError):
            result.collisions = 999  # type: ignore[misc]

    def test_episode_with_rl_actions(self) -> None:
        """RL 행동 시퀀스를 제공하면 safety_override가 발동할 수 있다."""
        hca = HybridCollisionAvoidance()
        rng = np.random.default_rng(42)
        rl_actions = rng.uniform(-1, 1, size=(100, 3))
        result = hca.evaluate_episode(
            n_drones=10, n_steps=100, seed=42, rl_actions=rl_actions
        )
        assert isinstance(result, EpisodeResult)
        assert result.total_steps > 0
        assert result.total_steps <= 100

    def test_episode_apf_only_no_safety_override(self) -> None:
        """APF 단독(rl_actions=None)에서도 에피소드가 정상 완료된다."""
        hca = HybridCollisionAvoidance()
        result = hca.evaluate_episode(n_drones=5, n_steps=50, seed=7)
        assert isinstance(result, EpisodeResult)
        # APF only → safety_override는 RL 미사용 시 발동 안 함
        assert result.safety_overrides == 0


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    """엣지 케이스 처리 검증."""

    def test_no_neighbors(self) -> None:
        """이웃 없을 때 min_neighbor_dist_m은 inf."""
        hca = HybridCollisionAvoidance()
        result = hca.compute(
            drone_pos=np.zeros(3),
            drone_vel=np.zeros(3),
            goal_pos=np.array([10.0, 0.0, 0.0]),
            neighbor_positions=[],
            neighbor_velocities=[],
            rl_action=np.array([0.5, 0.0, 0.0]),
        )
        assert result.min_neighbor_dist_m == float("inf")
        # 이웃 없으면 override 불가 → hybrid
        assert result.mode == "hybrid"

    def test_single_neighbor(self) -> None:
        """이웃 1대일 때 정상 동작."""
        hca = HybridCollisionAvoidance()
        result = hca.compute(
            drone_pos=np.zeros(3),
            drone_vel=np.zeros(3),
            goal_pos=np.array([50.0, 0.0, 0.0]),
            neighbor_positions=[np.array([20.0, 0.0, 0.0])],
            neighbor_velocities=[np.zeros(3)],
        )
        assert result.min_neighbor_dist_m == pytest.approx(20.0)

    def test_goal_at_current_position(self) -> None:
        """목표가 현재 위치와 동일하면 인력 0."""
        hca = HybridCollisionAvoidance()
        result = hca.compute(
            drone_pos=np.array([10.0, 10.0, 10.0]),
            drone_vel=np.zeros(3),
            goal_pos=np.array([10.0, 10.0, 10.0]),
            neighbor_positions=[],
            neighbor_velocities=[],
        )
        # 인력 0 + 이웃 없음 → 합력 0
        assert np.allclose(result.force, (0.0, 0.0, 0.0), atol=1e-9)

    def test_episode_single_drone(self) -> None:
        """드론 1대(자기만) 에피소드 — 충돌/니어미스 불가."""
        hca = HybridCollisionAvoidance()
        result = hca.evaluate_episode(n_drones=1, n_steps=50, seed=42)
        assert result.collisions == 0
        assert result.near_misses == 0
        assert result.mean_min_dist_m == float("inf")


# ============================================================
# Internal APF Functions
# ============================================================


class TestAPFFunctions:
    """내부 APF 함수 단위 테스트."""

    def test_attractive_force_direction(self) -> None:
        """인력은 목표 방향."""
        force = _attractive_force(np.zeros(3), np.array([10.0, 0.0, 0.0]))
        assert force[0] > 0
        assert abs(force[1]) < 1e-9
        assert abs(force[2]) < 1e-9

    def test_repulsive_force_pushes_away(self) -> None:
        """척력은 타 드론 반대 방향."""
        force = _repulsive_force(
            np.zeros(3),
            np.array([5.0, 0.0, 0.0]),
            np.zeros(3),
            np.zeros(3),
        )
        # 자기(0,0,0)에서 타(5,0,0) → 반대 방향 = 음의 x
        assert force[0] < 0

    def test_repulsive_force_zero_beyond_d0(self) -> None:
        """영향 거리(d0) 밖에서는 척력 0."""
        force = _repulsive_force(
            np.zeros(3),
            np.array([60.0, 0.0, 0.0]),  # d0=50 밖
            np.zeros(3),
            np.zeros(3),
        )
        assert np.allclose(force, 0.0)
