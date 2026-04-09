"""
다중 착륙장 네트워크
===================
착륙장 간 연결 + 트래픽 분산 + 용량 관리.

사용법:
    ln = LandingNetwork()
    ln.add_pad("A1", position=(0, 0), capacity=5)
    best = ln.recommend_pad(drone_pos=(100, 200))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class LandingPad:
    """착륙장"""
    pad_id: str
    position: tuple[float, float]
    capacity: int = 5
    current_occupancy: int = 0
    queue: list[str] = field(default_factory=list)
    total_landings: int = 0


class LandingNetwork:
    """착륙장 네트워크."""

    def __init__(self) -> None:
        self._pads: dict[str, LandingPad] = {}

    def add_pad(self, pad_id: str, position: tuple[float, float], capacity: int = 5) -> None:
        self._pads[pad_id] = LandingPad(pad_id=pad_id, position=position, capacity=capacity)

    def _distance(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        return float(np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2))

    def recommend_pad(self, drone_pos: tuple[float, float], prefer_capacity: bool = True) -> str | None:
        if not self._pads:
            return None

        candidates = []
        for pid, pad in self._pads.items():
            if pad.current_occupancy >= pad.capacity:
                continue
            dist = self._distance(drone_pos, pad.position)
            occupancy_ratio = pad.current_occupancy / max(pad.capacity, 1)
            score = dist * (1 + occupancy_ratio * 2) if prefer_capacity else dist
            candidates.append((pid, score))

        if not candidates:
            # 모든 패드 만석 → 가장 가까운
            candidates = [(pid, self._distance(drone_pos, pad.position)) for pid, pad in self._pads.items()]

        candidates.sort(key=lambda x: x[1])
        return candidates[0][0] if candidates else None

    def land(self, pad_id: str, drone_id: str) -> bool:
        pad = self._pads.get(pad_id)
        if not pad:
            return False
        if pad.current_occupancy >= pad.capacity:
            pad.queue.append(drone_id)
            return False
        pad.current_occupancy += 1
        pad.total_landings += 1
        return True

    def depart(self, pad_id: str) -> str | None:
        pad = self._pads.get(pad_id)
        if not pad:
            return None
        pad.current_occupancy = max(0, pad.current_occupancy - 1)
        if pad.queue:
            next_drone = pad.queue.pop(0)
            pad.current_occupancy += 1
            pad.total_landings += 1
            return next_drone
        return None

    def network_utilization(self) -> float:
        total_cap = sum(p.capacity for p in self._pads.values())
        total_occ = sum(p.current_occupancy for p in self._pads.values())
        return round(total_occ / max(total_cap, 1) * 100, 1)

    def busiest_pad(self) -> str | None:
        if not self._pads:
            return None
        return max(self._pads, key=lambda pid: self._pads[pid].total_landings)

    def summary(self) -> dict[str, Any]:
        return {
            "pads": len(self._pads),
            "utilization": self.network_utilization(),
            "total_queued": sum(len(p.queue) for p in self._pads.values()),
            "total_landings": sum(p.total_landings for p in self._pads.values()),
        }
