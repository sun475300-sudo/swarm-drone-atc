"""
Multi-agent RL coordinator.
===========================
Coordinates decentralized agent policies with shared reward shaping.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class AgentState:
    q_table: dict[tuple[int, int], float]
    epsilon: float = 0.2


class MARLCoordinator:
    def __init__(
        self,
        n_actions: int = 5,
        learning_rate: float = 0.1,
        gamma: float = 0.95,
        seed: int = 42,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self.n_actions = n_actions
        self.lr = learning_rate
        self.gamma = gamma
        self._agents: dict[str, AgentState] = {}
        self._experiences: list[tuple[str, int, int, float, int, bool]] = []
        self._episodes = 0

    def register_agent(self, agent_id: str, epsilon: float = 0.2) -> None:
        self._agents[agent_id] = AgentState(q_table={}, epsilon=float(np.clip(epsilon, 0.01, 1.0)))

    def _q(self, agent_id: str, state: int, action: int) -> float:
        return self._agents[agent_id].q_table.get((state, action), 0.0)

    def select_actions(self, states: dict[str, int]) -> dict[str, int]:
        actions: dict[str, int] = {}
        for agent_id, state in states.items():
            if agent_id not in self._agents:
                self.register_agent(agent_id)
            agent = self._agents[agent_id]

            if self._rng.random() < agent.epsilon:
                action = int(self._rng.integers(0, self.n_actions))
            else:
                q_vals = [self._q(agent_id, state, a) for a in range(self.n_actions)]
                action = int(np.argmax(q_vals))
            actions[agent_id] = action
        return actions

    def store_step(
        self,
        transitions: dict[str, tuple[int, int, float, int, bool]],
        shared_reward: float = 0.0,
    ) -> None:
        for agent_id, (state, action, reward, next_state, done) in transitions.items():
            r = float(reward) + float(shared_reward)
            self._experiences.append((agent_id, state, action, r, next_state, done))
            if done:
                self._episodes += 1

    def train_step(self, batch_size: int = 32) -> float:
        if not self._experiences:
            return 0.0

        idx = self._rng.choice(len(self._experiences), size=min(batch_size, len(self._experiences)), replace=False)
        batch = [self._experiences[i] for i in idx]

        td_errors: list[float] = []
        for agent_id, state, action, reward, next_state, done in batch:
            if agent_id not in self._agents:
                self.register_agent(agent_id)
            agent = self._agents[agent_id]
            q_sa = agent.q_table.get((state, action), 0.0)
            next_max = max(agent.q_table.get((next_state, a), 0.0) for a in range(self.n_actions))
            target = reward if done else reward + self.gamma * next_max
            td = target - q_sa
            agent.q_table[(state, action)] = q_sa + self.lr * td
            td_errors.append(td)

            agent.epsilon = max(0.02, agent.epsilon * 0.999)

        return float(np.mean(np.square(td_errors))) if td_errors else 0.0

    def policy_snapshot(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for aid, agent in self._agents.items():
            out[aid] = {
                "states": float(len({s for s, _ in agent.q_table.keys()})),
                "epsilon": round(agent.epsilon, 6),
            }
        return out

    def summary(self) -> dict[str, Any]:
        return {
            "agents": len(self._agents),
            "experiences": len(self._experiences),
            "episodes": self._episodes,
        }
