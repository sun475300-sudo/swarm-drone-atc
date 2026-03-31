# Phase 601: Swarm Topology Control — Dynamic Graph Rewiring
"""
동적 토폴로지 제어: 그래프 리와이어링,
연결성 유지, 스몰월드 최적화.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class TopologyMetrics:
    connectivity: float
    avg_degree: float
    diameter: int
    clustering: float


class DynamicTopology:
    """동적 통신 토폴로지."""

    def __init__(self, n_nodes: int, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_nodes
        self.adj = np.zeros((n_nodes, n_nodes))
        self.positions = self.rng.uniform(0, 100, (n_nodes, 2))
        self.comm_range = 40.0

    def build_range_graph(self):
        for i in range(self.n):
            for j in range(i + 1, self.n):
                d = np.linalg.norm(self.positions[i] - self.positions[j])
                if d <= self.comm_range:
                    self.adj[i, j] = self.adj[j, i] = 1

    def rewire(self, p=0.1):
        edges = [(i, j) for i in range(self.n) for j in range(i+1, self.n) if self.adj[i, j] > 0]
        for i, j in edges:
            if self.rng.random() < p:
                self.adj[i, j] = self.adj[j, i] = 0
                k = int(self.rng.integers(0, self.n))
                while k == i or self.adj[i, k] > 0:
                    k = int(self.rng.integers(0, self.n))
                self.adj[i, k] = self.adj[k, i] = 1

    def is_connected(self) -> bool:
        visited = set()
        stack = [0]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            neighbors = np.where(self.adj[node] > 0)[0]
            stack.extend(neighbors)
        return len(visited) == self.n

    def avg_degree(self) -> float:
        return float(self.adj.sum() / self.n)

    def clustering_coeff(self) -> float:
        cc = 0.0
        for i in range(self.n):
            neighbors = np.where(self.adj[i] > 0)[0]
            k = len(neighbors)
            if k < 2:
                continue
            links = sum(1 for a in neighbors for b in neighbors if a < b and self.adj[a, b] > 0)
            cc += 2 * links / (k * (k - 1))
        return cc / self.n

    def metrics(self) -> TopologyMetrics:
        return TopologyMetrics(
            connectivity=1.0 if self.is_connected() else 0.0,
            avg_degree=round(self.avg_degree(), 2),
            diameter=0,
            clustering=round(self.clustering_coeff(), 4)
        )


class SwarmTopologyControl:
    def __init__(self, n_nodes=20, seed=42):
        self.topo = DynamicTopology(n_nodes, seed)
        self.topo.build_range_graph()
        self.history: list[TopologyMetrics] = []
        self.rewire_count = 0

    def run(self, steps=10, rewire_p=0.1):
        for _ in range(steps):
            self.topo.rewire(rewire_p)
            self.history.append(self.topo.metrics())
            self.rewire_count += 1

    def summary(self):
        return {
            "nodes": self.topo.n,
            "rewires": self.rewire_count,
            "connected": self.topo.is_connected(),
            "avg_degree": round(self.topo.avg_degree(), 2),
            "clustering": round(self.topo.clustering_coeff(), 4),
        }


if __name__ == "__main__":
    stc = SwarmTopologyControl(20, 42)
    stc.run(10)
    for k, v in stc.summary().items():
        print(f"  {k}: {v}")
