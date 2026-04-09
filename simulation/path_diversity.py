"""
경로 다양성 생성기
=================
k-최단경로 + 경로 유사도 + 분산 최적화.

사용법:
    pd = PathDiversity()
    paths = pd.generate_diverse_paths(start=(0,0,50), goal=(1000,1000,50), k=5)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class PathCandidate:
    """경로 후보"""
    path_id: int
    waypoints: list[tuple[float, float, float]]
    distance: float
    diversity_score: float = 0.0
    risk_score: float = 0.0


class PathDiversity:
    """경로 다양성 생성."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._generated: list[list[PathCandidate]] = []

    def _straight_distance(
        self, a: tuple[float, float, float], b: tuple[float, float, float],
    ) -> float:
        return float(np.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b))))

    def _generate_detour(
        self, start: tuple[float, float, float],
        goal: tuple[float, float, float],
        spread: float,
    ) -> list[tuple[float, float, float]]:
        """우회 경로 생성"""
        n_waypoints = self._rng.integers(2, 5)
        waypoints = [start]
        for i in range(n_waypoints):
            t = (i + 1) / (n_waypoints + 1)
            mid = tuple(s + (g - s) * t for s, g in zip(start, goal))
            offset = tuple(self._rng.normal(0, spread) for _ in range(3))
            wp = (mid[0] + offset[0], mid[1] + offset[1], max(30, mid[2] + offset[2] * 0.3))
            waypoints.append(wp)
        waypoints.append(goal)
        return waypoints

    def _path_distance(self, waypoints: list[tuple[float, float, float]]) -> float:
        total = 0.0
        for i in range(len(waypoints) - 1):
            total += self._straight_distance(waypoints[i], waypoints[i + 1])
        return total

    def _path_similarity(
        self, path_a: list[tuple[float, float, float]],
        path_b: list[tuple[float, float, float]],
    ) -> float:
        """두 경로 유사도 (0=완전다름, 1=동일)"""
        n = min(len(path_a), len(path_b))
        if n == 0:
            return 0.0
        dists = []
        for i in range(n):
            ia = int(i * len(path_a) / n)
            ib = int(i * len(path_b) / n)
            d = self._straight_distance(path_a[min(ia, len(path_a)-1)], path_b[min(ib, len(path_b)-1)])
            dists.append(d)
        avg_dist = np.mean(dists)
        return max(0, 1 - avg_dist / 500)

    def generate_diverse_paths(
        self, start: tuple[float, float, float],
        goal: tuple[float, float, float],
        k: int = 5, min_diversity: float = 0.3,
    ) -> list[PathCandidate]:
        """k개 다양한 경로 생성"""
        direct = self._straight_distance(start, goal)
        candidates: list[PathCandidate] = []

        # 직선 경로
        direct_path = PathCandidate(
            path_id=0, waypoints=[start, goal],
            distance=direct, diversity_score=0.0,
        )
        candidates.append(direct_path)

        attempts = 0
        pid = 1
        while len(candidates) < k and attempts < k * 10:
            spread = direct * 0.1 * (1 + attempts * 0.1)
            waypoints = self._generate_detour(start, goal, spread)
            dist = self._path_distance(waypoints)

            # 다양성 검사
            similarities = [
                self._path_similarity(waypoints, c.waypoints) for c in candidates
            ]
            avg_sim = np.mean(similarities) if similarities else 0

            if avg_sim < (1 - min_diversity) or attempts > k * 5:
                candidate = PathCandidate(
                    path_id=pid, waypoints=waypoints,
                    distance=round(dist, 1),
                    diversity_score=round(1 - avg_sim, 3),
                )
                candidates.append(candidate)
                pid += 1

            attempts += 1

        self._generated.append(candidates)
        return candidates

    def best_diverse_path(
        self, candidates: list[PathCandidate],
        distance_weight: float = 0.6, diversity_weight: float = 0.4,
    ) -> PathCandidate | None:
        if not candidates:
            return None
        min_dist = min(c.distance for c in candidates)
        max_dist = max(c.distance for c in candidates)
        rng = max_dist - min_dist if max_dist > min_dist else 1

        best = None
        best_score = -1
        for c in candidates:
            d_score = 1 - (c.distance - min_dist) / rng
            score = d_score * distance_weight + c.diversity_score * diversity_weight
            if score > best_score:
                best_score = score
                best = c
        return best

    def summary(self) -> dict[str, Any]:
        return {
            "total_generations": len(self._generated),
            "total_candidates": sum(len(g) for g in self._generated),
        }
