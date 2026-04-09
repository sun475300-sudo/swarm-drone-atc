# Phase 590: Drone Social Network — Trust & Influence Propagation
"""
드론 소셜 네트워크: 신뢰 그래프,
영향력 전파, 평판 시스템, 커뮤니티 탐지.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class DroneAgent:
    agent_id: int
    trust_scores: dict = field(default_factory=dict)  # {peer_id: score}
    reputation: float = 0.5
    influence: float = 0.0
    community: int = -1


class TrustGraph:
    """신뢰 그래프."""

    def __init__(self, n_nodes: int, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_nodes
        self.adjacency = np.zeros((n_nodes, n_nodes))
        self.trust = np.ones((n_nodes, n_nodes)) * 0.5

    def connect(self, i: int, j: int, trust_val: float = 0.5):
        self.adjacency[i, j] = 1
        self.adjacency[j, i] = 1
        self.trust[i, j] = trust_val
        self.trust[j, i] = trust_val

    def random_connect(self, p=0.3):
        for i in range(self.n):
            for j in range(i + 1, self.n):
                if self.rng.random() < p:
                    trust = float(self.rng.uniform(0.3, 0.9))
                    self.connect(i, j, trust)

    def propagate_trust(self, iterations=10, decay=0.8):
        for _ in range(iterations):
            new_trust = self.trust.copy()
            for i in range(self.n):
                neighbors = np.where(self.adjacency[i] > 0)[0]
                for j in range(self.n):
                    if i == j or self.adjacency[i, j] > 0:
                        continue
                    # 이웃을 통한 간접 신뢰
                    indirect = 0.0
                    count = 0
                    for k in neighbors:
                        if self.adjacency[k, j] > 0:
                            indirect += self.trust[i, k] * self.trust[k, j]
                            count += 1
                    if count > 0:
                        new_trust[i, j] = max(new_trust[i, j], decay * indirect / count)
            self.trust = new_trust

    def pagerank(self, damping=0.85, iterations=20) -> np.ndarray:
        n = self.n
        rank = np.ones(n) / n
        degree = self.adjacency.sum(axis=1)
        degree[degree == 0] = 1
        for _ in range(iterations):
            new_rank = (1 - damping) / n
            for i in range(n):
                neighbors = np.where(self.adjacency[:, i] > 0)[0]
                for j in neighbors:
                    new_rank += damping * rank[j] / degree[j]
                rank[i] = new_rank
        return rank / rank.sum()

    def community_detect(self, n_communities=3) -> np.ndarray:
        """간이 스펙트럴 클러스터링."""
        degree = np.diag(self.adjacency.sum(axis=1))
        laplacian = degree - self.adjacency
        eigvals, eigvecs = np.linalg.eigh(laplacian)
        features = eigvecs[:, 1:n_communities + 1]
        # K-means 간이
        centers = features[self.rng.choice(self.n, n_communities, replace=False)]
        labels = np.zeros(self.n, dtype=int)
        for _ in range(10):
            for i in range(self.n):
                dists = [np.linalg.norm(features[i] - c) for c in centers]
                labels[i] = int(np.argmin(dists))
            for c in range(n_communities):
                mask = labels == c
                if mask.any():
                    centers[c] = features[mask].mean(axis=0)
        return labels


class DroneSocialNetwork:
    """드론 소셜 네트워크 시뮬레이션."""

    def __init__(self, n_drones=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.graph = TrustGraph(n_drones, seed)
        self.agents = [DroneAgent(i) for i in range(n_drones)]
        self.n = n_drones

    def build_network(self, connectivity=0.3):
        self.graph.random_connect(connectivity)

    def propagate(self, iterations=10):
        self.graph.propagate_trust(iterations)
        ranks = self.graph.pagerank()
        labels = self.graph.community_detect(3)
        for i, a in enumerate(self.agents):
            a.influence = float(ranks[i])
            a.community = int(labels[i])
            neighbors = np.where(self.graph.adjacency[i] > 0)[0]
            a.reputation = float(np.mean(self.graph.trust[neighbors, i])) if len(neighbors) > 0 else 0.5

    def run(self):
        self.build_network()
        self.propagate()

    def summary(self):
        edges = int(self.graph.adjacency.sum() / 2)
        communities = len(set(a.community for a in self.agents))
        return {
            "drones": self.n,
            "edges": edges,
            "communities": communities,
            "avg_trust": round(float(np.mean(self.graph.trust[self.graph.adjacency > 0])), 4),
            "avg_reputation": round(float(np.mean([a.reputation for a in self.agents])), 4),
            "max_influence": round(max(a.influence for a in self.agents), 4),
        }


if __name__ == "__main__":
    dsn = DroneSocialNetwork(20, 42)
    dsn.run()
    for k, v in dsn.summary().items():
        print(f"  {k}: {v}")
