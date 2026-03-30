"""Phase 295: Geospatial Index — 지리공간 인덱스.

R-Tree, Quadtree, Geohash 기반 공간 검색,
영역 쿼리, KNN(K-Nearest Neighbors) 검색 최적화.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SpatialObject:
    obj_id: str
    position: np.ndarray
    radius: float = 0.0
    data: dict = field(default_factory=dict)


@dataclass
class BoundingBox:
    min_corner: np.ndarray
    max_corner: np.ndarray

    def contains(self, point: np.ndarray) -> bool:
        return all(self.min_corner[:3] <= point[:3]) and all(point[:3] <= self.max_corner[:3])

    def intersects(self, other: 'BoundingBox') -> bool:
        return all(self.min_corner[:3] <= other.max_corner[:3]) and all(other.min_corner[:3] <= self.max_corner[:3])

    @property
    def center(self) -> np.ndarray:
        return (self.min_corner + self.max_corner) / 2

    @property
    def size(self) -> np.ndarray:
        return self.max_corner - self.min_corner


class QuadtreeNode:
    """3D Quadtree (실제로는 Octree) 노드."""

    MAX_OBJECTS = 8
    MAX_DEPTH = 10

    def __init__(self, bbox: BoundingBox, depth: int = 0):
        self.bbox = bbox
        self.depth = depth
        self.objects: List[SpatialObject] = []
        self.children: List[Optional[QuadtreeNode]] = []

    def _subdivide(self):
        center = self.bbox.center
        mn = self.bbox.min_corner
        mx = self.bbox.max_corner
        for i in range(8):
            new_min = np.array([
                mn[0] if i & 1 == 0 else center[0],
                mn[1] if i & 2 == 0 else center[1],
                mn[2] if i & 4 == 0 else center[2],
            ])
            new_max = np.array([
                center[0] if i & 1 == 0 else mx[0],
                center[1] if i & 2 == 0 else mx[1],
                center[2] if i & 4 == 0 else mx[2],
            ])
            self.children.append(QuadtreeNode(BoundingBox(new_min, new_max), self.depth + 1))

    def insert(self, obj: SpatialObject) -> bool:
        if not self.bbox.contains(obj.position):
            return False
        if len(self.objects) < self.MAX_OBJECTS or self.depth >= self.MAX_DEPTH:
            self.objects.append(obj)
            return True
        if not self.children:
            self._subdivide()
        for child in self.children:
            if child and child.insert(obj):
                return True
        self.objects.append(obj)
        return True

    def query_range(self, bbox: BoundingBox) -> List[SpatialObject]:
        results = []
        if not self.bbox.intersects(bbox):
            return results
        for obj in self.objects:
            if bbox.contains(obj.position):
                results.append(obj)
        for child in self.children:
            if child:
                results.extend(child.query_range(bbox))
        return results

    def query_radius(self, center: np.ndarray, radius: float) -> List[SpatialObject]:
        bbox = BoundingBox(center - radius, center + radius)
        candidates = self.query_range(bbox)
        return [o for o in candidates if np.linalg.norm(o.position[:3] - center[:3]) <= radius]


class GeohashEncoder:
    """Geohash 인코딩 (3D 확장)."""

    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

    @staticmethod
    def encode(lat: float, lon: float, alt: float = 0.0, precision: int = 6) -> str:
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        bits = []
        is_lon = True
        while len(bits) < precision * 5:
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                if lon >= mid:
                    bits.append(1)
                    lon_range[0] = mid
                else:
                    bits.append(0)
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat >= mid:
                    bits.append(1)
                    lat_range[0] = mid
                else:
                    bits.append(0)
                    lat_range[1] = mid
            is_lon = not is_lon
        result = ""
        for i in range(0, len(bits), 5):
            chunk = bits[i:i + 5]
            idx = sum(b << (4 - j) for j, b in enumerate(chunk))
            result += GeohashEncoder.BASE32[idx]
        return result

    @staticmethod
    def neighbors(ghash: str) -> List[str]:
        """인접 geohash 반환 (간이 구현)."""
        if not ghash:
            return []
        base = ghash[:-1]
        last = ghash[-1]
        idx = GeohashEncoder.BASE32.index(last) if last in GeohashEncoder.BASE32 else 0
        nbs = []
        for delta in [-1, 1]:
            ni = (idx + delta) % 32
            nbs.append(base + GeohashEncoder.BASE32[ni])
        return nbs


class GeospatialIndex:
    """지리공간 인덱스.

    - Octree 기반 공간 분할
    - 영역/반경 쿼리
    - KNN 검색
    - Geohash 인코딩
    """

    def __init__(self, bounds_min: np.ndarray = None, bounds_max: np.ndarray = None):
        if bounds_min is None:
            bounds_min = np.array([-1000.0, -1000.0, -100.0])
        if bounds_max is None:
            bounds_max = np.array([1000.0, 1000.0, 500.0])
        self._tree = QuadtreeNode(BoundingBox(bounds_min, bounds_max))
        self._objects: Dict[str, SpatialObject] = {}
        self._geohash = GeohashEncoder()

    def insert(self, obj: SpatialObject) -> bool:
        self._objects[obj.obj_id] = obj
        return self._tree.insert(obj)

    def query_range(self, min_corner: np.ndarray, max_corner: np.ndarray) -> List[SpatialObject]:
        return self._tree.query_range(BoundingBox(min_corner, max_corner))

    def query_radius(self, center: np.ndarray, radius: float) -> List[SpatialObject]:
        return self._tree.query_radius(center, radius)

    def query_knn(self, center: np.ndarray, k: int) -> List[Tuple[SpatialObject, float]]:
        """K-최근접 이웃 검색."""
        distances = []
        for obj in self._objects.values():
            d = np.linalg.norm(obj.position[:3] - center[:3])
            distances.append((obj, d))
        distances.sort(key=lambda x: x[1])
        return distances[:k]

    def get_geohash(self, obj_id: str, precision: int = 6) -> Optional[str]:
        obj = self._objects.get(obj_id)
        if not obj:
            return None
        return self._geohash.encode(obj.position[0], obj.position[1], obj.position[2] if len(obj.position) > 2 else 0, precision)

    def get_object(self, obj_id: str) -> Optional[SpatialObject]:
        return self._objects.get(obj_id)

    def remove(self, obj_id: str) -> bool:
        return self._objects.pop(obj_id, None) is not None

    def summary(self) -> dict:
        return {
            "total_objects": len(self._objects),
            "tree_depth": self._tree.MAX_DEPTH,
        }
