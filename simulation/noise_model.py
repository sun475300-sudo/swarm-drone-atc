"""
소음 모델링
==========
드론별 소음 레벨 계산 + 지상 소음 지도 + 소음 규제 검증.
거리 감쇠 + 다중 드론 합산 + 시간대별 규제.

사용법:
    nm = NoiseModel()
    nm.update_drones({"d1": (100, 200, 50)})
    level = nm.ground_noise_at(100, 200)  # dBA
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class NoiseSource:
    """드론 소음원"""
    drone_id: str
    position: tuple[float, float, float]
    base_noise_dba: float = 75.0  # 1m 기준 소음 (dBA)
    speed_factor: float = 1.0  # 속도 비례 소음 증가


@dataclass
class NoiseRegulation:
    """소음 규제"""
    name: str
    max_dba: float
    time_start: float = 0.0  # 시 (0~24)
    time_end: float = 24.0
    description: str = ""


DEFAULT_REGULATIONS: list[NoiseRegulation] = [
    NoiseRegulation("주간", max_dba=65.0, time_start=6.0, time_end=22.0,
                    description="주간 소음 기준 65dBA"),
    NoiseRegulation("야간", max_dba=55.0, time_start=22.0, time_end=6.0,
                    description="야간 소음 기준 55dBA"),
]


class NoiseModel:
    """
    드론 소음 모델.

    역제곱 법칙 감쇠 + 다중 소음원 합산.
    """

    def __init__(
        self,
        base_noise_dba: float = 75.0,
        regulations: list[NoiseRegulation] | None = None,
    ) -> None:
        self.base_noise_dba = base_noise_dba
        self.regulations = regulations or list(DEFAULT_REGULATIONS)
        self._sources: dict[str, NoiseSource] = {}

    def update_drones(
        self,
        positions: dict[str, tuple[float, float, float]],
        speeds: dict[str, float] | None = None,
    ) -> None:
        """드론 위치 갱신"""
        speeds = speeds or {}
        self._sources.clear()
        for did, pos in positions.items():
            speed = speeds.get(did, 10.0)
            speed_factor = 1.0 + max(0, speed - 10) * 0.02
            self._sources[did] = NoiseSource(
                drone_id=did,
                position=pos,
                base_noise_dba=self.base_noise_dba,
                speed_factor=speed_factor,
            )

    def noise_at(self, x: float, y: float, z: float = 0.0) -> float:
        """특정 위치의 합산 소음 레벨 (dBA)"""
        if not self._sources:
            return 0.0

        # 에너지 합산 (dBA → W → 합산 → dBA)
        total_energy = 0.0
        for src in self._sources.values():
            sx, sy, sz = src.position
            dist = max(1.0, np.sqrt((x - sx)**2 + (y - sy)**2 + (z - sz)**2))
            # 역제곱 감쇠: L = L_ref - 20*log10(d/d_ref)
            level = src.base_noise_dba * src.speed_factor - 20 * np.log10(dist)
            if level > 0:
                total_energy += 10 ** (level / 10)

        if total_energy <= 0:
            return 0.0
        return float(10 * np.log10(total_energy))

    def ground_noise_at(self, x: float, y: float) -> float:
        """지상 소음 레벨"""
        return self.noise_at(x, y, z=0.0)

    def noise_map(
        self,
        bounds: tuple[float, float, float, float] = (0, 0, 1000, 1000),
        resolution: int = 20,
    ) -> np.ndarray:
        """소음 지도 (2D grid)"""
        x_min, y_min, x_max, y_max = bounds
        xs = np.linspace(x_min, x_max, resolution)
        ys = np.linspace(y_min, y_max, resolution)
        grid = np.zeros((resolution, resolution))
        for i, y in enumerate(ys):
            for j, x in enumerate(xs):
                grid[i, j] = self.ground_noise_at(x, y)
        return grid

    def max_ground_noise(self) -> float:
        """현재 최대 지상 소음"""
        if not self._sources:
            return 0.0
        # 각 드론 직하점 소음 중 최대
        max_n = 0.0
        for src in self._sources.values():
            n = self.ground_noise_at(src.position[0], src.position[1])
            max_n = max(max_n, n)
        return max_n

    def check_regulation(
        self, x: float, y: float, hour: float = 12.0
    ) -> list[dict[str, Any]]:
        """소음 규제 위반 검사"""
        level = self.ground_noise_at(x, y)
        violations = []
        for reg in self.regulations:
            in_range = False
            if reg.time_start < reg.time_end:
                in_range = reg.time_start <= hour < reg.time_end
            else:
                in_range = hour >= reg.time_start or hour < reg.time_end

            if in_range and level > reg.max_dba:
                violations.append({
                    "regulation": reg.name,
                    "max_dba": reg.max_dba,
                    "actual_dba": round(level, 1),
                    "exceeded_by": round(level - reg.max_dba, 1),
                    "description": reg.description,
                })
        return violations

    def footprint_area(self, threshold_dba: float = 55.0) -> float:
        """소음 영향 면적 추정 (m²)"""
        if not self._sources:
            return 0.0
        # 각 드론의 영향 반경 합산
        total = 0.0
        for src in self._sources.values():
            # L = L_ref - 20*log10(r) → r = 10^((L_ref - threshold) / 20)
            r = 10 ** ((src.base_noise_dba * src.speed_factor - threshold_dba) / 20)
            total += np.pi * r * r
        return float(total)

    def summary(self) -> dict[str, Any]:
        return {
            "total_sources": len(self._sources),
            "max_ground_noise_dba": round(self.max_ground_noise(), 1),
            "footprint_55dba_m2": round(self.footprint_area(55.0), 0),
        }
