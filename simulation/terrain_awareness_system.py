"""Phase 288: Terrain Awareness System — 지형 인식 시스템.

DEM(Digital Elevation Model) 기반 지형 추적,
최저 안전고도(MSA) 계산, 지형 충돌 경고(TAWS) 구현.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class TerrainType(Enum):
    FLAT = "flat"
    HILL = "hill"
    MOUNTAIN = "mountain"
    VALLEY = "valley"
    URBAN = "urban"
    WATER = "water"
    FOREST = "forest"


class AlertLevel(Enum):
    NONE = "none"
    CAUTION = "caution"
    WARNING = "warning"
    PULL_UP = "pull_up"


@dataclass
class TerrainCell:
    x: int
    y: int
    elevation_m: float
    terrain_type: TerrainType = TerrainType.FLAT
    obstacle_height_m: float = 0.0


@dataclass
class TAWSAlert:
    drone_id: str
    level: AlertLevel
    terrain_elevation: float
    drone_altitude: float
    clearance_m: float
    message: str


class DigitalElevationModel:
    """디지털 고도 모델 (절차적 생성)."""

    def __init__(self, size: int = 100, resolution: float = 10.0, rng_seed: int = 42):
        self.size = size
        self.resolution = resolution
        self._rng = np.random.default_rng(rng_seed)
        self._elevation = self._generate_terrain()
        self._obstacles = np.zeros((size, size))

    def _generate_terrain(self) -> np.ndarray:
        """Perlin-like terrain generation using octave noise."""
        terrain = np.zeros((self.size, self.size))
        for octave in range(4):
            freq = 2 ** octave
            amp = 50.0 / (2 ** octave)
            noise = self._rng.standard_normal((self.size // freq + 2, self.size // freq + 2))
            # Simple bilinear upscale
            x = np.linspace(0, noise.shape[0] - 1, self.size)
            y = np.linspace(0, noise.shape[1] - 1, self.size)
            xg, yg = np.meshgrid(x, y, indexing="ij")
            xi = np.clip(xg.astype(int), 0, noise.shape[0] - 2)
            yi = np.clip(yg.astype(int), 0, noise.shape[1] - 2)
            xf = xg - xi
            yf = yg - yi
            interp = (
                noise[xi, yi] * (1 - xf) * (1 - yf)
                + noise[xi + 1, yi] * xf * (1 - yf)
                + noise[xi, yi + 1] * (1 - xf) * yf
                + noise[xi + 1, yi + 1] * xf * yf
            )
            terrain += interp * amp
        terrain -= terrain.min()
        return terrain

    def add_obstacle(self, x: int, y: int, height: float):
        if 0 <= x < self.size and 0 <= y < self.size:
            self._obstacles[x, y] = max(self._obstacles[x, y], height)

    def elevation_at(self, world_x: float, world_y: float) -> float:
        gx = int(world_x / self.resolution) % self.size
        gy = int(world_y / self.resolution) % self.size
        return float(self._elevation[gx, gy] + self._obstacles[gx, gy])

    def terrain_profile(self, start: np.ndarray, end: np.ndarray, n_samples: int = 50) -> List[float]:
        profile = []
        for i in range(n_samples):
            t = i / (n_samples - 1)
            pos = start * (1 - t) + end * t
            profile.append(self.elevation_at(pos[0], pos[1]))
        return profile

    def max_elevation_in_radius(self, x: float, y: float, radius: float) -> float:
        gx = int(x / self.resolution)
        gy = int(y / self.resolution)
        r_cells = int(radius / self.resolution) + 1
        max_elev = 0.0
        for dx in range(-r_cells, r_cells + 1):
            for dy in range(-r_cells, r_cells + 1):
                cx, cy = (gx + dx) % self.size, (gy + dy) % self.size
                max_elev = max(max_elev, self._elevation[cx, cy] + self._obstacles[cx, cy])
        return max_elev


class TerrainAwarenessSystem:
    """지형 인식 및 충돌 경고 시스템 (TAWS).

    - DEM 기반 지형 고도 조회
    - 최저 안전고도(MSA) 계산
    - 지형 접근 경고 (CFIT 방지)
    - 비행 경로 지형 클리어런스 검증
    """

    MIN_CLEARANCE_M = 30.0
    WARNING_CLEARANCE_M = 50.0
    CAUTION_CLEARANCE_M = 80.0

    def __init__(self, dem_size: int = 100, resolution: float = 10.0, rng_seed: int = 42):
        self._dem = DigitalElevationModel(dem_size, resolution, rng_seed)
        self._alerts: List[TAWSAlert] = []
        self._drone_altitudes: Dict[str, float] = {}
        self._msa_cache: Dict[Tuple[int, int], float] = {}

    def get_elevation(self, x: float, y: float) -> float:
        return self._dem.elevation_at(x, y)

    def compute_msa(self, x: float, y: float, radius: float = 100.0) -> float:
        max_terrain = self._dem.max_elevation_in_radius(x, y, radius)
        return max_terrain + self.MIN_CLEARANCE_M

    def check_clearance(self, drone_id: str, position: np.ndarray) -> TAWSAlert:
        terrain_elev = self.get_elevation(position[0], position[1])
        altitude = position[2] if len(position) > 2 else 50.0
        clearance = altitude - terrain_elev
        self._drone_altitudes[drone_id] = altitude
        if clearance < self.MIN_CLEARANCE_M:
            level = AlertLevel.PULL_UP
            msg = f"PULL UP! Clearance {clearance:.0f}m < {self.MIN_CLEARANCE_M}m"
        elif clearance < self.WARNING_CLEARANCE_M:
            level = AlertLevel.WARNING
            msg = f"TERRAIN WARNING: Clearance {clearance:.0f}m"
        elif clearance < self.CAUTION_CLEARANCE_M:
            level = AlertLevel.CAUTION
            msg = f"Terrain caution: Clearance {clearance:.0f}m"
        else:
            level = AlertLevel.NONE
            msg = "Terrain clear"
        alert = TAWSAlert(
            drone_id=drone_id, level=level, terrain_elevation=terrain_elev,
            drone_altitude=altitude, clearance_m=clearance, message=msg,
        )
        if level != AlertLevel.NONE:
            self._alerts.append(alert)
        return alert

    def validate_path(self, waypoints: List[np.ndarray]) -> List[TAWSAlert]:
        alerts = []
        for i, wp in enumerate(waypoints):
            elev = self.get_elevation(wp[0], wp[1])
            alt = wp[2] if len(wp) > 2 else 50.0
            clearance = alt - elev
            if clearance < self.WARNING_CLEARANCE_M:
                level = AlertLevel.WARNING if clearance < self.MIN_CLEARANCE_M else AlertLevel.CAUTION
                alerts.append(TAWSAlert(
                    drone_id=f"waypoint_{i}", level=level, terrain_elevation=elev,
                    drone_altitude=alt, clearance_m=clearance,
                    message=f"Path waypoint {i}: clearance {clearance:.0f}m",
                ))
        return alerts

    def terrain_profile(self, start: np.ndarray, end: np.ndarray) -> List[float]:
        return self._dem.terrain_profile(start, end)

    def get_alerts(self, level: Optional[AlertLevel] = None) -> List[TAWSAlert]:
        if level:
            return [a for a in self._alerts if a.level == level]
        return self._alerts.copy()

    def clear_alerts(self):
        self._alerts.clear()

    def summary(self) -> dict:
        level_counts = {}
        for a in self._alerts:
            level_counts[a.level.value] = level_counts.get(a.level.value, 0) + 1
        return {
            "dem_size": self._dem.size,
            "tracked_drones": len(self._drone_altitudes),
            "total_alerts": len(self._alerts),
            "alert_levels": level_counts,
        }
