"""
풍동 시뮬레이터
==============
3D 풍속 필드 + 건물 차폐 + 터널 효과.

사용법:
    wt = WindTunnel(base_wind=(5, 0, 0))
    wt.add_building((100, 100), width=50, height=80)
    wind = wt.wind_at((120, 110, 40))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Building:
    """건물"""
    center: tuple[float, float]
    width: float
    height: float


class WindTunnel:
    """3D 풍동 시뮬레이터."""

    def __init__(self, base_wind: tuple[float, float, float] = (5.0, 0.0, 0.0), seed: int = 42) -> None:
        self.base_wind = np.array(base_wind, dtype=float)
        self._rng = np.random.default_rng(seed)
        self._buildings: list[Building] = []
        self._queries = 0

    def add_building(self, center: tuple[float, float], width: float = 50, height: float = 80) -> None:
        self._buildings.append(Building(center=center, width=width, height=height))

    def wind_at(self, position: tuple[float, float, float]) -> tuple[float, float, float]:
        """특정 위치의 풍속 벡터"""
        self._queries += 1
        pos = np.array(position)
        wind = self.base_wind.copy()

        for bld in self._buildings:
            bx, by = bld.center
            dx = pos[0] - bx
            dy = pos[1] - by
            dist_xy = np.sqrt(dx**2 + dy**2)
            half_w = bld.width / 2

            if dist_xy < half_w * 3 and pos[2] < bld.height:
                # 차폐 효과
                shelter = max(0, 1 - dist_xy / (half_w * 3))
                wind[:2] *= (1 - shelter * 0.7)

                # 터널 효과 (건물 사이)
                if half_w < dist_xy < half_w * 2:
                    wind[:2] *= 1.3  # 가속

                # 상승 기류 (건물 상단 근처)
                if pos[2] > bld.height * 0.7 and dist_xy < half_w * 2:
                    wind[2] += 2.0 * shelter

        # 난류 추가
        turbulence = self._rng.normal(0, 0.5, size=3)
        wind += turbulence

        return (round(float(wind[0]), 2), round(float(wind[1]), 2), round(float(wind[2]), 2))

    def wind_speed_at(self, position: tuple[float, float, float]) -> float:
        w = self.wind_at(position)
        return round(float(np.sqrt(sum(v**2 for v in w))), 2)

    def is_sheltered(self, position: tuple[float, float, float], threshold: float = 0.5) -> bool:
        base_speed = float(np.linalg.norm(self.base_wind))
        actual_speed = self.wind_speed_at(position)
        return actual_speed < base_speed * threshold

    def wind_field_slice(self, z: float, grid_n: int = 10, area: float = 1000) -> list[dict[str, Any]]:
        """수평 슬라이스 풍속 필드"""
        field = []
        step = area / grid_n
        for i in range(grid_n):
            for j in range(grid_n):
                x, y = i * step, j * step
                w = self.wind_at((x, y, z))
                field.append({"x": x, "y": y, "z": z, "wx": w[0], "wy": w[1], "wz": w[2]})
        return field

    def summary(self) -> dict[str, Any]:
        return {
            "buildings": len(self._buildings),
            "base_wind_speed": round(float(np.linalg.norm(self.base_wind)), 1),
            "total_queries": self._queries,
        }
