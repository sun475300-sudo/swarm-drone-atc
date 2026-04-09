"""
공역 히트맵
===========
시간대별 밀도 히트맵 + 핫스팟 예측 + 트렌드.

사용법:
    hm = AirspaceHeatmap(bounds=(0, 0, 1000, 1000), resolution=100)
    hm.record(positions, t=10.0)
    hot = hm.hotspots()
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class HotspotInfo:
    """핫스팟 정보"""
    row: int
    col: int
    center: tuple[float, float]
    density: float
    trend: float  # 양수 = 증가, 음수 = 감소


class AirspaceHeatmap:
    """시간대별 공역 밀도 히트맵."""

    def __init__(
        self,
        bounds: tuple[float, float, float, float] = (0, 0, 1000, 1000),
        resolution: float = 100.0,
        time_window: int = 10,
    ) -> None:
        self.bounds = bounds
        self.resolution = resolution
        x_min, y_min, x_max, y_max = bounds
        self.n_cols = max(1, int((x_max - x_min) / resolution))
        self.n_rows = max(1, int((y_max - y_min) / resolution))
        self._time_window = time_window
        self._snapshots: list[tuple[float, np.ndarray]] = []

    def record(
        self, positions: dict[str, tuple[float, float, float]], t: float,
    ) -> None:
        """현재 위치 기록"""
        grid = np.zeros((self.n_rows, self.n_cols))
        x_min, y_min, x_max, y_max = self.bounds

        for pos in positions.values():
            col = int((pos[0] - x_min) / self.resolution)
            row = int((pos[1] - y_min) / self.resolution)
            col = max(0, min(col, self.n_cols - 1))
            row = max(0, min(row, self.n_rows - 1))
            grid[row, col] += 1

        self._snapshots.append((t, grid))
        if len(self._snapshots) > self._time_window * 10:
            self._snapshots = self._snapshots[-self._time_window * 10:]

    def current_heatmap(self) -> np.ndarray:
        if not self._snapshots:
            return np.zeros((self.n_rows, self.n_cols))
        return self._snapshots[-1][1]

    def average_heatmap(self, n: int | None = None) -> np.ndarray:
        """최근 n 스냅샷 평균"""
        if not self._snapshots:
            return np.zeros((self.n_rows, self.n_cols))
        count = n or self._time_window
        recent = self._snapshots[-count:]
        grids = np.array([g for _, g in recent])
        return np.mean(grids, axis=0)

    def hotspots(self, threshold: float = 3.0) -> list[HotspotInfo]:
        """핫스팟 탐지 (평균 밀도 이상)"""
        avg = self.average_heatmap()
        trend = self._compute_trend()
        hotspots = []

        for r in range(self.n_rows):
            for c in range(self.n_cols):
                if avg[r, c] >= threshold:
                    x_min, y_min = self.bounds[0], self.bounds[1]
                    cx = x_min + (c + 0.5) * self.resolution
                    cy = y_min + (r + 0.5) * self.resolution
                    hotspots.append(HotspotInfo(
                        row=r, col=c,
                        center=(cx, cy),
                        density=float(avg[r, c]),
                        trend=float(trend[r, c]) if trend is not None else 0.0,
                    ))

        return sorted(hotspots, key=lambda h: -h.density)

    def predict_density(
        self, row: int, col: int, steps_ahead: int = 5,
    ) -> float:
        """특정 셀 밀도 예측"""
        if len(self._snapshots) < 3:
            return self.current_heatmap()[row, col] if self._snapshots else 0.0

        recent_values = [g[row, col] for _, g in self._snapshots[-10:]]
        if len(recent_values) < 2:
            return recent_values[-1] if recent_values else 0.0

        # 선형 트렌드
        x = np.arange(len(recent_values))
        slope = np.polyfit(x, recent_values, 1)[0]
        predicted = recent_values[-1] + slope * steps_ahead
        return max(0, float(predicted))

    def _compute_trend(self) -> np.ndarray | None:
        if len(self._snapshots) < 3:
            return None

        recent = self._snapshots[-min(5, len(self._snapshots)):]
        if len(recent) < 2:
            return None

        first = recent[0][1]
        last = recent[-1][1]
        dt = recent[-1][0] - recent[0][0]
        if dt < 1e-6:
            return np.zeros_like(first)
        return (last - first) / dt

    def peak_density(self) -> float:
        hm = self.current_heatmap()
        return float(np.max(hm))

    def summary(self) -> dict[str, Any]:
        hm = self.current_heatmap()
        return {
            "grid_size": (self.n_rows, self.n_cols),
            "snapshots": len(self._snapshots),
            "peak_density": float(np.max(hm)) if self._snapshots else 0,
            "mean_density": float(np.mean(hm)) if self._snapshots else 0,
            "hotspot_count": len(self.hotspots()),
        }
