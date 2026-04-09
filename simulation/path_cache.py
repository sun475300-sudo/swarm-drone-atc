"""
경로 캐시
=========
출발-도착 경로 LRU 캐시 + 히트율 + 무효화.

사용법:
    pc = PathCache(max_size=100)
    pc.put("A→B", waypoints)
    cached = pc.get("A→B")
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheStats:
    """캐시 통계"""
    hits: int
    misses: int
    evictions: int
    size: int
    hit_rate: float


class PathCache:
    """경로 LRU 캐시."""

    def __init__(self, max_size: int = 200) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, list[tuple[float, float, float]]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _make_key(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        resolution: float = 50.0,
    ) -> str:
        """위치를 그리드 스냅하여 키 생성"""
        def snap(v: float) -> int:
            return int(round(v / resolution))
        s = (snap(start[0]), snap(start[1]), snap(start[2]))
        e = (snap(end[0]), snap(end[1]), snap(end[2]))
        return f"{s}->{e}"

    def get(self, key: str) -> list[tuple[float, float, float]] | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def get_by_positions(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
    ) -> list[tuple[float, float, float]] | None:
        key = self._make_key(start, end)
        return self.get(key)

    def put(self, key: str, path: list[tuple[float, float, float]]) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = path
            return

        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
            self._evictions += 1

        self._cache[key] = path

    def put_by_positions(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        path: list[tuple[float, float, float]],
    ) -> str:
        key = self._make_key(start, end)
        self.put(key, path)
        return key

    def invalidate(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_region(
        self,
        center: tuple[float, float],
        radius: float,
    ) -> int:
        """특정 지역 근처 캐시 무효화"""
        to_remove = []
        for key in self._cache:
            # 키에서 좌표 파싱 시도
            path = self._cache[key]
            if path:
                for wp in [path[0], path[-1]]:
                    dx = wp[0] - center[0]
                    dy = wp[1] - center[1]
                    if (dx*dx + dy*dy) < radius*radius:
                        to_remove.append(key)
                        break

        for key in to_remove:
            del self._cache[key]
        return len(to_remove)

    def clear(self) -> None:
        self._cache.clear()

    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / max(total, 1)

    def stats(self) -> CacheStats:
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            size=len(self._cache),
            hit_rate=self.hit_rate(),
        )

    def summary(self) -> dict[str, Any]:
        s = self.stats()
        return {
            "size": s.size,
            "max_size": self._max_size,
            "hit_rate": round(s.hit_rate, 3),
            "hits": s.hits,
            "misses": s.misses,
            "evictions": s.evictions,
        }
