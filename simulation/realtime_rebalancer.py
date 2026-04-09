"""
실시간 리밸런싱
==============
공역 밀도 편향 감지 + 드론 재배치 명령.

사용법:
    rb = RealtimeRebalancer(grid_size=5)
    rb.update_positions({"d1": (100,200,50), "d2": (800,800,50)})
    actions = rb.rebalance()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class RebalanceAction:
    """재배치 명령"""
    drone_id: str
    from_sector: tuple[int, int]
    to_sector: tuple[int, int]
    reason: str


class RealtimeRebalancer:
    """실시간 공역 리밸런싱."""

    def __init__(self, grid_size: int = 5, area_size: float = 1000.0, imbalance_threshold: float = 2.0) -> None:
        self.grid_size = grid_size
        self.area_size = area_size
        self.imbalance_threshold = imbalance_threshold
        self._positions: dict[str, tuple[float, float, float]] = {}
        self._actions: list[RebalanceAction] = []

    def update_positions(self, positions: dict[str, tuple[float, float, float]]) -> None:
        self._positions.update(positions)

    def _sector_of(self, pos: tuple[float, float, float]) -> tuple[int, int]:
        cell = self.area_size / self.grid_size
        return (int(pos[0] / max(cell, 1)), int(pos[1] / max(cell, 1)))

    def density_map(self) -> dict[tuple[int, int], int]:
        dm: dict[tuple[int, int], int] = {}
        for pos in self._positions.values():
            s = self._sector_of(pos)
            dm[s] = dm.get(s, 0) + 1
        return dm

    def rebalance(self) -> list[RebalanceAction]:
        dm = self.density_map()
        if not dm:
            return []

        counts = list(dm.values())
        avg = np.mean(counts) if counts else 0

        overfull = [(s, c) for s, c in dm.items() if c > avg * self.imbalance_threshold]
        underfull = [(s, c) for s, c in dm.items() if c < avg * 0.5]

        actions = []
        for over_sec, over_count in overfull:
            if not underfull:
                break
            drones_in_sector = [
                did for did, pos in self._positions.items()
                if self._sector_of(pos) == over_sec
            ]
            excess = int(over_count - avg)
            for i in range(min(excess, len(drones_in_sector), len(underfull))):
                target = underfull[i % len(underfull)][0]
                action = RebalanceAction(
                    drone_id=drones_in_sector[i],
                    from_sector=over_sec,
                    to_sector=target,
                    reason=f"밀도 불균형 ({over_count} → avg {avg:.0f})",
                )
                actions.append(action)

        self._actions.extend(actions)
        return actions

    def imbalance_score(self) -> float:
        dm = self.density_map()
        if not dm:
            return 0.0
        counts = list(dm.values())
        return round(float(np.std(counts) / max(np.mean(counts), 1)), 3)

    def summary(self) -> dict[str, Any]:
        return {
            "drones": len(self._positions),
            "sectors_occupied": len(self.density_map()),
            "imbalance_score": self.imbalance_score(),
            "total_rebalances": len(self._actions),
        }
