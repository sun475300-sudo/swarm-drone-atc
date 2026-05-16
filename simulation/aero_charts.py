"""Phase 697: 항공 차트(VFR/sectional) 데이터베이스."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class ChartFeatureType(Enum):
    AIRPORT = "airport"
    HELIPAD = "helipad"
    VERTIPORT = "vertiport"
    OBSTACLE = "obstacle"
    RADIO_TOWER = "radio_tower"
    AIRSPACE_BOUNDARY = "airspace_boundary"
    VOR = "vor"
    WAYPOINT = "waypoint"


@dataclass(frozen=True)
class ChartFeature:
    feature_id: str
    feature_type: ChartFeatureType
    position: Tuple[float, float]
    altitude_m: float = 0.0
    name: str = ""
    extra: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)


class AeroCharts:
    """비행 계획/경로 검증을 위한 항공 차트 인메모리 DB."""

    def __init__(self) -> None:
        self.features: Dict[str, ChartFeature] = {}

    def add_feature(self, feature: ChartFeature) -> None:
        self.features[feature.feature_id] = feature

    def bulk_add(self, features: List[ChartFeature]) -> int:
        for f in features:
            self.features[f.feature_id] = f
        return len(features)

    def remove(self, feature_id: str) -> bool:
        if feature_id in self.features:
            del self.features[feature_id]
            return True
        return False

    def get(self, feature_id: str) -> Optional[ChartFeature]:
        return self.features.get(feature_id)

    def nearby(
        self,
        position: Tuple[float, float],
        radius_m: float,
        feature_type: Optional[ChartFeatureType] = None,
    ) -> List[ChartFeature]:
        if radius_m <= 0:
            return []
        out: List[ChartFeature] = []
        for f in self.features.values():
            if feature_type is not None and f.feature_type != feature_type:
                continue
            dx = f.position[0] - position[0]
            dy = f.position[1] - position[1]
            if np.sqrt(dx * dx + dy * dy) <= radius_m:
                out.append(f)
        return out

    def nearest(
        self, position: Tuple[float, float], feature_type: Optional[ChartFeatureType] = None
    ) -> Optional[ChartFeature]:
        best: Optional[ChartFeature] = None
        best_d = float("inf")
        for f in self.features.values():
            if feature_type is not None and f.feature_type != feature_type:
                continue
            dx = f.position[0] - position[0]
            dy = f.position[1] - position[1]
            d = np.sqrt(dx * dx + dy * dy)
            if d < best_d:
                best_d = d
                best = f
        return best

    def path_obstacles(
        self,
        waypoints: List[Tuple[float, float]],
        corridor_width_m: float,
        min_altitude_m: float = 0.0,
    ) -> List[ChartFeature]:
        if corridor_width_m < 0:
            raise ValueError(
                f"corridor_width_m must be non-negative, got {corridor_width_m}"
            )
        hazards: List[ChartFeature] = []
        seen: set[str] = set()
        for a, b in zip(waypoints[:-1], waypoints[1:]):
            for f in self.features.values():
                if f.feature_id in seen:
                    continue
                if f.feature_type not in (
                    ChartFeatureType.OBSTACLE, ChartFeatureType.RADIO_TOWER
                ):
                    continue
                if f.altitude_m < min_altitude_m:
                    continue
                if self._segment_distance(a, b, f.position) <= corridor_width_m:
                    hazards.append(f)
                    seen.add(f.feature_id)
        return hazards

    @staticmethod
    def _segment_distance(
        a: Tuple[float, float], b: Tuple[float, float], p: Tuple[float, float]
    ) -> float:
        ax, ay = a
        bx, by = b
        px, py = p
        dx = bx - ax
        dy = by - ay
        denom = dx * dx + dy * dy
        if denom == 0:
            return float(np.sqrt((px - ax) ** 2 + (py - ay) ** 2))
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
        cx = ax + t * dx
        cy = ay + t * dy
        return float(np.sqrt((px - cx) ** 2 + (py - cy) ** 2))

    def stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for f in self.features.values():
            counts[f.feature_type.value] = counts.get(f.feature_type.value, 0) + 1
        return {
            "total": len(self.features),
            "by_type": counts,
        }
