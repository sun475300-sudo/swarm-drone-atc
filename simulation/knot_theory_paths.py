# Phase 627: Knot Theory Paths — Knot Invariants
"""
매듭 이론 기반 3D 궤적 얽힘 분석:
교차수, 라이데마이스터 이동, 얽힘 지표.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class PathSegment:
    points: np.ndarray  # (N, 3)
    drone_id: int


class KnotAnalyzer:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.paths: list[PathSegment] = []

    def add_path(self, drone_id: int, points: np.ndarray):
        self.paths.append(PathSegment(points, drone_id))

    def compute_crossing_number(self, path_a: PathSegment, path_b: PathSegment) -> int:
        crossings = 0
        for i in range(len(path_a.points) - 1):
            for j in range(len(path_b.points) - 1):
                if self._segments_cross_2d(
                    path_a.points[i], path_a.points[i+1],
                    path_b.points[j], path_b.points[j+1]
                ):
                    crossings += 1
        return crossings

    def _segments_cross_2d(self, p1, p2, p3, p4) -> bool:
        d1 = self._cross_2d(p3, p4, p1)
        d2 = self._cross_2d(p3, p4, p2)
        d3 = self._cross_2d(p1, p2, p3)
        d4 = self._cross_2d(p1, p2, p4)
        return (d1 * d2 < 0) and (d3 * d4 < 0)

    def _cross_2d(self, a, b, c) -> float:
        return float((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def total_entanglement(self) -> int:
        total = 0
        for i in range(len(self.paths)):
            for j in range(i+1, len(self.paths)):
                total += self.compute_crossing_number(self.paths[i], self.paths[j])
        return total

    def writhe(self, path: PathSegment) -> float:
        w = 0.0
        pts = path.points
        for i in range(len(pts) - 1):
            for j in range(i+2, len(pts) - 1):
                r = pts[j] - pts[i]
                dist = np.linalg.norm(r) + 1e-6
                t1 = pts[i+1] - pts[i]
                t2 = pts[j+1] - pts[j]
                cross = np.cross(t1, t2)
                w += np.dot(cross, r) / (dist**3)
        return float(w / (4 * np.pi))


class KnotTheoryPaths:
    def __init__(self, n_drones=8, seed=42):
        self.rng = np.random.default_rng(seed)
        self.analyzer = KnotAnalyzer(seed)
        self.n_drones = n_drones
        self._generate_paths()

    def _generate_paths(self):
        for d in range(self.n_drones):
            n_points = 50
            t = np.linspace(0, 4*np.pi, n_points)
            r = 20 + d * 3
            points = np.column_stack([
                r * np.cos(t + d * 0.5),
                r * np.sin(t + d * 0.5),
                5 * np.sin(2 * t + d) + d * 10,
            ])
            self.analyzer.add_path(d, points)

    def run(self):
        pass  # analysis is computed on demand

    def summary(self):
        entanglement = self.analyzer.total_entanglement()
        writhes = [self.analyzer.writhe(p) for p in self.analyzer.paths]
        return {
            "drones": self.n_drones,
            "total_crossings": entanglement,
            "avg_writhe": round(float(np.mean(writhes)), 4),
            "max_writhe": round(float(np.max(np.abs(writhes))), 4),
            "paths": len(self.analyzer.paths),
        }


if __name__ == "__main__":
    kt = KnotTheoryPaths(8, 42)
    kt.run()
    for k, v in kt.summary().items():
        print(f"  {k}: {v}")
