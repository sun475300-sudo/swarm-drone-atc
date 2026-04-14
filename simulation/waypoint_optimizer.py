"""
웨이포인트 최적화
=================
경유지 간소화 + 곡선 평활화 + 에너지 절감.
Ramer-Douglas-Peucker 간소화 + Bezier 평활화.

사용법:
    opt = WaypointOptimizer()
    simplified = opt.simplify(waypoints, epsilon=5.0)
    smooth = opt.smooth(waypoints, resolution=20)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class OptimizationResult:
    """최적화 결과"""
    original_count: int
    optimized_count: int
    reduction_pct: float
    distance_saved_m: float
    energy_saved_pct: float


class WaypointOptimizer:
    """웨이포인트 경로 최적화."""

    def __init__(self, energy_per_meter: float = 0.01) -> None:
        self._energy_per_m = energy_per_meter

    def simplify(
        self,
        waypoints: list[tuple[float, float, float]],
        epsilon: float = 5.0,
    ) -> list[tuple[float, float, float]]:
        """Ramer-Douglas-Peucker 간소화"""
        if len(waypoints) <= 2:
            return list(waypoints)
        return self._rdp(waypoints, epsilon)

    def smooth(
        self,
        waypoints: list[tuple[float, float, float]],
        resolution: int = 20,
    ) -> list[tuple[float, float, float]]:
        """Bezier 곡선 평활화"""
        if len(waypoints) <= 2:
            return list(waypoints)

        pts = np.array(waypoints, dtype=float)
        n = len(pts)
        result = []

        for i in range(n - 1):
            for t_step in range(resolution):
                t = t_step / resolution
                if i == 0:
                    p = (1 - t) * pts[i] + t * pts[i + 1]
                elif i == n - 2:
                    p = (1 - t) * pts[i] + t * pts[i + 1]
                else:
                    # 3점 Bezier
                    p0 = (pts[i - 1] + pts[i]) / 2
                    p1 = pts[i]
                    p2 = (pts[i] + pts[i + 1]) / 2
                    p = (1 - t)**2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2

                result.append(tuple(p))

        result.append(waypoints[-1])
        return result

    def optimize(
        self,
        waypoints: list[tuple[float, float, float]],
        epsilon: float = 5.0,
    ) -> OptimizationResult:
        """간소화 + 에너지 절감 분석"""
        original = list(waypoints)
        simplified = self.simplify(waypoints, epsilon)

        orig_dist = self._total_distance(original)
        simp_dist = self._total_distance(simplified)

        saved = orig_dist - simp_dist
        energy_saved = (saved / max(orig_dist, 0.01)) * 100

        return OptimizationResult(
            original_count=len(original),
            optimized_count=len(simplified),
            reduction_pct=(1 - len(simplified) / max(len(original), 1)) * 100,
            distance_saved_m=saved,
            energy_saved_pct=max(0, energy_saved),
        )

    def remove_collinear(
        self,
        waypoints: list[tuple[float, float, float]],
        angle_threshold_deg: float = 5.0,
    ) -> list[tuple[float, float, float]]:
        """거의 직선인 중간 웨이포인트 제거"""
        if len(waypoints) <= 2:
            return list(waypoints)

        result = [waypoints[0]]
        for i in range(1, len(waypoints) - 1):
            v1 = np.array(waypoints[i]) - np.array(waypoints[i - 1])
            v2 = np.array(waypoints[i + 1]) - np.array(waypoints[i])
            n1 = np.linalg.norm(v1)
            n2 = np.linalg.norm(v2)
            if n1 > 0 and n2 > 0:
                cos_a = np.dot(v1, v2) / (n1 * n2)
                cos_a = np.clip(cos_a, -1, 1)
                angle = np.degrees(np.arccos(cos_a))
                if angle > angle_threshold_deg:
                    result.append(waypoints[i])
            else:
                result.append(waypoints[i])
        result.append(waypoints[-1])
        return result

    def _rdp(
        self,
        points: list[tuple[float, float, float]],
        epsilon: float,
    ) -> list[tuple[float, float, float]]:
        """Ramer-Douglas-Peucker"""
        if len(points) <= 2:
            return list(points)

        # 최대 거리 점 찾기
        start = np.array(points[0])
        end = np.array(points[-1])
        line_vec = end - start
        line_len = np.linalg.norm(line_vec)

        max_dist = 0
        max_idx = 0
        for i in range(1, len(points) - 1):
            pt = np.array(points[i])
            if line_len < 1e-6:
                d = float(np.linalg.norm(pt - start))
            else:
                cross = line_vec[0] * (pt[1] - start[1]) - line_vec[1] * (pt[0] - start[0])
                d = abs(float(cross)) / line_len
            if d > max_dist:
                max_dist = d
                max_idx = i

        if max_dist > epsilon:
            left = self._rdp(points[:max_idx + 1], epsilon)
            right = self._rdp(points[max_idx:], epsilon)
            return left[:-1] + right
        else:
            return [points[0], points[-1]]

    def _total_distance(self, wps: list[tuple[float, float, float]]) -> float:
        total = 0.0
        for i in range(len(wps) - 1):
            total += float(np.linalg.norm(
                np.array(wps[i + 1]) - np.array(wps[i])
            ))
        return total

    def summary(
        self, waypoints: list[tuple[float, float, float]], epsilon: float = 5.0
    ) -> dict[str, Any]:
        result = self.optimize(waypoints, epsilon)
        return {
            "original": result.original_count,
            "optimized": result.optimized_count,
            "reduction_pct": round(result.reduction_pct, 1),
            "distance_saved_m": round(result.distance_saved_m, 1),
        }
