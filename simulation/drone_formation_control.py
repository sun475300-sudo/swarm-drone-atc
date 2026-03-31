# Phase 605: Drone Formation Control — Graph Laplacian Consensus
"""
합의 기반 대형 제어: 그래프 라플라시안,
리더-팔로워, 대형 유지/전환.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class FormationPattern:
    name: str
    offsets: np.ndarray  # (N, 2) relative to leader


class ConsensusController:
    def __init__(self, n_agents: int, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_agents
        self.positions = self.rng.uniform(-20, 20, (n_agents, 2))
        self.velocities = np.zeros((n_agents, 2))
        self.adj = np.ones((n_agents, n_agents)) - np.eye(n_agents)
        self.leader_idx = 0

    def laplacian(self) -> np.ndarray:
        D = np.diag(self.adj.sum(axis=1))
        return D - self.adj

    def consensus_step(self, target_offsets: np.ndarray, dt=0.1, gain=1.0):
        L = self.laplacian()
        leader_pos = self.positions[self.leader_idx]
        for i in range(self.n):
            if i == self.leader_idx:
                continue
            target = leader_pos + target_offsets[i]
            error = target - self.positions[i]
            consensus_force = np.zeros(2)
            for j in range(self.n):
                if self.adj[i, j] > 0:
                    consensus_force += self.adj[i, j] * (self.positions[j] - self.positions[i])
            self.velocities[i] = gain * error + 0.3 * consensus_force
            self.positions[i] += self.velocities[i] * dt

    def formation_error(self, target_offsets: np.ndarray) -> float:
        leader_pos = self.positions[self.leader_idx]
        errors = []
        for i in range(self.n):
            if i == self.leader_idx:
                continue
            target = leader_pos + target_offsets[i]
            errors.append(np.linalg.norm(self.positions[i] - target))
        return float(np.mean(errors))


class DroneFormationControl:
    def __init__(self, n_drones=10, seed=42):
        self.rng = np.random.default_rng(seed)
        self.controller = ConsensusController(n_drones, seed)
        self.n = n_drones
        self.patterns = self._make_patterns()
        self.current_pattern = "V"
        self.steps = 0
        self.error_history: list[float] = []

    def _make_patterns(self) -> dict[str, FormationPattern]:
        n = self.n
        v_offsets = np.zeros((n, 2))
        for i in range(n):
            row = i // 2
            side = 1 if i % 2 == 0 else -1
            v_offsets[i] = [row * -5, side * row * 3]

        line_offsets = np.zeros((n, 2))
        for i in range(n):
            line_offsets[i] = [0, (i - n // 2) * 5]

        circle_offsets = np.zeros((n, 2))
        for i in range(n):
            angle = 2 * np.pi * i / n
            circle_offsets[i] = [np.cos(angle) * 15, np.sin(angle) * 15]

        return {
            "V": FormationPattern("V", v_offsets),
            "line": FormationPattern("line", line_offsets),
            "circle": FormationPattern("circle", circle_offsets),
        }

    def step(self):
        pattern = self.patterns[self.current_pattern]
        self.controller.consensus_step(pattern.offsets)
        err = self.controller.formation_error(pattern.offsets)
        self.error_history.append(err)
        self.steps += 1

    def run(self, steps=100):
        for _ in range(steps):
            self.step()

    def switch_formation(self, name: str):
        if name in self.patterns:
            self.current_pattern = name

    def summary(self):
        return {
            "drones": self.n,
            "formation": self.current_pattern,
            "steps": self.steps,
            "final_error": round(self.error_history[-1], 4) if self.error_history else 0,
            "min_error": round(min(self.error_history), 4) if self.error_history else 0,
            "converged": self.error_history[-1] < 1.0 if self.error_history else False,
        }


if __name__ == "__main__":
    dfc = DroneFormationControl(10, 42)
    dfc.run(100)
    for k, v in dfc.summary().items():
        print(f"  {k}: {v}")
