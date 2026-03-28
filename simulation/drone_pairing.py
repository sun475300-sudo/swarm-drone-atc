"""
드론 페어링
===========
2대 협업 페어링 + 호위/릴레이/탐색 패턴.

사용법:
    dp = DronePairing()
    dp.pair("d1", "d2", mode="ESCORT")
    status = dp.pair_status("d1")
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class PairInfo:
    """페어 정보"""
    pair_id: str
    drone_a: str
    drone_b: str
    mode: str  # ESCORT, RELAY, SEARCH, FORMATION
    active: bool = True
    distance_m: float = 0.0


class DronePairing:
    """드론 페어링 관리."""

    def __init__(self, max_pair_distance: float = 500.0) -> None:
        self._pairs: dict[str, PairInfo] = {}
        self._drone_to_pair: dict[str, str] = {}
        self._max_distance = max_pair_distance
        self._counter = 0

    def pair(self, drone_a: str, drone_b: str, mode: str = "ESCORT") -> PairInfo:
        self._counter += 1
        pid = f"P{self._counter:04d}"
        info = PairInfo(pair_id=pid, drone_a=drone_a, drone_b=drone_b, mode=mode)
        self._pairs[pid] = info
        self._drone_to_pair[drone_a] = pid
        self._drone_to_pair[drone_b] = pid
        return info

    def unpair(self, pair_id: str) -> bool:
        info = self._pairs.get(pair_id)
        if not info:
            return False
        info.active = False
        self._drone_to_pair.pop(info.drone_a, None)
        self._drone_to_pair.pop(info.drone_b, None)
        return True

    def get_partner(self, drone_id: str) -> str | None:
        pid = self._drone_to_pair.get(drone_id)
        if not pid:
            return None
        info = self._pairs.get(pid)
        if not info or not info.active:
            return None
        return info.drone_b if info.drone_a == drone_id else info.drone_a

    def pair_status(self, drone_id: str) -> PairInfo | None:
        pid = self._drone_to_pair.get(drone_id)
        if pid:
            info = self._pairs.get(pid)
            if info and info.active:
                return info
        return None

    def update_positions(
        self, positions: dict[str, tuple[float, float, float]],
    ) -> list[str]:
        """거리 업데이트, 초과 시 경고 반환"""
        warnings = []
        for pid, info in self._pairs.items():
            if not info.active:
                continue
            pos_a = positions.get(info.drone_a)
            pos_b = positions.get(info.drone_b)
            if pos_a and pos_b:
                dist = float(np.linalg.norm(
                    np.array(pos_a) - np.array(pos_b)
                ))
                info.distance_m = dist
                if dist > self._max_distance:
                    warnings.append(pid)
        return warnings

    def active_pairs(self) -> list[PairInfo]:
        return [p for p in self._pairs.values() if p.active]

    def by_mode(self, mode: str) -> list[PairInfo]:
        return [p for p in self._pairs.values() if p.active and p.mode == mode]

    def suggest_pair(
        self, positions: dict[str, tuple[float, float, float]],
        mode: str = "ESCORT",
    ) -> tuple[str, str] | None:
        """가장 가까운 미페어링 드론 쌍 제안"""
        unpaired = [d for d in positions if d not in self._drone_to_pair]
        if len(unpaired) < 2:
            return None

        best_dist = float("inf")
        best_pair = None
        for i in range(len(unpaired)):
            for j in range(i + 1, len(unpaired)):
                dist = float(np.linalg.norm(
                    np.array(positions[unpaired[i]]) - np.array(positions[unpaired[j]])
                ))
                if dist < best_dist:
                    best_dist = dist
                    best_pair = (unpaired[i], unpaired[j])
        return best_pair

    def summary(self) -> dict[str, Any]:
        active = self.active_pairs()
        by_mode: dict[str, int] = {}
        for p in active:
            by_mode[p.mode] = by_mode.get(p.mode, 0) + 1
        return {
            "total_pairs": len(self._pairs),
            "active_pairs": len(active),
            "by_mode": by_mode,
            "avg_distance": round(
                np.mean([p.distance_m for p in active]) if active else 0, 1
            ),
        }
