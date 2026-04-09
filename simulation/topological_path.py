# Phase 629: Topological Path Planning — Persistent Homology
"""
위상 데이터 분석 기반 경로 계획:
퍼시스턴트 호몰로지, 베티 수, 장애물 위상 분류.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class SimplexPair:
    birth: float
    death: float
    dimension: int

    @property
    def persistence(self) -> float:
        return self.death - self.birth


class RipsComplex:
    def __init__(self, points: np.ndarray, max_radius=20.0):
        self.points = points
        self.n = len(points)
        self.max_radius = max_radius
        self.pairs: list[SimplexPair] = []

    def compute_persistence(self, n_steps=20):
        self.pairs = []
        prev_components = 0
        prev_cycles = 0
        for step in range(1, n_steps + 1):
            radius = self.max_radius * step / n_steps
            adj = np.zeros((self.n, self.n), dtype=bool)
            for i in range(self.n):
                for j in range(i+1, self.n):
                    if np.linalg.norm(self.points[i] - self.points[j]) < radius:
                        adj[i, j] = True
                        adj[j, i] = True

            n_components = self._count_components(adj)
            n_cycles = self._count_cycles(adj)

            if step > 1:
                if n_components < prev_components:
                    self.pairs.append(SimplexPair(
                        birth=self.max_radius * (step-1) / n_steps,
                        death=radius,
                        dimension=0
                    ))
                if n_cycles > prev_cycles:
                    self.pairs.append(SimplexPair(
                        birth=radius,
                        death=self.max_radius,
                        dimension=1
                    ))
            prev_components = n_components
            prev_cycles = n_cycles

    def _count_components(self, adj: np.ndarray) -> int:
        visited = set()
        components = 0
        for i in range(self.n):
            if i not in visited:
                components += 1
                stack = [i]
                while stack:
                    node = stack.pop()
                    if node in visited:
                        continue
                    visited.add(node)
                    for j in range(self.n):
                        if adj[node, j] and j not in visited:
                            stack.append(j)
        return components

    def _count_cycles(self, adj: np.ndarray) -> int:
        edges = sum(adj[i, j] for i in range(self.n) for j in range(i+1, self.n))
        components = self._count_components(adj)
        return int(edges - self.n + components)

    def betti_numbers(self) -> dict[int, int]:
        b0 = sum(1 for p in self.pairs if p.dimension == 0)
        b1 = sum(1 for p in self.pairs if p.dimension == 1)
        return {0: b0, 1: b1}


class TopologicalPathPlanner:
    def __init__(self, n_obstacles=15, seed=42):
        self.rng = np.random.default_rng(seed)
        self.obstacles = self.rng.uniform(10, 90, (n_obstacles, 2))
        self.complex = RipsComplex(self.obstacles, 25.0)
        self.complex.compute_persistence()

    def run(self):
        pass  # analysis on demand

    def find_path_homotopy_class(self, start: np.ndarray, goal: np.ndarray) -> int:
        betti = self.complex.betti_numbers()
        return betti.get(1, 0) + 1

    def summary(self):
        betti = self.complex.betti_numbers()
        persistences = [p.persistence for p in self.complex.pairs]
        return {
            "obstacles": len(self.obstacles),
            "betti_0": betti.get(0, 0),
            "betti_1": betti.get(1, 0),
            "total_pairs": len(self.complex.pairs),
            "avg_persistence": round(float(np.mean(persistences)), 4) if persistences else 0,
            "homotopy_classes": self.find_path_homotopy_class(np.zeros(2), np.ones(2) * 100),
        }


if __name__ == "__main__":
    tp = TopologicalPathPlanner(15, 42)
    tp.run()
    for k, v in tp.summary().items():
        print(f"  {k}: {v}")
