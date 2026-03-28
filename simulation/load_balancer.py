"""
부하 분산기
==========
섹터 간 드론 재배치 + 핫스팟 완화 + 밀도 균등화.

사용법:
    lb = LoadBalancer(sectors=(3, 3), bounds=(0, 0, 900, 900))
    lb.update(positions)
    moves = lb.rebalance()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class RebalanceAction:
    """재배치 액션"""
    drone_id: str
    from_sector: str
    to_sector: str
    suggested_position: tuple[float, float, float]
    reason: str


class LoadBalancer:
    """섹터 간 부하 분산."""

    def __init__(
        self,
        bounds: tuple[float, float, float, float] = (0, 0, 900, 900),
        sectors: tuple[int, int] = (3, 3),
        target_density: int = 10,
        imbalance_threshold: float = 0.5,
    ) -> None:
        self.bounds = bounds
        self.n_rows, self.n_cols = sectors
        self.target = target_density
        self.threshold = imbalance_threshold
        self._positions: dict[str, tuple[float, float, float]] = {}
        self._sector_counts: dict[str, int] = {}

    def update(
        self, positions: dict[str, tuple[float, float, float]]
    ) -> None:
        self._positions = dict(positions)
        self._sector_counts.clear()
        for r in range(self.n_rows):
            for c in range(self.n_cols):
                self._sector_counts[f"S{r}{c}"] = 0
        for pos in positions.values():
            sid = self._get_sector(pos[0], pos[1])
            if sid:
                self._sector_counts[sid] = self._sector_counts.get(sid, 0) + 1

    def imbalance_score(self) -> float:
        """불균형 점수 (0=균형, 1=극불균형)"""
        counts = list(self._sector_counts.values())
        if not counts or max(counts) == 0:
            return 0.0
        return float((max(counts) - min(counts)) / max(max(counts), 1))

    def hotspots(self) -> list[str]:
        """핫스팟 섹터 (평균 대비 threshold 이상)"""
        counts = list(self._sector_counts.values())
        if not counts:
            return []
        avg = np.mean(counts)
        return [
            sid for sid, cnt in self._sector_counts.items()
            if cnt > avg * (1 + self.threshold)
        ]

    def coldspots(self) -> list[str]:
        """여유 섹터"""
        counts = list(self._sector_counts.values())
        if not counts:
            return []
        avg = np.mean(counts)
        return [
            sid for sid, cnt in self._sector_counts.items()
            if cnt < avg * (1 - self.threshold * 0.5)
        ]

    def rebalance(self, max_moves: int = 5) -> list[RebalanceAction]:
        """재배치 계획 생성"""
        hot = self.hotspots()
        cold = self.coldspots()

        if not hot or not cold:
            return []

        actions = []
        moves = 0

        for h_sid in hot:
            if moves >= max_moves:
                break
            # 이 섹터의 드론 찾기
            drones_in = [
                (did, pos) for did, pos in self._positions.items()
                if self._get_sector(pos[0], pos[1]) == h_sid
            ]
            for c_sid in cold:
                if moves >= max_moves:
                    break
                if self._sector_counts.get(c_sid, 0) >= self.target:
                    continue

                if drones_in:
                    did, _ = drones_in.pop()
                    target_pos = self._sector_center(c_sid)

                    actions.append(RebalanceAction(
                        drone_id=did,
                        from_sector=h_sid,
                        to_sector=c_sid,
                        suggested_position=(*target_pos, 60.0),
                        reason=f"핫스팟 {h_sid} → 여유 {c_sid}",
                    ))
                    moves += 1

        return actions

    def _get_sector(self, x: float, y: float) -> str:
        x_min, y_min, x_max, y_max = self.bounds
        dx = (x_max - x_min) / self.n_cols
        dy = (y_max - y_min) / self.n_rows
        col = max(0, min(int((x - x_min) / dx), self.n_cols - 1))
        row = max(0, min(int((y - y_min) / dy), self.n_rows - 1))
        return f"S{row}{col}"

    def _sector_center(self, sid: str) -> tuple[float, float]:
        r, c = int(sid[1]), int(sid[2])
        x_min, y_min, x_max, y_max = self.bounds
        dx = (x_max - x_min) / self.n_cols
        dy = (y_max - y_min) / self.n_rows
        return (x_min + (c + 0.5) * dx, y_min + (r + 0.5) * dy)

    def summary(self) -> dict[str, Any]:
        return {
            "total_drones": len(self._positions),
            "imbalance": round(self.imbalance_score(), 3),
            "hotspots": self.hotspots(),
            "coldspots": self.coldspots(),
            "sector_counts": dict(self._sector_counts),
        }
