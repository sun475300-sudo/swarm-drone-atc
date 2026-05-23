"""Phase 697: 항공 차트(VFR/sectional) 데이터베이스."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

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
    position: tuple[float, float]
    altitude_m: float = 0.0
    name: str = ""
    extra: tuple[tuple[str, str], ...] = field(default_factory=tuple)


class AeroCharts:
    """비행 계획/경로 검증을 위한 항공 차트 인메모리 DB."""

    def __init__(self) -> None:
        self.features: dict[str, ChartFeature] = {}

    @staticmethod
    def _validate_feature_position(pos: tuple[float, float]) -> None:
        if len(pos) != 2:
            raise ValueError(
                f"position must be a 2-element (lat, lon) tuple, got {len(pos)} elements"
            )
        if not math.isfinite(pos[0]) or not math.isfinite(pos[1]):
            raise ValueError(f"position coordinates must be finite, got {pos}")

    def add_feature(self, feature: ChartFeature) -> None:
        self._validate_feature_position(feature.position)
        self.features[feature.feature_id] = feature

    def bulk_add(self, features: list[ChartFeature]) -> int:
        """피처를 일괄 추가한다. 중복 feature_id(기존 차트 내 또는 입력 목록 내)는 ValueError.

        반환값: 새로 추가된 피처 수.
        """
        seen_in_batch: set[str] = set()
        for f in features:
            self._validate_feature_position(f.position)
            if f.feature_id in self.features or f.feature_id in seen_in_batch:
                raise ValueError(
                    f"duplicate feature_id {f.feature_id!r} in bulk_add"
                )
            seen_in_batch.add(f.feature_id)
        for f in features:
            self.features[f.feature_id] = f
        return len(features)

    def remove(self, feature_id: str) -> bool:
        if feature_id in self.features:
            del self.features[feature_id]
            return True
        return False

    def get(self, feature_id: str) -> ChartFeature | None:
        return self.features.get(feature_id)

    def nearby(
        self,
        position: tuple[float, float],
        radius_m: float,
        feature_type: ChartFeatureType | None = None,
    ) -> list[ChartFeature]:
        if radius_m < 0:
            raise ValueError(f"radius_m must be non-negative, got {radius_m}")
        self._validate_feature_position(position)
        out: list[ChartFeature] = []
        for f in self.features.values():
            if feature_type is not None and f.feature_type != feature_type:
                continue
            dx = f.position[0] - position[0]
            dy = f.position[1] - position[1]
            if np.sqrt(dx * dx + dy * dy) <= radius_m:
                out.append(f)
        return out

    def nearest(
        self, position: tuple[float, float], feature_type: ChartFeatureType | None = None
    ) -> ChartFeature | None:
        """Return the nearest feature to position, or None if no features match.

        If feature_type is specified, only features of that type are considered.
        Returns None if features dict is empty or no feature matches the type filter.
        """
        self._validate_feature_position(position)
        best: ChartFeature | None = None
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
        waypoints: list[tuple[float, float]],
        corridor_width_m: float,
        min_altitude_m: float = 0.0,
    ) -> list[ChartFeature]:
        if corridor_width_m < 0:
            raise ValueError(
                f"corridor_width_m must be non-negative, got {corridor_width_m}"
            )
        if len(waypoints) < 2:
            raise ValueError(
                f"path_obstacles requires at least 2 waypoints to define a path segment, "
                f"got {len(waypoints)}"
            )
        hazards: list[ChartFeature] = []
        seen: set[str] = set()
        for a, b in zip(waypoints[:-1], waypoints[1:], strict=False):
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
        a: tuple[float, float], b: tuple[float, float], p: tuple[float, float]
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

    def stats(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for f in self.features.values():
            counts[f.feature_type.value] = counts.get(f.feature_type.value, 0) + 1
        return {
            "total": len(self.features),
            "by_type": counts,
        }
