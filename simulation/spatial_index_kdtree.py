# Phase 641: Spatial Index KDTree — O(N²) → O(N log N) 충돌 스캔 최적화
"""
KDTree 기반 공간 인덱스로 근접 드론 쌍 탐색 성능 개선.
scipy.spatial.KDTree를 래핑하여 bulk query_pairs 지원.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class SpatialQuery:
    drone_id: str
    position: np.ndarray
    radius: float = 50.0


class KDTreeIndex:
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self._ids: list[str] = []
        self._positions: np.ndarray = np.empty((0, 3))
        self._tree = None

    def build(self, positions: dict[str, np.ndarray]) -> None:
        from scipy.spatial import KDTree
        self._ids = list(positions.keys())
        self._positions = np.array([positions[did] for did in self._ids])
        if len(self._ids) >= 2:
            self._tree = KDTree(self._positions)
        else:
            self._tree = None

    def query_pairs(self, radius: float) -> list[tuple[str, str, float]]:
        if self._tree is None or len(self._ids) < 2:
            return []
        pairs = self._tree.query_pairs(radius, output_type="ndarray")
        results = []
        for i, j in pairs:
            dist = float(np.linalg.norm(self._positions[i] - self._positions[j]))
            results.append((self._ids[i], self._ids[j], dist))
        return results

    def query_ball(self, point: np.ndarray, radius: float) -> list[str]:
        if self._tree is None:
            return []
        indices = self._tree.query_ball_point(point, radius)
        return [self._ids[i] for i in indices]

    def nearest_k(self, point: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
        if self._tree is None:
            return []
        k = min(k, len(self._ids))
        dists, indices = self._tree.query(point, k=k)
        if k == 1:
            return [(self._ids[indices], float(dists))]
        return [(self._ids[idx], float(d)) for d, idx in zip(dists, indices)]

    def benchmark(self, n_drones: int, n_queries: int = 100) -> dict:
        import time
        positions = {
            f"D-{i:04d}": self.rng.uniform(-5000, 5000, 3)
            for i in range(n_drones)
        }

        t0 = time.perf_counter()
        self.build(positions)
        build_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        pairs = self.query_pairs(50.0)
        query_time = time.perf_counter() - t0

        # brute force comparison
        t0 = time.perf_counter()
        ids = list(positions.keys())
        pos_arr = np.array([positions[d] for d in ids])
        bf_pairs = 0
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if np.linalg.norm(pos_arr[i] - pos_arr[j]) < 50.0:
                    bf_pairs += 1
        bf_time = time.perf_counter() - t0

        return {
            "n_drones": n_drones,
            "kdtree_build_ms": round(build_time * 1000, 3),
            "kdtree_query_ms": round(query_time * 1000, 3),
            "bruteforce_ms": round(bf_time * 1000, 3),
            "speedup": round(bf_time / max(query_time, 1e-9), 1),
            "pairs_found": len(pairs),
        }


if __name__ == "__main__":
    idx = KDTreeIndex(42)
    for n in [50, 100, 200, 500]:
        result = idx.benchmark(n)
        print(f"  N={n:4d} | KDTree: {result['kdtree_query_ms']:8.3f}ms | "
              f"Brute: {result['bruteforce_ms']:8.3f}ms | "
              f"Speedup: {result['speedup']}x | Pairs: {result['pairs_found']}")
