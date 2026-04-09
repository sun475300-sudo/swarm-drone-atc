"""
MCTS 경로 탐색
=============
몬테카를로 트리 탐색 경로 계획 + UCB1.

사용법:
    mp = MCTSPlanner(seed=42)
    path = mp.plan(start=(0,0,50), goal=(1000,1000,50), n_iterations=100)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class MCTSNode:
    position: tuple[float, float, float]
    visits: int = 0
    total_reward: float = 0.0
    children: list[int] = field(default_factory=list)
    parent: int | None = None


class MCTSPlanner:
    def __init__(self, step_size: float = 100, n_actions: int = 6, seed: int = 42) -> None:
        self.step_size = step_size
        self.n_actions = n_actions
        self._rng = np.random.default_rng(seed)
        self._nodes: list[MCTSNode] = []
        self._plans: int = 0

    def _ucb1(self, node: MCTSNode, parent_visits: int, c: float = 1.41) -> float:
        if node.visits == 0:
            return float("inf")
        return node.total_reward / node.visits + c * np.sqrt(np.log(parent_visits) / node.visits)

    def _actions(self) -> list[tuple[float, float, float]]:
        return [(self.step_size, 0, 0), (-self.step_size, 0, 0),
                (0, self.step_size, 0), (0, -self.step_size, 0),
                (0, 0, 20), (0, 0, -20)]

    def _dist(self, a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
        return float(np.sqrt(sum((ai-bi)**2 for ai, bi in zip(a, b))))

    def plan(self, start: tuple[float, float, float], goal: tuple[float, float, float], n_iterations: int = 100) -> list[tuple[float, float, float]]:
        self._nodes = [MCTSNode(position=start)]
        actions = self._actions()

        for _ in range(n_iterations):
            # Select
            idx = 0
            node = self._nodes[idx]
            while node.children and node.visits > 0:
                best_child = max(node.children, key=lambda c: self._ucb1(self._nodes[c], node.visits))
                idx = best_child
                node = self._nodes[idx]

            # Expand
            if len(node.children) < len(actions):
                for a in actions:
                    new_pos = tuple(p + d for p, d in zip(node.position, a))
                    new_pos = (new_pos[0], new_pos[1], max(30, new_pos[2]))
                    child_idx = len(self._nodes)
                    self._nodes.append(MCTSNode(position=new_pos, parent=idx))
                    node.children.append(child_idx)

            # Simulate (rollout)
            sim_pos = node.position
            for _ in range(10):
                action = actions[self._rng.integers(len(actions))]
                sim_pos = tuple(p + d for p, d in zip(sim_pos, action))
            reward = -self._dist(sim_pos, goal) / 1000

            # Backpropagate
            current = idx
            while current is not None:
                self._nodes[current].visits += 1
                self._nodes[current].total_reward += reward
                current = self._nodes[current].parent

        # Extract best path
        path = [start]
        idx = 0
        for _ in range(20):
            node = self._nodes[idx]
            if not node.children:
                break
            best = max(node.children, key=lambda c: self._nodes[c].visits)
            path.append(self._nodes[best].position)
            idx = best
            if self._dist(self._nodes[best].position, goal) < self.step_size:
                break
        path.append(goal)
        self._plans += 1
        return path

    def summary(self) -> dict[str, Any]:
        return {"plans": self._plans, "tree_size": len(self._nodes)}
