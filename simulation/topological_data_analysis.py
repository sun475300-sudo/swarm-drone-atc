# Phase 548: Topological Data Analysis — Persistent Homology
"""
위상 데이터 분석: Vietoris-Rips 복합체, 지속적 호몰로지,
Betti 수로 군집 대형의 위상적 특성 분석.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Simplex:
    vertices: tuple
    birth: float
    death: float = float('inf')
    dimension: int = 0


@dataclass
class PersistenceInterval:
    dimension: int
    birth: float
    death: float
    persistence: float


@dataclass
class TopologicalFeatures:
    betti_0: int  # 연결 성분 수
    betti_1: int  # 루프 수
    betti_2: int  # 공동(void) 수
    total_persistence: float


class VietorisRips:
    """Vietoris-Rips 복합체 구성."""

    def __init__(self, max_dim=2):
        self.max_dim = max_dim
        self.simplices: list[Simplex] = []

    def build(self, points: np.ndarray, max_radius=50.0, n_steps=20):
        n = len(points)
        # 거리 행렬
        dist = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                dist[i, j] = dist[j, i] = np.linalg.norm(points[i] - points[j])

        # 0-simplices (점)
        for i in range(n):
            self.simplices.append(Simplex((i,), 0.0, dimension=0))

        # 반경 증가하면서 simplex 추가
        radii = np.linspace(0, max_radius, n_steps)
        for r in radii:
            # 1-simplices (엣지)
            for i in range(n):
                for j in range(i + 1, n):
                    if dist[i, j] <= r:
                        existing = any(s.vertices == (i, j) for s in self.simplices if s.dimension == 1)
                        if not existing:
                            self.simplices.append(Simplex((i, j), dist[i, j], dimension=1))

            # 2-simplices (삼각형)
            if self.max_dim >= 2:
                for i in range(min(n, 30)):
                    for j in range(i + 1, min(n, 30)):
                        for k in range(j + 1, min(n, 30)):
                            if dist[i, j] <= r and dist[j, k] <= r and dist[i, k] <= r:
                                existing = any(s.vertices == (i, j, k) for s in self.simplices if s.dimension == 2)
                                if not existing:
                                    birth = max(dist[i, j], dist[j, k], dist[i, k])
                                    self.simplices.append(Simplex((i, j, k), birth, dimension=2))


class PersistentHomology:
    """지속적 호몰로지 계산 (간이)."""

    def __init__(self):
        self.intervals: list[PersistenceInterval] = []

    def compute(self, simplices: list[Simplex], max_radius=50.0) -> list[PersistenceInterval]:
        self.intervals.clear()

        # Betti-0: 연결 성분 추적 (Union-Find)
        vertices = set()
        for s in simplices:
            if s.dimension == 0:
                vertices.add(s.vertices[0])

        n = max(vertices) + 1 if vertices else 0
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
                return True
            return False

        # 엣지를 birth 순으로 정렬하여 처리
        edges = sorted([s for s in simplices if s.dimension == 1], key=lambda s: s.birth)
        birth_times = {v: 0.0 for v in vertices}

        for edge in edges:
            i, j = edge.vertices
            if union(i, j):
                # 성분 병합 → 하나의 성분이 소멸
                self.intervals.append(PersistenceInterval(0, 0.0, edge.birth, edge.birth))

        # 살아남은 성분
        components = len(set(find(v) for v in vertices))
        for _ in range(components):
            self.intervals.append(PersistenceInterval(0, 0.0, max_radius, max_radius))

        # Betti-1: 삼각형으로 루프 소멸 추적 (근사)
        triangles = sorted([s for s in simplices if s.dimension == 2], key=lambda s: s.birth)
        n_loops = max(0, len(edges) - (n - components))
        for i, tri in enumerate(triangles[:n_loops]):
            self.intervals.append(PersistenceInterval(1, tri.birth * 0.5, tri.birth, tri.birth * 0.5))

        return self.intervals

    def betti_numbers(self, radius: float) -> tuple[int, int, int]:
        b0 = sum(1 for iv in self.intervals if iv.dimension == 0 and iv.birth <= radius < iv.death)
        b1 = sum(1 for iv in self.intervals if iv.dimension == 1 and iv.birth <= radius < iv.death)
        b2 = sum(1 for iv in self.intervals if iv.dimension == 2 and iv.birth <= radius < iv.death)
        return b0, b1, b2


class TopologicalDataAnalysis:
    """TDA 기반 군집 대형 분석."""

    def __init__(self, n_drones=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.positions = self.rng.uniform(-50, 50, (n_drones, 3))
        self.vr = VietorisRips(max_dim=2)
        self.ph = PersistentHomology()
        self.features: TopologicalFeatures | None = None

    def analyze(self, max_radius=50.0):
        self.vr.build(self.positions, max_radius, n_steps=15)
        intervals = self.ph.compute(self.vr.simplices, max_radius)
        b0, b1, b2 = self.ph.betti_numbers(max_radius * 0.5)
        total_p = sum(iv.persistence for iv in intervals)
        self.features = TopologicalFeatures(b0, b1, b2, total_p)

    def summary(self):
        if not self.features:
            self.analyze()
        return {
            "drones": self.n_drones,
            "simplices": len(self.vr.simplices),
            "intervals": len(self.ph.intervals),
            "betti_0": self.features.betti_0,
            "betti_1": self.features.betti_1,
            "total_persistence": round(self.features.total_persistence, 2),
        }


if __name__ == "__main__":
    tda = TopologicalDataAnalysis(15, 42)
    tda.analyze()
    for k, v in tda.summary().items():
        print(f"  {k}: {v}")
