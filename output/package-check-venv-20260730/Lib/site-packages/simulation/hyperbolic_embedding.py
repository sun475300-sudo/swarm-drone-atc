# Phase 623: Hyperbolic Embedding — Poincare Disk Model
"""
쌍곡 공간 계층적 드론 네트워크 임베딩:
푸앵카레 디스크 모델, 쌍곡 거리, 계층 탐색.
"""

from dataclasses import dataclass

import numpy as np


def poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    """``poincare_distance`` 동작을 수행한다."""
    diff = np.linalg.norm(u - v) ** 2
    nu = 1 - np.linalg.norm(u) ** 2
    nv = 1 - np.linalg.norm(v) ** 2
    return float(np.arccosh(1 + 2 * diff / (nu * nv + 1e-10)))


@dataclass
class HyperbolicNode:
    """``HyperbolicNode`` 관련 기능을 제공한다."""
    node_id: int
    embedding: np.ndarray  # 2D Poincare disk
    depth: int = 0
    parent: int = -1


class PoincareEmbedding:
    """``PoincareEmbedding`` 관련 기능을 제공한다."""
    def __init__(self, n_nodes=20, seed=42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.n = n_nodes
        self.nodes: list[HyperbolicNode] = []
        self._build_tree()

    def _build_tree(self):
        self.nodes.append(HyperbolicNode(0, np.array([0.0, 0.0]), 0, -1))
        for i in range(1, self.n):
            parent = self.rng.integers(0, i)
            depth = self.nodes[parent].depth + 1
            r = 1 - 1.0 / (depth + 1)
            angle = self.rng.uniform(0, 2 * np.pi)
            emb = np.array([r * np.cos(angle), r * np.sin(angle)]) * 0.9
            self.nodes.append(HyperbolicNode(i, emb, depth, parent))

    def distance(self, i: int, j: int) -> float:
        """``distance`` 동작을 수행한다."""
        return poincare_distance(self.nodes[i].embedding, self.nodes[j].embedding)

    def nearest_neighbors(self, node_id: int, k=3) -> list[int]:
        """``nearest_neighbors`` 동작을 수행한다."""
        dists = [(j, self.distance(node_id, j)) for j in range(self.n) if j != node_id]
        dists.sort(key=lambda x: x[1])
        return [d[0] for d in dists[:k]]


class HyperbolicEmbedding:
    """``HyperbolicEmbedding`` 관련 기능을 제공한다."""
    def __init__(self, n_nodes=20, seed=42):
        """인스턴스를 초기화한다."""
        self.embedding = PoincareEmbedding(n_nodes, seed)
        self.n = n_nodes
        self.steps = 0

    def run(self, steps=50):
        """메인 실행 루프를 수행한다."""
        for _ in range(steps):
            for node in self.embedding.nodes:
                neighbors = self.embedding.nearest_neighbors(node.node_id, 3)
                for _nb in neighbors:
                    pass  # embedding stable after construction
            self.steps += 1

    def summary(self):
        """현재 상태 요약을 반환한다."""
        depths = [n.depth for n in self.embedding.nodes]
        dists = []
        for i in range(self.n):
            for j in range(i+1, self.n):
                dists.append(self.embedding.distance(i, j))
        return {
            "nodes": self.n,
            "max_depth": max(depths),
            "avg_depth": round(float(np.mean(depths)), 2),
            "avg_hyperbolic_dist": round(float(np.mean(dists)), 4),
            "steps": self.steps,
        }


if __name__ == "__main__":
    he = HyperbolicEmbedding(20, 42)
    he.run(50)
    for k, v in he.summary().items():
        print(f"  {k}: {v}")
