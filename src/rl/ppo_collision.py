"""P736: PPO 기반 충돌 회피 정책 학습 — Stable-Baselines3 wrapper.

규칙 기반 APF·CBS와 동등 안전성 + 25% 효율 개선 검증 목표.

실행:
    python -m src.rl.ppo_collision train --steps 50000 --output models/ppo_v1.zip
    python -m src.rl.ppo_collision eval --model models/ppo_v1.zip --scenarios 10

의존성: stable-baselines3, gymnasium, torch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PPOConfig:
    """PPO 학습 하이퍼파라미터."""

    learning_rate: float = 3e-4
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.0
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5


@dataclass
class TrainingStats:
    """학습 통계 추적."""

    total_timesteps: int = 0
    episodes: int = 0
    mean_reward: float = 0.0
    near_miss_rate: float = 0.0
    collision_rate: float = 0.0
    rewards_history: list[float] = field(default_factory=list)


class SDACSGymEnv:
    """SwarmSimulator를 Gym 환경으로 wrap.

    Observation: 자기·이웃 N대의 [x, y, z, vx, vy, vz, phase_onehot]
    Action: [ax, ay, az] continuous (-1, 1) → APF 대체 가속도
    Reward: -(near_miss + 10·collision) + 0.1·progress
    """

    def __init__(self, scenario: str = "default", n_drones: int = 50, max_neighbors: int = 8) -> None:
        """SDACSGymEnv 인스턴스를 초기화한다."""
        self.scenario = scenario
        self.n_drones = n_drones
        self.max_neighbors = max_neighbors
        self._step_count = 0
        # TODO: SwarmSimulator(scenario_cfg={'drones':{'default_count':n_drones}}) 초기화

    def reset(self) -> tuple[Any, dict[str, Any]]:
        """환경을 초기 상태로 리셋."""
        self._step_count = 0
        # TODO: simulator._spawn_drones() + 초기 observation 생성
        obs = self._build_observation()
        return obs, {}

    def step(self, action: Any) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        """한 스텝 진행 + reward 계산."""
        self._step_count += 1
        # TODO: action을 APF 대체 가속도로 환경에 적용
        reward = self._compute_reward()
        terminated = False
        truncated = self._step_count >= 1000
        return self._build_observation(), reward, terminated, truncated, {}

    def _build_observation(self) -> Any:
        """현재 상태로부터 observation 벡터 생성."""
        # TODO: drones[i] + KDTree 이웃 N대 상태를 평탄화
        return [0.0] * (7 * (self.max_neighbors + 1))

    def _compute_reward(self) -> float:
        """near_miss · collision · progress 가중합."""
        # TODO: simulator.controller stats 활용
        return 0.0


def train(cfg: PPOConfig, env: SDACSGymEnv, total_timesteps: int = 50_000) -> TrainingStats:
    """PPO 정책 학습 + 통계 반환."""
    stats = TrainingStats()
    try:
        from stable_baselines3 import PPO  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("stable-baselines3 필요: pip install stable-baselines3") from e

    model = PPO(
        "MlpPolicy",
        env=env,
        learning_rate=cfg.learning_rate,
        n_steps=cfg.n_steps,
        batch_size=cfg.batch_size,
        n_epochs=cfg.n_epochs,
        gamma=cfg.gamma,
        gae_lambda=cfg.gae_lambda,
        clip_range=cfg.clip_range,
        ent_coef=cfg.ent_coef,
        vf_coef=cfg.vf_coef,
        max_grad_norm=cfg.max_grad_norm,
        verbose=1,
    )
    model.learn(total_timesteps=total_timesteps)
    stats.total_timesteps = total_timesteps
    return stats


def evaluate(model_path: str, scenarios: int = 10, seeds: int = 5) -> dict[str, float]:
    """학습된 모델을 N 시나리오 × M seed로 평가."""
    # TODO: SB3 model load → SDACSGymEnv 평가 루프
    # NMR/MSD/AU 메트릭 반환 (P705 활용)
    return {"NMR": 0.0, "MSD": 0.0, "AU": 0.0, "FT": 0.0}
