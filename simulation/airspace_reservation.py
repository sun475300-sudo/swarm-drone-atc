"""
공역 예약 시스템
================
4D 시공간 슬롯 예약 + 충돌 방지 + 취소.

사용법:
    ar = AirspaceReservation(grid_size=100)
    ok = ar.reserve("d1", sector=(2, 3), t_start=0, t_end=60)
    conflicts = ar.check_conflicts("d2", sector=(2, 3), t_start=30, t_end=90)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Reservation:
    """공역 예약"""
    reservation_id: str
    drone_id: str
    sector: tuple[int, int]
    altitude_band: tuple[float, float]  # (min_alt, max_alt)
    t_start: float
    t_end: float
    priority: int = 3  # 1=highest
    active: bool = True


class AirspaceReservation:
    """4D 공역 슬롯 예약 시스템."""

    def __init__(
        self,
        grid_size: float = 100.0,
        max_reservations: int = 1000,
    ) -> None:
        self._grid_size = grid_size
        self._max_reservations = max_reservations
        self._reservations: dict[str, Reservation] = {}
        self._counter = 0

    def reserve(
        self,
        drone_id: str,
        sector: tuple[int, int],
        t_start: float,
        t_end: float,
        altitude_band: tuple[float, float] = (0, 120),
        priority: int = 3,
    ) -> str | None:
        """예약 생성 (충돌 시 None 반환)"""
        conflicts = self.check_conflicts(drone_id, sector, t_start, t_end, altitude_band)
        # 우선순위가 더 높은 기존 예약이 있으면 거부
        for c in conflicts:
            if c.priority <= priority:
                return None

        self._counter += 1
        rid = f"R{self._counter:05d}"

        # 낮은 우선순위 예약 취소
        for c in conflicts:
            self.cancel(c.reservation_id)

        reservation = Reservation(
            reservation_id=rid,
            drone_id=drone_id,
            sector=sector,
            altitude_band=altitude_band,
            t_start=t_start,
            t_end=t_end,
            priority=priority,
        )
        self._reservations[rid] = reservation

        # 최대 예약 수 초과 시 가장 오래된 것 제거
        if len(self._reservations) > self._max_reservations:
            oldest = min(self._reservations.values(), key=lambda r: r.t_start)
            del self._reservations[oldest.reservation_id]

        return rid

    def check_conflicts(
        self,
        drone_id: str,
        sector: tuple[int, int],
        t_start: float,
        t_end: float,
        altitude_band: tuple[float, float] = (0, 120),
    ) -> list[Reservation]:
        """충돌하는 예약 목록"""
        conflicts = []
        for r in self._reservations.values():
            if not r.active or r.drone_id == drone_id:
                continue
            if r.sector != sector:
                continue
            # 시간 겹침 검사
            if r.t_start >= t_end or r.t_end <= t_start:
                continue
            # 고도 겹침 검사
            if r.altitude_band[0] >= altitude_band[1] or r.altitude_band[1] <= altitude_band[0]:
                continue
            conflicts.append(r)
        return conflicts

    def cancel(self, reservation_id: str) -> bool:
        r = self._reservations.get(reservation_id)
        if r:
            r.active = False
            return True
        return False

    def get_drone_reservations(self, drone_id: str) -> list[Reservation]:
        return [r for r in self._reservations.values() if r.drone_id == drone_id and r.active]

    def active_reservations(self, t: float | None = None) -> list[Reservation]:
        result = [r for r in self._reservations.values() if r.active]
        if t is not None:
            result = [r for r in result if r.t_start <= t <= r.t_end]
        return result

    def sector_schedule(self, sector: tuple[int, int]) -> list[Reservation]:
        return sorted(
            [r for r in self._reservations.values() if r.sector == sector and r.active],
            key=lambda r: r.t_start,
        )

    def cleanup_expired(self, t: float) -> int:
        expired = [rid for rid, r in self._reservations.items() if r.t_end < t]
        for rid in expired:
            del self._reservations[rid]
        return len(expired)

    def summary(self) -> dict[str, Any]:
        active = [r for r in self._reservations.values() if r.active]
        return {
            "total_reservations": len(self._reservations),
            "active_reservations": len(active),
            "unique_drones": len(set(r.drone_id for r in active)),
            "unique_sectors": len(set(r.sector for r in active)),
        }
