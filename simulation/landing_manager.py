"""
착륙 관리자
==========
착륙 패드 할당 + 대기열 관리 + 최소 간격 제어 + 비상 착륙.
패드 점유율 최적화 + 안전 거리 유지.

사용법:
    lm = LandingManager(pads=[LandingPad("P1", (0, 0))])
    lm.request_landing("drone_1", (500, 500, 50))
    assignment = lm.assign_pad("drone_1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class LandingPad:
    """착륙 패드"""
    pad_id: str
    position: tuple[float, float]
    occupied_by: str | None = None
    available: bool = True
    capacity: int = 1
    min_interval_s: float = 10.0  # 최소 착륙 간격
    last_landing_t: float = -100.0


@dataclass
class LandingRequest:
    """착륙 요청"""
    drone_id: str
    position: tuple[float, float, float]
    priority: int = 1  # 높을수록 우선
    t_requested: float = 0.0
    is_emergency: bool = False
    assigned_pad: str | None = None
    status: str = "PENDING"  # PENDING, ASSIGNED, LANDING, COMPLETED, REJECTED


class LandingManager:
    """
    착륙 관리자.

    패드 할당 + 대기열 + 간격 + 비상.
    """

    def __init__(
        self,
        pads: list[LandingPad] | None = None,
        default_interval_s: float = 10.0,
    ) -> None:
        self._pads: dict[str, LandingPad] = {}
        self._queue: list[LandingRequest] = []
        self._completed: list[LandingRequest] = []
        self._default_interval = default_interval_s

        if pads:
            for p in pads:
                self._pads[p.pad_id] = p

    def add_pad(
        self,
        pad_id: str,
        position: tuple[float, float],
        capacity: int = 1,
    ) -> LandingPad:
        pad = LandingPad(
            pad_id=pad_id, position=position,
            capacity=capacity, min_interval_s=self._default_interval,
        )
        self._pads[pad_id] = pad
        return pad

    def request_landing(
        self,
        drone_id: str,
        position: tuple[float, float, float],
        priority: int = 1,
        t: float = 0.0,
        is_emergency: bool = False,
    ) -> LandingRequest:
        """착륙 요청"""
        req = LandingRequest(
            drone_id=drone_id,
            position=position,
            priority=5 if is_emergency else priority,
            t_requested=t,
            is_emergency=is_emergency,
        )
        self._queue.append(req)
        self._queue.sort(key=lambda r: (-r.priority, r.t_requested))
        return req

    def assign_pad(
        self, drone_id: str, t: float = 0.0
    ) -> LandingRequest | None:
        """최적 패드 할당"""
        req = self._find_request(drone_id)
        if not req:
            return None

        best_pad = self._find_nearest_pad(req, t)
        if not best_pad:
            req.status = "REJECTED"
            return req

        req.assigned_pad = best_pad.pad_id
        req.status = "ASSIGNED"
        best_pad.occupied_by = drone_id
        best_pad.available = False

        return req

    def complete_landing(
        self, drone_id: str, t: float = 0.0
    ) -> bool:
        """착륙 완료"""
        req = self._find_request(drone_id)
        if not req or not req.assigned_pad:
            return False

        pad = self._pads.get(req.assigned_pad)
        if pad:
            pad.occupied_by = None
            pad.available = True
            pad.last_landing_t = t

        req.status = "COMPLETED"
        self._queue.remove(req)
        self._completed.append(req)
        return True

    def release_pad(self, pad_id: str) -> None:
        pad = self._pads.get(pad_id)
        if pad:
            pad.occupied_by = None
            pad.available = True

    def available_pads(self, t: float = 0.0) -> list[LandingPad]:
        """사용 가능 패드"""
        return [
            p for p in self._pads.values()
            if p.available and (t - p.last_landing_t) >= p.min_interval_s
        ]

    def queue_length(self) -> int:
        return len(self._queue)

    def pad_utilization(self) -> float:
        """패드 사용률"""
        if not self._pads:
            return 0.0
        occupied = sum(1 for p in self._pads.values() if not p.available)
        return occupied / len(self._pads)

    def emergency_override(
        self, drone_id: str, t: float = 0.0
    ) -> LandingRequest | None:
        """비상 착륙 강제 할당 (기존 점유 해제)"""
        req = self._find_request(drone_id)
        if not req:
            req = self.request_landing(drone_id, (0, 0, 0), t=t, is_emergency=True)

        # 가장 가까운 패드 강제 할당
        pos = np.array(req.position[:2])
        nearest = min(
            self._pads.values(),
            key=lambda p: np.linalg.norm(pos - np.array(p.position)),
        )

        # 기존 점유 해제
        if nearest.occupied_by:
            old_req = self._find_request(nearest.occupied_by)
            if old_req:
                old_req.assigned_pad = None
                old_req.status = "PENDING"

        nearest.occupied_by = drone_id
        nearest.available = False
        req.assigned_pad = nearest.pad_id
        req.status = "ASSIGNED"
        req.is_emergency = True

        return req

    def _find_request(self, drone_id: str) -> LandingRequest | None:
        for req in self._queue:
            if req.drone_id == drone_id:
                return req
        return None

    def _find_nearest_pad(
        self, req: LandingRequest, t: float
    ) -> LandingPad | None:
        """최적 패드 (거리 + 간격 충족)"""
        avail = self.available_pads(t)
        if not avail:
            return None

        pos = np.array(req.position[:2])
        return min(
            avail,
            key=lambda p: np.linalg.norm(pos - np.array(p.position)),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "total_pads": len(self._pads),
            "available_pads": sum(1 for p in self._pads.values() if p.available),
            "queue_length": self.queue_length(),
            "completed": len(self._completed),
            "utilization": round(self.pad_utilization(), 3),
            "emergency_count": sum(
                1 for r in self._queue + self._completed if r.is_emergency
            ),
        }
