# Phase 604: Probabilistic Roadmap (PRM) — Path Planning
"""
확률적 로드맵: 랜덤 샘플링 기반 경로 그래프,
K-nearest neighbor 연결, A* 탐색.
"""

import numpy as np
from dataclasses import dataclass, field
import heapq


@dataclass
class PRMNode:
    node_id: int
    position: np.ndarray
    neighbors: list = field(default_factory=list)


class PRM:
    def __init__(self, bounds=(0, 100, 0, 100), seed=42):
        self.rng = np.random.default_rng(seed)
        self.bounds = bounds
        self.nodes: list[PRMNode] = []
        self.obstacles: list[tuple] = []  # (cx, cy, radius)

    def add_obstacle(self, cx, cy, r):
        self.obstacles.append((cx, cy, r))

    def _collision_free(self, p1: np.ndarray, p2: np.ndarray) -> bool:
        for cx, cy, r in self.obstacles:
            center = np.array([cx, cy])
            d = np.linalg.norm(np.cross(p2 - p1, p1 - center)) / (np.linalg.norm(p2 - p1) + 1e-8)
            if d < r:
                return False
        return True

    def _in_obstacle(self, p: np.ndarray) -> bool:
        for cx, cy, r in self.obstacles:
            if np.linalg.norm(p - np.array([cx, cy])) < r:
                return True
        return False

    def sample(self, n=200):
        xmin, xmax, ymin, ymax = self.bounds
        while len(self.nodes) < n:
            p = np.array([self.rng.uniform(xmin, xmax), self.rng.uniform(ymin, ymax)])
            if not self._in_obstacle(p):
                self.nodes.append(PRMNode(len(self.nodes), p))

    def connect(self, k=6):
        positions = np.array([n.position for n in self.nodes])
        for node in self.nodes:
            dists = np.linalg.norm(positions - node.position, axis=1)
            nearest = np.argsort(dists)[1:k+1]
            for j in nearest:
                if self._collision_free(node.position, self.nodes[j].position):
                    node.neighbors.append(j)

    def a_star(self, start_idx: int, goal_idx: int) -> list[int]:
        open_set = [(0, start_idx)]
        g_score = {start_idx: 0}
        came_from = {}
        goal_pos = self.nodes[goal_idx].position
        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal_idx:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return path[::-1]
            for neighbor in self.nodes[current].neighbors:
                d = np.linalg.norm(self.nodes[current].position - self.nodes[neighbor].position)
                tentative = g_score[current] + d
                if tentative < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    h = np.linalg.norm(self.nodes[neighbor].position - goal_pos)
                    heapq.heappush(open_set, (tentative + h, neighbor))
        return []


class ProbabilisticRoadmap:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.prm = PRM(seed=seed)
        self.paths_found = 0
        self.paths_failed = 0

    def setup(self, n_samples=100, n_obstacles=5):
        for _ in range(n_obstacles):
            self.prm.add_obstacle(
                float(self.rng.uniform(20, 80)),
                float(self.rng.uniform(20, 80)),
                float(self.rng.uniform(3, 8))
            )
        self.prm.sample(n_samples)
        self.prm.connect(6)

    def find_path(self, start_idx=0, goal_idx=-1) -> list[int]:
        if goal_idx < 0:
            goal_idx = len(self.prm.nodes) - 1
        path = self.prm.a_star(start_idx, goal_idx)
        if path:
            self.paths_found += 1
        else:
            self.paths_failed += 1
        return path

    def run(self, n_queries=10):
        self.setup()
        n = len(self.prm.nodes)
        for _ in range(n_queries):
            s = int(self.rng.integers(0, n))
            g = int(self.rng.integers(0, n))
            if s != g:
                self.find_path(s, g)

    def summary(self):
        return {
            "nodes": len(self.prm.nodes),
            "obstacles": len(self.prm.obstacles),
            "paths_found": self.paths_found,
            "paths_failed": self.paths_failed,
            "success_rate": round(self.paths_found / max(self.paths_found + self.paths_failed, 1), 4),
        }


if __name__ == "__main__":
    prm = ProbabilisticRoadmap(42)
    prm.run(10)
    for k, v in prm.summary().items():
        print(f"  {k}: {v}")
