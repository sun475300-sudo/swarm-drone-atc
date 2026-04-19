# Phase 601: Swarm Topology Control — Graph Rewiring
"""
토폴로지 제어: 그래프 리와이어링,
대수적 연결도 최적화, 적응형 네트워크.
"""

import numpy as np
from dataclasses import dataclass


class TopologyManager:
    def __init__(self, n_agents=15, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_agents
        self.adj = np.zeros((n_agents, n_agents))
        self._init_ring()
        self.rewire_count = 0

    def _init_ring(self):
        for i in range(self.n):
            j = (i + 1) % self.n
            self.adj[i, j] = 1
            self.adj[j, i] = 1

    def algebraic_connectivity(self) -> float:
        D = np.diag(self.adj.sum(axis=1))
        L = D - self.adj
        eigvals = np.linalg.eigvalsh(L)
        sorted_eig = np.sort(eigvals)
        return float(sorted_eig[1]) if len(sorted_eig) > 1 else 0.0

    def rewire_step(self, p_rewire=0.1):
        for i in range(self.n):
            for j in range(i + 1, self.n):
                if self.adj[i, j] == 1 and self.rng.random() < p_rewire:
                    k = self.rng.integers(0, self.n)
                    while k == i or self.adj[i, k] == 1:
                        k = self.rng.integers(0, self.n)
                    self.adj[i, j] = 0
                    self.adj[j, i] = 0
                    self.adj[i, k] = 1
                    self.adj[k, i] = 1
                    self.rewire_count += 1

    def add_shortcut(self):
        i, j = self.rng.integers(0, self.n, 2)
        while i == j or self.adj[i, j] == 1:
            i, j = self.rng.integers(0, self.n, 2)
        self.adj[i, j] = 1
        self.adj[j, i] = 1


class SwarmTopologyControl:
    def __init__(self, n_agents=15, seed=42):
        self.manager = TopologyManager(n_agents, seed)
        self.steps = 0
        self.connectivity_history: list[float] = []

    def run(self, steps=50):
        for _ in range(steps):
            self.manager.rewire_step()
            if self.steps % 10 == 0:
                self.manager.add_shortcut()
            self.connectivity_history.append(self.manager.algebraic_connectivity())
            self.steps += 1

    def summary(self):
        return {
            "agents": self.manager.n,
            "steps": self.steps,
            "rewires": self.manager.rewire_count,
            "edges": int(self.manager.adj.sum() / 2),
            "final_connectivity": round(self.connectivity_history[-1], 4) if self.connectivity_history else 0,
        }


if __name__ == "__main__":
    stc = SwarmTopologyControl(15, 42)
    stc.run(50)
    for k, v in stc.summary().items():
        print(f"  {k}: {v}")
