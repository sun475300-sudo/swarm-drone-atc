"""
비행 복도 관리
==============
단방향/양방향 복도 + 진입/이탈 프로토콜.

사용법:
    fc = FlightCorridorManager()
    fc.add_corridor("C1", start=(0, 0), end=(1000, 0), width=100)
    ok = fc.request_entry("d1", "C1", direction="FORWARD")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class FlightCorridor:
    """비행 복도"""
    corridor_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    width: float = 100.0
    altitude_range: tuple[float, float] = (30, 120)
    direction: str = "BIDIRECTIONAL"  # FORWARD, REVERSE, BIDIRECTIONAL
    max_drones: int = 10
    occupants: list[str] = field(default_factory=list)
    active: bool = True


class FlightCorridorManager:
    """비행 복도 관리."""

    def __init__(self) -> None:
        self._corridors: dict[str, FlightCorridor] = {}

    def add_corridor(
        self,
        corridor_id: str,
        start: tuple[float, float],
        end: tuple[float, float],
        width: float = 100.0,
        direction: str = "BIDIRECTIONAL",
        max_drones: int = 10,
        altitude_range: tuple[float, float] = (30, 120),
    ) -> FlightCorridor:
        corridor = FlightCorridor(
            corridor_id=corridor_id,
            start=start, end=end,
            width=width, direction=direction,
            max_drones=max_drones,
            altitude_range=altitude_range,
        )
        self._corridors[corridor_id] = corridor
        return corridor

    def request_entry(
        self,
        drone_id: str,
        corridor_id: str,
        direction: str = "FORWARD",
    ) -> bool:
        """복도 진입 요청"""
        corridor = self._corridors.get(corridor_id)
        if not corridor or not corridor.active:
            return False
        if len(corridor.occupants) >= corridor.max_drones:
            return False
        if corridor.direction != "BIDIRECTIONAL" and corridor.direction != direction:
            return False
        if drone_id not in corridor.occupants:
            corridor.occupants.append(drone_id)
        return True

    def exit_corridor(self, drone_id: str, corridor_id: str) -> bool:
        corridor = self._corridors.get(corridor_id)
        if not corridor:
            return False
        if drone_id in corridor.occupants:
            corridor.occupants.remove(drone_id)
            return True
        return False

    def is_in_corridor(
        self,
        position: tuple[float, float, float],
        corridor_id: str,
    ) -> bool:
        """위치가 복도 내인지 판정"""
        corridor = self._corridors.get(corridor_id)
        if not corridor:
            return False

        # 고도 검사
        if position[2] < corridor.altitude_range[0] or position[2] > corridor.altitude_range[1]:
            return False

        # 복도 중심선까지 거리
        s = np.array(corridor.start)
        e = np.array(corridor.end)
        p = np.array(position[:2])

        line_vec = e - s
        line_len = np.linalg.norm(line_vec)
        if line_len < 1e-6:
            return float(np.linalg.norm(p - s)) <= corridor.width / 2

        # 투영
        t = float(np.dot(p - s, line_vec) / (line_len * line_len))
        t = max(0, min(1, t))
        closest = s + t * line_vec
        dist = float(np.linalg.norm(p - closest))

        return dist <= corridor.width / 2

    def find_corridor(
        self, position: tuple[float, float, float],
    ) -> str | None:
        """현재 위치의 복도 ID"""
        for cid, corridor in self._corridors.items():
            if corridor.active and self.is_in_corridor(position, cid):
                return cid
        return None

    def corridor_utilization(self, corridor_id: str) -> float:
        corridor = self._corridors.get(corridor_id)
        if not corridor:
            return 0.0
        return len(corridor.occupants) / max(corridor.max_drones, 1)

    def corridor_length(self, corridor_id: str) -> float:
        corridor = self._corridors.get(corridor_id)
        if not corridor:
            return 0.0
        return float(np.linalg.norm(
            np.array(corridor.end) - np.array(corridor.start)
        ))

    def summary(self) -> dict[str, Any]:
        active = [c for c in self._corridors.values() if c.active]
        return {
            "total_corridors": len(self._corridors),
            "active_corridors": len(active),
            "total_occupants": sum(len(c.occupants) for c in active),
            "avg_utilization": round(
                sum(self.corridor_utilization(c.corridor_id) for c in active)
                / max(len(active), 1), 3
            ),
        }
