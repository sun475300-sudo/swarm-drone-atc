"""
3D Spatial Hash Grid — O(N²) → O(N·k) 근접 쿼리 최적화

사용 예:
    sh = SpatialHash(cell_size=50.0)
    sh.clear()
    for did, pos in drones.items():
        sh.insert(did, pos)
    neighbors = sh.query_pairs(radius=50.0)  # → set of frozenset pairs
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterator

import numpy as np


class SpatialHash:
    """
    3D 공간 해싱 그리드.

    Parameters
    ----------
    cell_size : float
        셀 한 변의 길이 (m). 분리 기준과 동일하게 설정 권장.
    """

    __slots__ = ("_cell_size", "_inv_cell", "_grid", "_positions")

    def __init__(self, cell_size: float = 50.0) -> None:
        self._cell_size = cell_size
        self._inv_cell = 1.0 / cell_size
        self._grid: dict[tuple[int, int, int], list[str]] = defaultdict(list)
        self._positions: dict[str, np.ndarray] = {}

    def clear(self) -> None:
        self._grid.clear()
        self._positions.clear()

    def _key(self, pos: np.ndarray) -> tuple[int, int, int]:
        return (
            int(np.floor(pos[0] * self._inv_cell)),
            int(np.floor(pos[1] * self._inv_cell)),
            int(np.floor(pos[2] * self._inv_cell)),
        )

    def insert(self, drone_id: str, position: np.ndarray) -> None:
        self._positions[drone_id] = position
        self._grid[self._key(position)].append(drone_id)

    def query_radius(self, position: np.ndarray, radius: float) -> list[str]:
        """주어진 위치에서 radius 이내의 모든 drone_id 반환."""
        r_cells = int(np.ceil(radius * self._inv_cell))
        cx, cy, cz = self._key(position)
        result: list[str] = []
        r2 = radius * radius

        for dx in range(-r_cells, r_cells + 1):
            for dy in range(-r_cells, r_cells + 1):
                for dz in range(-r_cells, r_cells + 1):
                    cell = self._grid.get((cx + dx, cy + dy, cz + dz))
                    if cell is None:
                        continue
                    for did in cell:
                        p = self._positions[did]
                        d = p - position
                        if d[0]*d[0] + d[1]*d[1] + d[2]*d[2] <= r2:
                            result.append(did)
        return result

    def query_pairs(self, radius: float) -> set[tuple[str, str]]:
        """
        radius 이내에 있는 모든 드론 쌍 반환.
        O(N * k) — k는 평균 이웃 수.
        sorted tuple로 중복 방지 (frozenset 대비 해싱 오버헤드 감소).
        """
        r2 = radius * radius
        pairs: set[tuple[str, str]] = set()

        for did, pos in self._positions.items():
            neighbors = self.query_radius(pos, radius)
            for nid in neighbors:
                if nid != did:
                    pair = (did, nid) if did < nid else (nid, did)
                    pairs.add(pair)
        return pairs

    def query_pairs_with_dist(
        self, radius: float
    ) -> Iterator[tuple[str, str, float]]:
        """
        radius 이내 쌍 + 거리 반환 (중복 제거).
        sorted tuple로 해싱 최적화.
        """
        r2 = radius * radius
        seen: set[tuple[str, str]] = set()

        for did, pos in self._positions.items():
            cx, cy, cz = self._key(pos)
            r_cells = int(np.ceil(radius * self._inv_cell))

            for dx in range(-r_cells, r_cells + 1):
                for dy in range(-r_cells, r_cells + 1):
                    for dz in range(-r_cells, r_cells + 1):
                        cell = self._grid.get((cx + dx, cy + dy, cz + dz))
                        if cell is None:
                            continue
                        for nid in cell:
                            if nid == did:
                                continue
                            pair = (did, nid) if did < nid else (nid, did)
                            if pair in seen:
                                continue
                            np2 = self._positions[nid]
                            d = pos - np2
                            dist2 = d[0]*d[0] + d[1]*d[1] + d[2]*d[2]
                            if dist2 <= r2:
                                seen.add(pair)
                                yield did, nid, float(np.sqrt(dist2))
