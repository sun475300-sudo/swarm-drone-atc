"""
심층 강화학습 컨트롤러
====================
DQN 기반 충돌 회피 정책 학습.

사용법:
    drl = DeepRLController(state_dim=8, n_actions=5, seed=42)
    action = drl.select_action(state=[100,200,50,10,0,0,0.8,90])
    drl.store_transition(state, action, reward=-0.1, next_state, done=False)
    loss = drl.train_step(batch_size=32)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class Transition:
    state: list[float]
    action: int
    reward: float
    next_state: list[float]
    done: bool


class ReplayBuffer:
    def __init__(self, capacity: int = 10000, seed: int = 42) -> None:
        self._buffer: list[Transition] = []
        self._capacity = capacity
        self._rng = np.random.default_rng(seed)

    def push(self, t: Transition) -> None:
        if len(self._buffer) >= self._capacity:
            self._buffer.pop(0)
        self._buffer.append(t)

    def sample(self, batch_size: int) -> list[Transition]:
        indices = self._rng.choice(len(self._buffer), size=min(batch_size, len(self._buffer)), replace=False)
        return [self._buffer[i] for i in indices]

    def __len__(self) -> int:
        return len(self._buffer)


class SimpleQNetwork:
    """간이 Q-네트워크 (NumPy 기반, 2-layer)"""
    def __init__(self, state_dim: int, n_actions: int, hidden: int = 64, seed: int = 42) -> None:
        rng = np.random.default_rng(seed)
        self.w1 = rng.normal(0, 0.1, (state_dim, hidden))
        self.b1 = np.zeros(hidden)
        self.w2 = rng.normal(0, 0.1, (hidden, n_actions))
        self.b2 = np.zeros(n_actions)

    def forward(self, state: np.ndarray) -> np.ndarray:
        h = np.maximum(0, state @ self.w1 + self.b1)  # ReLU
        return h @ self.w2 + self.b2

    def copy_from(self, other: SimpleQNetwork) -> None:
        self.w1 = other.w1.copy()
        self.b1 = other.b1.copy()
        self.w2 = other.w2.copy()
        self.b2 = other.b2.copy()


class DeepRLController:
    def __init__(self, state_dim: int = 8, n_actions: int = 5,
                 lr: float = 0.001, gamma: float = 0.99,
                 epsilon: float = 1.0, epsilon_min: float = 0.05,
                 epsilon_decay: float = 0.995, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self.state_dim = state_dim
        self.n_actions = n_actions
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        self._q_net = SimpleQNetwork(state_dim, n_actions, seed=seed)
        self._target_net = SimpleQNetwork(state_dim, n_actions, seed=seed + 1)
        self._target_net.copy_from(self._q_net)

        self._buffer = ReplayBuffer(capacity=10000, seed=seed)
        self._steps = 0
        self._episodes = 0
        self._total_reward = 0.0
        self._losses: list[float] = []
        self._target_update_freq = 100

    def select_action(self, state: list[float]) -> int:
        self._steps += 1
        if self._rng.random() < self.epsilon:
            return int(self._rng.integers(0, self.n_actions))
        q_values = self._q_net.forward(np.array(state, dtype=np.float64))
        return int(np.argmax(q_values))

    def store_transition(self, state: list[float], action: int,
                         reward: float, next_state: list[float],
                         done: bool = False) -> None:
        self._buffer.push(Transition(state, action, reward, next_state, done))
        self._total_reward += reward
        if done:
            self._episodes += 1
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def train_step(self, batch_size: int = 32) -> float:
        if len(self._buffer) < batch_size:
            return 0.0

        batch = self._buffer.sample(batch_size)
        states = np.array([t.state for t in batch])
        actions = np.array([t.action for t in batch])
        rewards = np.array([t.reward for t in batch])
        next_states = np.array([t.next_state for t in batch])
        dones = np.array([t.done for t in batch], dtype=np.float64)

        # Q(s, a) 현재
        q_values = self._q_net.forward(states)
        q_selected = q_values[np.arange(batch_size), actions]

        # Q_target(s', a') 최대
        q_next = self._target_net.forward(next_states)
        q_target = rewards + self.gamma * np.max(q_next, axis=1) * (1 - dones)

        # TD 오차
        td_error = q_target - q_selected
        loss = float(np.mean(td_error ** 2))

        # 간이 업데이트 (수동 역전파)
        # output layer gradient
        dq = np.zeros_like(q_values)
        dq[np.arange(batch_size), actions] = -2 * td_error / batch_size

        h = np.maximum(0, states @ self._q_net.w1 + self._q_net.b1)
        dw2 = h.T @ dq
        db2 = dq.sum(axis=0)

        dh = dq @ self._q_net.w2.T
        dh[h <= 0] = 0  # ReLU gradient
        dw1 = states.T @ dh
        db1 = dh.sum(axis=0)

        self._q_net.w2 -= self.lr * dw2
        self._q_net.b2 -= self.lr * db2
        self._q_net.w1 -= self.lr * dw1
        self._q_net.b1 -= self.lr * db1

        self._losses.append(loss)

        # 타겟 네트워크 업데이트
        if self._steps % self._target_update_freq == 0:
            self._target_net.copy_from(self._q_net)

        return loss

    def summary(self) -> dict[str, Any]:
        return {
            "steps": self._steps,
            "episodes": self._episodes,
            "epsilon": round(self.epsilon, 4),
            "buffer_size": len(self._buffer),
            "avg_loss": round(float(np.mean(self._losses[-100:])), 6) if self._losses else 0,
            "total_reward": round(self._total_reward, 2),
        }
