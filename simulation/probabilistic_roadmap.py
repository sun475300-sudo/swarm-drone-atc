# Phase 604: Probabilistic Roadmap — PRM + A*
"""
확률적 로드맵: 샘플링 기반 경로 계획,
PRM 그래프 구축, A* 검색.
"""

import numpy as np
from dataclasses import dataclass
import heapq


class PRMGraph:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.nodes: list[np.ndarray] = []
        self.edges: dict[int, list[tuple[int, float]]] = {}

    def build(self, n_samples: int, x_range: tuple, y_range: tuple, k_neighbors=5):
        for _ in range(n_samples):
            x = self.rng.uniform(x_range[0], x_range[1])
            y = self.rng.uniform(y_range[0], y_range[1])
            self.nodes.append(np.array([x, y]))
        for i in range(len(self.nodes)):
            self.edges[i] = []
        for i in range(len(self.nodes)):
            dists = [(j, np.linalg.norm(self.nodes[i] - self.nodes[j]))
                     for j in range(len(self.nodes)) if j != i]
            dists.sort(key=lambda x: x[1])
            for j, d in dists[:k_neighbors]:
                self.edges[i].append((j, d))
                if i not in [e[0] for e in self.edges[j]]:
                    self.edges[j].append((i, d))

    def _nearest(self, point: np.ndarray) -> int:
        dists = [np.linalg.norm(n - point) for n in self.nodes]
        return int(np.argmin(dists))

    def query(self, start: np.ndarray, goal: np.ndarray) -> list[np.ndarray] | None:
        s_idx = self._nearest(start)
        g_idx = self._nearest(goal)
        # A*
        open_set = [(0.0, s_idx)]
        came_from: dict[int, int] = {}
        g_score = {s_idx: 0.0}
        while open_set:
            _, current = heapq.heappop(open_set)
            if current == g_idx:
                path = [self.nodes[current]]
                while current in came_from:
                    current = came_from[current]
                    path.append(self.nodes[current])
                return list(reversed(path))
            for neighbor, cost in self.edges.get(current, []):
                tentative = g_score[current] + cost
                if tentative < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    h = np.linalg.norm(self.nodes[neighbor] - self.nodes[g_idx])
                    heapq.heappush(open_set, (tentative + h, neighbor))
        return None


class ProbabilisticRoadmapPlanner:
    def __init__(self, n_samples=100, seed=42):
        self.graph = PRMGraph(seed)
        self.n_samples = n_samples
        self.path: list[np.ndarray] | None = None
        self.start = np.array([5.0, 5.0])
        self.goal = np.array([95.0, 95.0])

    def run(self):
        self.graph.build(self.n_samples, (0, 100), (0, 100))
        self.path = self.graph.query(self.start, self.goal)

    def summary(self):
        path_len = 0.0
        if self.path and len(self.path) > 1:
            for i in range(len(self.path) - 1):
                path_len += np.linalg.norm(self.path[i + 1] - self.path[i])
        return {
            "nodes": len(self.graph.nodes),
            "edges": sum(len(v) for v in self.graph.edges.values()) // 2,
            "path_found": self.path is not None,
            "path_length": round(path_len, 2),
            "path_waypoints": len(self.path) if self.path else 0,
        }


if __name__ == "__main__":
    prm = ProbabilisticRoadmapPlanner(100, 42)
    prm.run()
    for k, v in prm.summary().items():
        print(f"  {k}: {v}")
