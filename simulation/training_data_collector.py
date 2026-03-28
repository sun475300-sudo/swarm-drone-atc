"""
학습 데이터 수집
===============
시뮬레이션 경험 → 구조화된 학습 데이터셋 생성.

사용법:
    tdc = TrainingDataCollector()
    tdc.record_state(state={"pos": (100,200,50)}, action="TURN_LEFT", reward=5.0)
    dataset = tdc.export_dataset()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Experience:
    """경험 데이터"""
    state: dict[str, Any]
    action: str
    reward: float
    next_state: dict[str, Any] | None = None
    done: bool = False
    t: float = 0.0


class TrainingDataCollector:
    """학습 데이터 수집."""

    def __init__(self, max_buffer: int = 10000) -> None:
        self.max_buffer = max_buffer
        self._buffer: list[Experience] = []
        self._episode_boundaries: list[int] = []
        self._total_collected = 0

    def record_state(
        self, state: dict[str, Any], action: str,
        reward: float = 0.0, next_state: dict[str, Any] | None = None,
        done: bool = False, t: float = 0.0,
    ) -> None:
        exp = Experience(
            state=state, action=action, reward=reward,
            next_state=next_state, done=done, t=t,
        )
        self._buffer.append(exp)
        self._total_collected += 1

        if done:
            self._episode_boundaries.append(len(self._buffer))

        if len(self._buffer) > self.max_buffer:
            self._buffer = self._buffer[-self.max_buffer:]

    def mark_episode_end(self) -> None:
        if self._buffer:
            self._buffer[-1].done = True
            self._episode_boundaries.append(len(self._buffer))

    def export_dataset(self) -> list[dict[str, Any]]:
        return [
            {
                "state": e.state,
                "action": e.action,
                "reward": e.reward,
                "next_state": e.next_state,
                "done": e.done,
            }
            for e in self._buffer
        ]

    def sample_batch(self, batch_size: int = 32) -> list[Experience]:
        if len(self._buffer) < batch_size:
            return list(self._buffer)
        rng = np.random.default_rng()
        indices = rng.choice(len(self._buffer), size=batch_size, replace=False)
        return [self._buffer[i] for i in indices]

    def action_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for e in self._buffer:
            dist[e.action] = dist.get(e.action, 0) + 1
        return dist

    def reward_stats(self) -> dict[str, float]:
        if not self._buffer:
            return {"mean": 0, "std": 0, "min": 0, "max": 0}
        rewards = [e.reward for e in self._buffer]
        return {
            "mean": round(float(np.mean(rewards)), 3),
            "std": round(float(np.std(rewards)), 3),
            "min": round(float(np.min(rewards)), 3),
            "max": round(float(np.max(rewards)), 3),
        }

    def episode_count(self) -> int:
        return len(self._episode_boundaries)

    def summary(self) -> dict[str, Any]:
        return {
            "buffer_size": len(self._buffer),
            "total_collected": self._total_collected,
            "episodes": self.episode_count(),
            "actions": len(self.action_distribution()),
            "reward_stats": self.reward_stats(),
        }
