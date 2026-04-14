"""
PPO 기반 강화학습 충돌 회피 에이전트

Actor-Critic 구조의 PPO 알고리즘으로 드론 충돌 회피 정책을 학습한다.
외부 의존성 없이 PyTorch만 사용하여 구현.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Normal

# ─── 상수 ───────────────────────────────────────────────
OBS_DIM = 18          # 관측 차원: 자기위치(3)+속도(3)+목표(3)+이웃상대위치(9)
ACT_DIM = 3           # 행동 차원: 속도 변화 [dx, dy, dz]
COLLISION_DIST = 5.0  # 충돌 판정 거리 (m)
WARNING_DIST = 15.0   # 근접 경고 거리 (m)
GOAL_DIST = 3.0       # 목표 도달 판정 거리 (m)
MAX_STEPS = 200       # 에피소드 최대 스텝
NUM_NEIGHBORS = 3     # 관측할 이웃 수
ARENA_SIZE = 100.0    # 환경 크기 (m)


@dataclass
class StepResult:
    """환경 스텝 결과 (불변)"""
    obs: np.ndarray
    reward: float
    done: bool


# ─── 환경 ───────────────────────────────────────────────
class DroneEnv:
    """단일 드론 충돌 회피 환경 (gym-like, gym 의존성 없음)"""

    def __init__(self, n_neighbors: int = NUM_NEIGHBORS, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._n_neighbors = n_neighbors
        self._pos = np.zeros(3)
        self._vel = np.zeros(3)
        self._goal = np.zeros(3)
        self._neighbors: np.ndarray = np.zeros((n_neighbors, 3))
        self._step_count = 0

    def reset(self) -> np.ndarray:
        """환경 초기화, 초기 관측 반환"""
        self._pos = self._rng.uniform(-ARENA_SIZE, ARENA_SIZE, size=3)
        self._vel = np.zeros(3)
        self._goal = self._rng.uniform(-ARENA_SIZE, ARENA_SIZE, size=3)
        self._neighbors = self._rng.uniform(
            -ARENA_SIZE, ARENA_SIZE, size=(self._n_neighbors, 3)
        )
        self._step_count = 0
        return self._build_obs()

    def step(self, action: np.ndarray) -> StepResult:
        """행동 적용 후 결과 반환"""
        # 행동 클리핑 (-1 ~ 1)
        action = np.clip(action, -1.0, 1.0)
        self._vel = np.clip(self._vel + action, -5.0, 5.0)
        self._pos = self._pos + self._vel * 0.1  # dt=0.1s
        self._step_count += 1

        # 이웃 드론 랜덤 이동 (간단한 시뮬레이션)
        self._neighbors = self._neighbors + self._rng.normal(0, 0.5, self._neighbors.shape)

        reward, done = self._compute_reward()
        return StepResult(obs=self._build_obs(), reward=reward, done=done)

    def _build_obs(self) -> np.ndarray:
        """18차원 관측 벡터 구성"""
        # 가장 가까운 이웃의 상대 위치
        rel_positions = self._neighbors - self._pos
        distances = np.linalg.norm(rel_positions, axis=1)
        sorted_idx = np.argsort(distances)[:self._n_neighbors]
        nearest_rel = rel_positions[sorted_idx].flatten()

        goal_rel = self._goal - self._pos
        return np.concatenate([self._pos, self._vel, goal_rel, nearest_rel]).astype(np.float32)

    def _compute_reward(self) -> Tuple[float, bool]:
        """보상 및 종료 조건 계산"""
        dist_to_goal = float(np.linalg.norm(self._goal - self._pos))
        rel_positions = self._neighbors - self._pos
        min_neighbor_dist = float(np.min(np.linalg.norm(rel_positions, axis=1)))

        # 충돌
        if min_neighbor_dist < COLLISION_DIST:
            return -10.0, True

        # 목표 도달
        if dist_to_goal < GOAL_DIST:
            return 10.0, True

        # 시간 초과
        if self._step_count >= MAX_STEPS:
            return -1.0, True

        # 단계 보상
        reward = -0.01  # 시간 패널티
        reward += max(0.0, 1.0 - dist_to_goal / ARENA_SIZE)  # 목표 접근 보상 (0~1)
        if min_neighbor_dist < WARNING_DIST:
            reward -= 5.0  # 근접 경고

        return reward, False


# ─── 네트워크 ───────────────────────────────────────────
class ActorCritic(nn.Module):
    """Actor-Critic MLP 네트워크"""

    def __init__(self, obs_dim: int = OBS_DIM, act_dim: int = ACT_DIM) -> None:
        super().__init__()
        # Actor: 정책 네트워크
        self.actor_net = nn.Sequential(
            nn.Linear(obs_dim, 128), nn.Tanh(),
            nn.Linear(128, 64), nn.Tanh(),
        )
        self.actor_mean = nn.Linear(64, act_dim)
        self.actor_log_std = nn.Parameter(torch.zeros(act_dim))

        # Critic: 가치 네트워크
        self.critic_net = nn.Sequential(
            nn.Linear(obs_dim, 128), nn.Tanh(),
            nn.Linear(128, 64), nn.Tanh(),
            nn.Linear(64, 1),
        )

    def forward(self, obs: torch.Tensor) -> Tuple[Normal, torch.Tensor]:
        """관측 → (행동 분포, 상태 가치)"""
        h = self.actor_net(obs)
        mean = torch.tanh(self.actor_mean(h))  # -1 ~ 1 범위
        std = self.actor_log_std.exp().expand_as(mean)
        dist = Normal(mean, std)
        value = self.critic_net(obs)
        return dist, value


# ─── PPO 에이전트 ───────────────────────────────────────
@dataclass
class RolloutBuffer:
    """롤아웃 데이터 버퍼"""
    obs: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    rewards: list = field(default_factory=list)
    dones: list = field(default_factory=list)
    log_probs: list = field(default_factory=list)
    values: list = field(default_factory=list)

    def clear(self) -> None:
        for lst in [self.obs, self.actions, self.rewards,
                    self.dones, self.log_probs, self.values]:
            lst.clear()


class PPOAgent:
    """PPO 강화학습 에이전트"""

    def __init__(
        self,
        lr: float = 3e-4,
        gamma: float = 0.99,
        lam: float = 0.95,
        clip_eps: float = 0.2,
        epochs: int = 10,
        seed: int = 42,
    ) -> None:
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._gamma = gamma
        self._lam = lam
        self._clip_eps = clip_eps
        self._epochs = epochs

        torch.manual_seed(seed)
        self._net = ActorCritic().to(self._device)
        self._optimizer = torch.optim.Adam(self._net.parameters(), lr=lr)
        self._buffer = RolloutBuffer()

    def select_action(self, obs: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """관측에서 행동 선택, (행동, 로그확률, 가치) 반환"""
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=self._device).unsqueeze(0)
        with torch.no_grad():
            dist, value = self._net(obs_t)
        action = dist.sample()
        log_prob = dist.log_prob(action).sum(dim=-1)
        return (
            action.squeeze(0).cpu().numpy(),
            float(log_prob.item()),
            float(value.item()),
        )

    def collect_rollout(self, env: DroneEnv) -> float:
        """한 에피소드 롤아웃 수집, 총 보상 반환"""
        obs = env.reset()
        total_reward = 0.0
        done = False

        while not done:
            action, log_prob, value = self.select_action(obs)
            result = env.step(action)

            self._buffer.obs.append(obs)
            self._buffer.actions.append(action)
            self._buffer.rewards.append(result.reward)
            self._buffer.dones.append(result.done)
            self._buffer.log_probs.append(log_prob)
            self._buffer.values.append(value)

            obs = result.obs
            done = result.done
            total_reward += result.reward

        return total_reward

    def _compute_gae(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """GAE(Generalized Advantage Estimation) 계산"""
        rewards = self._buffer.rewards
        values = self._buffer.values
        dones = self._buffer.dones
        n = len(rewards)

        advantages = np.zeros(n, dtype=np.float32)
        last_gae = 0.0
        for t in reversed(range(n)):
            next_value = 0.0 if t == n - 1 else values[t + 1]
            next_non_terminal = 0.0 if dones[t] else 1.0
            delta = rewards[t] + self._gamma * next_value * next_non_terminal - values[t]
            last_gae = delta + self._gamma * self._lam * next_non_terminal * last_gae
            advantages[t] = last_gae

        returns = advantages + np.array(values, dtype=np.float32)
        adv_t = torch.as_tensor(advantages, device=self._device)
        ret_t = torch.as_tensor(returns, device=self._device)
        return adv_t, ret_t

    def update(self) -> float:
        """PPO 정책 업데이트, 평균 손실 반환"""
        if len(self._buffer.obs) == 0:
            return 0.0

        adv, returns = self._compute_gae()
        # 어드밴티지 정규화
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)

        obs_t = torch.as_tensor(np.array(self._buffer.obs), dtype=torch.float32, device=self._device)
        act_t = torch.as_tensor(np.array(self._buffer.actions), dtype=torch.float32, device=self._device)
        old_log_probs = torch.as_tensor(np.array(self._buffer.log_probs), dtype=torch.float32, device=self._device)

        total_loss = 0.0
        for _ in range(self._epochs):
            dist, values = self._net(obs_t)
            new_log_probs = dist.log_prob(act_t).sum(dim=-1)
            ratio = (new_log_probs - old_log_probs).exp()

            # PPO 클리핑
            surr1 = ratio * adv
            surr2 = torch.clamp(ratio, 1.0 - self._clip_eps, 1.0 + self._clip_eps) * adv
            policy_loss = -torch.min(surr1, surr2).mean()

            value_loss = 0.5 * (returns - values.squeeze(-1)).pow(2).mean()
            entropy_bonus = -0.01 * dist.entropy().mean()

            loss = policy_loss + value_loss + entropy_bonus
            self._optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(self._net.parameters(), 0.5)
            self._optimizer.step()
            total_loss += loss.item()

        self._buffer.clear()
        return total_loss / self._epochs

    def train(self, n_episodes: int = 100, seed: int = 42) -> list[float]:
        """학습 루프, 에피소드별 보상 리스트 반환"""
        env = DroneEnv(seed=seed)
        episode_rewards: list[float] = []

        for ep in range(n_episodes):
            reward = self.collect_rollout(env)
            loss = self.update()
            episode_rewards.append(reward)

            if (ep + 1) % 10 == 0:
                avg = np.mean(episode_rewards[-10:])
                print(f"[에피소드 {ep + 1}/{n_episodes}] 보상: {reward:.2f}, "
                      f"최근10 평균: {avg:.2f}, 손실: {loss:.4f}, "
                      f"장치: {self._device}")

        return episode_rewards


if __name__ == "__main__":
    print("=== PPO 충돌 회피 에이전트 학습 시작 ===")
    agent = PPOAgent(seed=42)
    rewards = agent.train(n_episodes=100)
    print(f"\n=== 학습 완료 ===")
    print(f"최종 10 에피소드 평균 보상: {np.mean(rewards[-10:]):.2f}")
