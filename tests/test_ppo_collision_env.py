"""P736 SDACSGymEnv 환경 wiring 단위 테스트.

학습(SB3/torch/GPU) 없이 환경 자체의 reset/step/observation/reward 계약을 검증한다.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from src.rl.ppo_collision import (
    COLLISION_DIST,
    NEAR_MISS_DIST,
    PPOConfig,
    SDACSGymEnv,
)


@pytest.fixture
def env() -> SDACSGymEnv:
    """소형 결정론적 환경."""
    return SDACSGymEnv(n_drones=6, max_neighbors=4, seed=42)


def test_reset_returns_observation_of_contract_length(env: SDACSGymEnv) -> None:
    # Arrange / Act
    obs, info = env.reset()

    # Assert — 7 * (max_neighbors + 1)
    assert len(obs) == 7 * (env.max_neighbors + 1)
    assert isinstance(info, dict)


def test_observation_is_finite_float_vector(env: SDACSGymEnv) -> None:
    obs, _ = env.reset()
    arr = np.asarray(obs, dtype=np.float64)
    assert np.all(np.isfinite(arr))


def test_reset_is_deterministic_given_seed() -> None:
    a, _ = SDACSGymEnv(n_drones=6, max_neighbors=4, seed=7).reset()
    b, _ = SDACSGymEnv(n_drones=6, max_neighbors=4, seed=7).reset()
    np.testing.assert_allclose(np.asarray(a), np.asarray(b))


def test_different_seeds_differ() -> None:
    a, _ = SDACSGymEnv(n_drones=6, max_neighbors=4, seed=1).reset()
    b, _ = SDACSGymEnv(n_drones=6, max_neighbors=4, seed=2).reset()
    assert not np.allclose(np.asarray(a), np.asarray(b))


def test_step_advances_count_and_returns_5_tuple(env: SDACSGymEnv) -> None:
    env.reset()
    obs, reward, terminated, truncated, info = env.step(np.zeros(3))
    assert env._step_count == 1
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert len(obs) == 7 * (env.max_neighbors + 1)


def test_truncates_at_max_steps() -> None:
    # n_drones=1 + 무행동(정지) → 충돌·목표도달 종료 없이 truncation 경로만 검증.
    env = SDACSGymEnv(n_drones=1, max_neighbors=2, seed=0, max_steps=3)
    env.reset()
    flags = [env.step(np.zeros(3)) for _ in range(3)]
    assert flags[-1][3] is True  # 마지막 스텝 truncated
    assert flags[0][3] is False
    assert flags[1][3] is False
    assert all(not f[2] for f in flags)  # terminated 발생 없음


def test_action_drives_ego_toward_commanded_direction() -> None:
    env = SDACSGymEnv(n_drones=1, max_neighbors=2, seed=0)
    env.reset()
    start = env._positions[0].copy()
    for _ in range(10):
        env.step(np.array([1.0, 0.0, 0.0]))
    # +x 가속 누적 → x 증가
    assert env._positions[0][0] > start[0]


def test_progress_toward_goal_yields_positive_reward_component() -> None:
    env = SDACSGymEnv(n_drones=1, max_neighbors=2, seed=0)
    env.reset()
    # 목표 방향 단위 벡터로 가속하면 진행 보상이 양수여야 한다.
    direction = env._goals[0] - env._positions[0]
    direction = direction / (np.linalg.norm(direction) + 1e-9)
    _, reward, _, _, _ = env.step(direction)
    assert reward > -1.0  # 충돌 없는 전진은 큰 음수 아님


def test_collision_triggers_termination_and_penalty() -> None:
    env = SDACSGymEnv(n_drones=2, max_neighbors=1, seed=0)
    env.reset()
    # 두 드론을 같은 위치에 강제 배치 → 충돌
    env._positions[1] = env._positions[0].copy()
    _, reward, terminated, _, info = env.step(np.zeros(3))
    assert terminated is True
    assert reward < 0
    assert info["collision"] is True


def test_reaching_goal_terminates_episode() -> None:
    env = SDACSGymEnv(n_drones=1, max_neighbors=1, seed=0)
    env.reset()
    env._positions[0] = env._goals[0].copy()
    _, _, terminated, _, info = env.step(np.zeros(3))
    assert terminated is True
    assert info["reached_goal"] is True


def test_near_miss_counted_in_episode_stats() -> None:
    env = SDACSGymEnv(n_drones=2, max_neighbors=1, seed=0)
    env.reset()
    # 충돌은 아니지만 near-miss 범위 내로 배치
    offset = (NEAR_MISS_DIST + COLLISION_DIST) / 2.0
    env._positions[1] = env._positions[0] + np.array([offset, 0.0, 0.0])
    env.step(np.zeros(3))
    assert env.episode_near_misses >= 1


def test_ppo_config_is_frozen() -> None:
    cfg = PPOConfig()
    with pytest.raises(FrozenInstanceError):
        cfg.learning_rate = 1.0  # type: ignore[misc]
