"""Phase 297: Real-time Map Builder — 실시간 지도 구축.

SLAM(Simultaneous Localization and Mapping) 기반 환경 매핑,
점유 격자(Occupancy Grid), 포인트 클라우드 통합, 지도 공유.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class CellState(Enum):
    UNKNOWN = 0
    FREE = 1
    OCCUPIED = 2
    DYNAMIC = 3


@dataclass
class MapObservation:
    observer_id: str
    position: np.ndarray
    scan_points: List[np.ndarray]
    timestamp: float = 0.0
    confidence: float = 0.8


@dataclass
class PointOfInterest:
    poi_id: str
    position: np.ndarray
    category: str  # "obstacle", "landing_pad", "building", "tree", "antenna"
    confidence: float = 0.5
    first_seen: float = 0.0
    last_seen: float = 0.0
    observations: int = 1


class OccupancyGrid:
    """로그 확률 기반 점유 격자."""

    def __init__(self, size: int = 200, resolution: float = 5.0):
        self.size = size
        self.resolution = resolution
        self._grid = np.zeros((size, size, 20), dtype=np.float32)  # log-odds
        self._update_count = np.zeros((size, size, 20), dtype=np.int32)
        self.LOG_ODD_FREE = -0.4
        self.LOG_ODD_OCC = 0.85
        self.CLAMP = 5.0

    def _to_grid(self, pos: np.ndarray) -> Tuple[int, int, int]:
        gx = int(pos[0] / self.resolution + self.size / 2) % self.size
        gy = int(pos[1] / self.resolution + self.size / 2) % self.size
        gz = max(0, min(19, int(pos[2] / self.resolution) if len(pos) > 2 else 5))
        return gx, gy, gz

    def update_free(self, pos: np.ndarray):
        gx, gy, gz = self._to_grid(pos)
        self._grid[gx, gy, gz] = np.clip(self._grid[gx, gy, gz] + self.LOG_ODD_FREE, -self.CLAMP, self.CLAMP)
        self._update_count[gx, gy, gz] += 1

    def update_occupied(self, pos: np.ndarray):
        gx, gy, gz = self._to_grid(pos)
        self._grid[gx, gy, gz] = np.clip(self._grid[gx, gy, gz] + self.LOG_ODD_OCC, -self.CLAMP, self.CLAMP)
        self._update_count[gx, gy, gz] += 1

    def get_state(self, pos: np.ndarray) -> CellState:
        gx, gy, gz = self._to_grid(pos)
        val = self._grid[gx, gy, gz]
        if self._update_count[gx, gy, gz] == 0:
            return CellState.UNKNOWN
        elif val > 0.5:
            return CellState.OCCUPIED
        elif val < -0.5:
            return CellState.FREE
        return CellState.UNKNOWN

    def get_probability(self, pos: np.ndarray) -> float:
        gx, gy, gz = self._to_grid(pos)
        return 1.0 / (1.0 + np.exp(-self._grid[gx, gy, gz]))

    def get_explored_ratio(self) -> float:
        total = self._update_count.size
        explored = np.count_nonzero(self._update_count)
        return explored / total


class RealtimeMapBuilder:
    """실시간 지도 구축기.

    - 점유 격자 기반 환경 매핑
    - 레이캐스트 관측 통합
    - POI(관심 지점) 탐지 및 추적
    - 다중 드론 지도 공유/병합
    """

    def __init__(self, grid_size: int = 200, resolution: float = 5.0, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._grid = OccupancyGrid(grid_size, resolution)
        self._pois: Dict[str, PointOfInterest] = {}
        self._observations: List[MapObservation] = []
        self._drone_positions: Dict[str, np.ndarray] = {}
        self._poi_counter = 0

    def process_observation(self, obs: MapObservation):
        self._observations.append(obs)
        self._drone_positions[obs.observer_id] = obs.position.copy()
        # Ray-cast: mark cells between observer and scan points
        for point in obs.scan_points:
            direction = point - obs.position
            dist = np.linalg.norm(direction)
            if dist < 0.1:
                continue
            n_steps = max(2, int(dist / self._grid.resolution))
            for i in range(n_steps - 1):
                t = i / n_steps
                free_pos = obs.position + direction * t
                self._grid.update_free(free_pos)
            # Endpoint is occupied
            self._grid.update_occupied(point)
            # Check for POI
            self._check_poi(point, obs)

    def _check_poi(self, point: np.ndarray, obs: MapObservation):
        # Check if near existing POI
        for poi in self._pois.values():
            if np.linalg.norm(poi.position - point) < self._grid.resolution * 2:
                poi.last_seen = obs.timestamp
                poi.observations += 1
                poi.confidence = min(1.0, poi.confidence + 0.05)
                return
        # New POI if cell is reliably occupied
        if self._grid.get_probability(point) > 0.7:
            self._poi_counter += 1
            poi = PointOfInterest(
                poi_id=f"POI-{self._poi_counter:04d}", position=point.copy(),
                category="obstacle", confidence=obs.confidence,
                first_seen=obs.timestamp, last_seen=obs.timestamp,
            )
            self._pois[poi.poi_id] = poi

    def query_area(self, center: np.ndarray, radius: float) -> Dict[str, CellState]:
        """영역 내 셀 상태 조회."""
        results = {}
        n = int(radius / self._grid.resolution)
        for dx in range(-n, n + 1):
            for dy in range(-n, n + 1):
                pos = center + np.array([dx * self._grid.resolution, dy * self._grid.resolution, center[2] if len(center) > 2 else 0])
                if np.linalg.norm(pos[:2] - center[:2]) <= radius:
                    key = f"{int(pos[0])},{int(pos[1])}"
                    results[key] = self._grid.get_state(pos)
        return results

    def get_pois(self, category: Optional[str] = None, min_confidence: float = 0.0) -> List[PointOfInterest]:
        pois = list(self._pois.values())
        if category:
            pois = [p for p in pois if p.category == category]
        pois = [p for p in pois if p.confidence >= min_confidence]
        return pois

    def merge_map(self, other_observations: List[MapObservation]):
        for obs in other_observations:
            self.process_observation(obs)

    def get_exploration_progress(self) -> float:
        return self._grid.get_explored_ratio()

    def summary(self) -> dict:
        return {
            "total_observations": len(self._observations),
            "tracked_drones": len(self._drone_positions),
            "total_pois": len(self._pois),
            "exploration_ratio": round(self.get_exploration_progress() * 100, 2),
            "grid_size": self._grid.size,
            "resolution_m": self._grid.resolution,
        }
