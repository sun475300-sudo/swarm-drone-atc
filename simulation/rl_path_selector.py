"""
강화학습 기반 경로 선택
=======================
Q-테이블 기반 경로 선택 + 보상 함수 + 탐색/활용.

사용법:
    rl = RLPathSelector(n_actions=4)
    action = rl.select_action("state_1")
    rl.update("state_1", action, reward=10.0, next_state="state_2")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Episode:
    """에피소드 기록"""
    states: list[str] = field(default_factory=list)
    actions: list[int] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)
    total_reward: float = 0.0


class RLPathSelector:
    """Q-테이블 기반 경로 선택."""

    def __init__(
        self, n_actions: int = 4,
        alpha: float = 0.1, gamma: float = 0.95,
        epsilon: float = 0.2, epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01, seed: int = 42,
    ) -> None:
        self.n_actions = n_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self._rng = np.random.default_rng(seed)
        self._q: dict[str, np.ndarray] = {}
        self._episodes: list[Episode] = []
        self._current: Episode | None = None
        self._total_updates = 0

    def _get_q(self, state: str) -> np.ndarray:
        if state not in self._q:
            self._q[state] = np.zeros(self.n_actions)
        return self._q[state]

    def select_action(self, state: str) -> int:
        """epsilon-greedy 행동 선택"""
        if self._rng.random() < self.epsilon:
            return int(self._rng.integers(0, self.n_actions))
        q = self._get_q(state)
        return int(np.argmax(q))

    def update(self, state: str, action: int, reward: float, next_state: str) -> None:
        """Q-러닝 업데이트"""
        q = self._get_q(state)
        q_next = self._get_q(next_state)
        q[action] += self.alpha * (reward + self.gamma * np.max(q_next) - q[action])
        self._total_updates += 1

        if self._current:
            self._current.states.append(state)
            self._current.actions.append(action)
            self._current.rewards.append(reward)
            self._current.total_reward += reward

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def start_episode(self) -> None:
        self._current = Episode()

    def end_episode(self) -> None:
        if self._current:
            self._episodes.append(self._current)
            self._current = None
            self.decay_epsilon()

    def best_action(self, state: str) -> int:
        """탐색 없이 최적 행동"""
        return int(np.argmax(self._get_q(state)))

    def q_value(self, state: str, action: int) -> float:
        return float(self._get_q(state)[action])

    def episode_rewards(self) -> list[float]:
        return [e.total_reward for e in self._episodes]

    def average_reward(self, last_n: int = 10) -> float:
        rewards = self.episode_rewards()
        if not rewards:
            return 0.0
        return float(np.mean(rewards[-last_n:]))

    def summary(self) -> dict[str, Any]:
        return {
            "states": len(self._q),
            "episodes": len(self._episodes),
            "total_updates": self._total_updates,
            "epsilon": round(self.epsilon, 4),
            "avg_reward": round(self.average_reward(), 2),
        }
