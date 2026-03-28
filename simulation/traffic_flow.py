"""
교통 흐름 분석기
================
방향별 밀도 분석 + 병목 탐지 + 흐름 최적화.
공역 내 드론 교통 패턴 실시간 모니터링.

사용법:
    tf = TrafficFlowAnalyzer(bounds=(0, 0, 1000, 1000), grid=(5, 5))
    tf.update(positions, velocities)
    bottlenecks = tf.detect_bottlenecks()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class FlowCell:
    """교통 흐름 셀"""
    row: int
    col: int
    density: int = 0
    avg_speed: float = 0.0
    avg_direction_deg: float = 0.0
    flow_rate: float = 0.0  # drones/min 통과량
    congestion: float = 0.0  # 0~1


@dataclass
class Bottleneck:
    """병목 지점"""
    cell_id: str
    row: int
    col: int
    density: int
    congestion: float
    avg_speed: float
    recommendation: str


class TrafficFlowAnalyzer:
    """교통 흐름 분석기."""

    def __init__(
        self,
        bounds: tuple[float, float, float, float] = (0, 0, 1000, 1000),
        grid: tuple[int, int] = (5, 5),
        congestion_threshold: float = 0.7,
        max_density_per_cell: int = 10,
    ) -> None:
        self.bounds = bounds
        self.n_rows, self.n_cols = grid
        self.congestion_threshold = congestion_threshold
        self.max_density = max_density_per_cell
        self._cells: dict[str, FlowCell] = {}
        self._init_cells()

    def _init_cells(self) -> None:
        for r in range(self.n_rows):
            for c in range(self.n_cols):
                self._cells[f"{r}_{c}"] = FlowCell(row=r, col=c)

    def update(
        self,
        positions: dict[str, tuple[float, float, float]],
        velocities: dict[str, tuple[float, float, float]] | None = None,
    ) -> None:
        """드론 위치/속도로 흐름 갱신"""
        # 리셋
        for cell in self._cells.values():
            cell.density = 0
            cell.avg_speed = 0
            cell.avg_direction_deg = 0
            cell.congestion = 0

        cell_drones: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
            k: [] for k in self._cells
        }

        velocities = velocities or {}

        for did, pos in positions.items():
            cid = self._get_cell_id(pos[0], pos[1])
            if cid:
                vel = velocities.get(did, (0, 0, 0))
                cell_drones[cid].append((np.array(pos), np.array(vel)))

        for cid, drones in cell_drones.items():
            cell = self._cells[cid]
            cell.density = len(drones)
            cell.congestion = cell.density / max(self.max_density, 1)

            if drones:
                speeds = [float(np.linalg.norm(v)) for _, v in drones]
                cell.avg_speed = float(np.mean(speeds))

                dirs = []
                for _, v in drones:
                    if np.linalg.norm(v[:2]) > 0.1:
                        angle = float(np.degrees(np.arctan2(v[1], v[0]))) % 360
                        dirs.append(angle)
                if dirs:
                    sin_avg = np.mean(np.sin(np.radians(dirs)))
                    cos_avg = np.mean(np.cos(np.radians(dirs)))
                    cell.avg_direction_deg = float(np.degrees(np.arctan2(sin_avg, cos_avg))) % 360

                cell.flow_rate = cell.density * cell.avg_speed / 10.0

    def detect_bottlenecks(self) -> list[Bottleneck]:
        """병목 지점 탐지"""
        bottlenecks = []
        for cid, cell in self._cells.items():
            if cell.congestion >= self.congestion_threshold:
                if cell.avg_speed < 5.0 and cell.density > 2:
                    rec = "교통 흐름 분산 필요 — 대안 경로 활성화"
                elif cell.congestion >= 1.0:
                    rec = "과밀 — 유입 제한 또는 고도 분리 권장"
                else:
                    rec = "혼잡 주의 — 모니터링 강화"

                bottlenecks.append(Bottleneck(
                    cell_id=cid, row=cell.row, col=cell.col,
                    density=cell.density, congestion=cell.congestion,
                    avg_speed=cell.avg_speed, recommendation=rec,
                ))
        return bottlenecks

    def flow_map(self) -> np.ndarray:
        """흐름률 2D 맵"""
        grid = np.zeros((self.n_rows, self.n_cols))
        for cell in self._cells.values():
            grid[cell.row, cell.col] = cell.flow_rate
        return grid

    def density_map(self) -> np.ndarray:
        grid = np.zeros((self.n_rows, self.n_cols))
        for cell in self._cells.values():
            grid[cell.row, cell.col] = cell.density
        return grid

    def overall_congestion(self) -> float:
        if not self._cells:
            return 0.0
        return float(np.mean([c.congestion for c in self._cells.values()]))

    def _get_cell_id(self, x: float, y: float) -> str | None:
        x_min, y_min, x_max, y_max = self.bounds
        dx = (x_max - x_min) / self.n_cols
        dy = (y_max - y_min) / self.n_rows
        col = int((x - x_min) / dx)
        row = int((y - y_min) / dy)
        col = max(0, min(col, self.n_cols - 1))
        row = max(0, min(row, self.n_rows - 1))
        return f"{row}_{col}"

    def summary(self) -> dict[str, Any]:
        bns = self.detect_bottlenecks()
        return {
            "total_cells": len(self._cells),
            "overall_congestion": round(self.overall_congestion(), 3),
            "bottleneck_count": len(bns),
            "max_density": max((c.density for c in self._cells.values()), default=0),
        }
