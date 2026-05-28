"""Phase 693: 버티포트 (eVTOL 이착륙장) 운영 관리."""

from __future__ import annotations

import contextlib
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PadStatus(Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"


@dataclass
class LandingPad:
    pad_id: str
    position: tuple[float, float]
    status: PadStatus = PadStatus.AVAILABLE
    max_weight_kg: float = 3000.0
    current_callsign: str | None = None


@dataclass
class SlotReservation:
    slot_id: str
    pad_id: str
    callsign: str
    start_time: float
    duration_s: float
    priority: int = 5


class VertiportOps:
    """버티포트 패드/슬롯 예약, 큐, 운영을 관리."""

    def __init__(self, vertiport_id: str = "VP-01", max_queue_size: int = 500) -> None:
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
        self.vertiport_id = vertiport_id
        self.pads: dict[str, LandingPad] = {}
        self.reservations: dict[str, SlotReservation] = {}
        self.wait_queue: list[str] = []
        self.max_queue_size = max_queue_size
        self._next_slot = 0

    def add_pad(self, pad_id: str, position: tuple[float, float], max_weight: float = 3000.0) -> None:
        if pad_id in self.pads:
            raise ValueError(f"pad_id {pad_id!r} already exists; remove it first or use a unique ID")
        if not math.isfinite(max_weight) or max_weight <= 0:
            raise ValueError(
                f"max_weight must be a finite positive number, got {max_weight}"
            )
        if len(position) != 2:
            raise ValueError(
                f"position must be a 2-element (lat, lon) tuple, got {len(position)} elements"
            )
        if not math.isfinite(position[0]) or not math.isfinite(position[1]):
            raise ValueError(f"position coordinates must be finite, got {position}")
        self.pads[pad_id] = LandingPad(pad_id=pad_id, position=position, max_weight_kg=max_weight)

    def reserve_slot(
        self,
        callsign: str,
        desired_time: float,
        duration_s: float = 600.0,
        weight_kg: float = 1500.0,
        priority: int = 5,
    ) -> str | None:
        if not math.isfinite(desired_time) or desired_time < 0:
            raise ValueError(
                f"desired_time must be a finite non-negative number, got {desired_time}"
            )
        if not math.isfinite(duration_s) or duration_s <= 0:
            raise ValueError(f"duration_s must be a finite positive number, got {duration_s}")
        if not math.isfinite(weight_kg) or weight_kg < 0:
            raise ValueError(f"weight_kg must be a finite non-negative number, got {weight_kg}")
        candidate = self._find_available_pad(desired_time, duration_s, weight_kg)
        if candidate is None:
            # 중복 callsign 및 max_queue_size 초과 거부
            if callsign not in self.wait_queue and len(self.wait_queue) < self.max_queue_size:
                self.wait_queue.append(callsign)
            return None
        self._next_slot += 1
        slot_id = f"SLOT-{self._next_slot:05d}"
        self.reservations[slot_id] = SlotReservation(
            slot_id=slot_id,
            pad_id=candidate,
            callsign=callsign,
            start_time=desired_time,
            duration_s=duration_s,
            priority=priority,
        )
        self.pads[candidate].status = PadStatus.RESERVED
        # 이전 실패 시도로 대기열에 있는 경우 제거 — 이제 슬롯이 확보됨
        with contextlib.suppress(ValueError):
            self.wait_queue.remove(callsign)
        return slot_id

    def _find_available_pad(self, start: float, duration_s: float, weight_kg: float) -> str | None:
        end = start + duration_s
        for pad_id, pad in self.pads.items():
            if pad.max_weight_kg < weight_kg:
                continue
            if pad.status in (PadStatus.MAINTENANCE, PadStatus.OCCUPIED):
                continue
            conflict = False
            for res in self.reservations.values():
                if res.pad_id != pad_id:
                    continue
                res_end = res.start_time + res.duration_s
                if not (end <= res.start_time or start >= res_end):
                    conflict = True
                    break
            if not conflict:
                return pad_id
        return None

    def purge_completed(self, current_time: float) -> int:
        """start_time + duration_s가 current_time 이전인 만료 예약을 제거한다.

        패드 상태가 RESERVED인 경우 AVAILABLE로 복원한다.
        반환값: 제거된 예약 수.
        """
        expired_keys = [
            k for k, v in self.reservations.items()
            if v.start_time + v.duration_s < current_time
        ]
        for k in expired_keys:
            pad_id = self.reservations[k].pad_id
            del self.reservations[k]
            # 해당 패드에 남은 예약이 없고 RESERVED 상태이면 AVAILABLE로 복원
            pad = self.pads.get(pad_id)
            if pad is not None and pad.status == PadStatus.RESERVED:
                if not any(r.pad_id == pad_id for r in self.reservations.values()):
                    pad.status = PadStatus.AVAILABLE
        return len(expired_keys)

    def cancel_reservation(self, slot_id: str) -> bool:
        if slot_id not in self.reservations:
            return False
        pad_id = self.reservations[slot_id].pad_id
        del self.reservations[slot_id]
        pad = self.pads.get(pad_id)
        # OCCUPIED 상태(이미 착륙) 또는 MAINTENANCE 상태는 건드리지 않음
        if (pad is not None
                and pad.status == PadStatus.RESERVED
                and not any(r.pad_id == pad_id for r in self.reservations.values())):
            pad.status = PadStatus.AVAILABLE
        return True

    def land(self, slot_id: str) -> bool:
        res = self.reservations.get(slot_id)
        if res is None:
            return False
        pad = self.pads.get(res.pad_id)
        if pad is None:
            return False
        # RESERVED 상태인 패드만 착륙 허용 — 이미 OCCUPIED인 경우 이중 착륙 방지
        if pad.status != PadStatus.RESERVED:
            return False
        pad.status = PadStatus.OCCUPIED
        pad.current_callsign = res.callsign
        return True

    def depart(self, pad_id: str) -> bool:
        pad = self.pads.get(pad_id)
        if pad is None:
            return False
        # OCCUPIED 상태인 패드만 AVAILABLE로 복원 — MAINTENANCE 상태는 건드리지 않음
        if pad.status == PadStatus.OCCUPIED:
            pad.status = PadStatus.AVAILABLE
        pad.current_callsign = None
        # 현재 시각 이전에 시작된 예약(소모된 슬롯)만 제거 — 미래 예약은 유지
        now = time.time()
        stale = [
            k for k, r in self.reservations.items()
            if r.pad_id == pad_id and r.start_time <= now
        ]
        for k in stale:
            del self.reservations[k]
        return True

    def set_maintenance(self, pad_id: str, enabled: bool = True) -> bool:
        """패드를 정비 모드로 전환하거나 해제한다.

        `enable_maintenance` / `disable_maintenance`를 선호한다.
        """
        if enabled:
            return self.enable_maintenance(pad_id)
        return self.disable_maintenance(pad_id)

    def enable_maintenance(self, pad_id: str) -> bool:
        """패드를 MAINTENANCE 상태로 전환한다.

        OCCUPIED 또는 RESERVED 상태(드론 운영 중)인 경우 False를 반환해 보호한다.
        """
        pad = self.pads.get(pad_id)
        if pad is None:
            return False
        if pad.status in (PadStatus.OCCUPIED, PadStatus.RESERVED):
            return False
        pad.status = PadStatus.MAINTENANCE
        return True

    def disable_maintenance(self, pad_id: str) -> bool:
        """MAINTENANCE 상태인 패드를 AVAILABLE로 복원한다.

        OCCUPIED 또는 RESERVED 상태는 건드리지 않는다.
        """
        pad = self.pads.get(pad_id)
        if pad is None or pad.status != PadStatus.MAINTENANCE:
            return False
        pad.status = PadStatus.AVAILABLE
        return True

    def occupancy_rate(self) -> float:
        if not self.pads:
            return 0.0
        busy = sum(
            1 for p in self.pads.values()
            if p.status in (PadStatus.OCCUPIED, PadStatus.RESERVED)
        )
        return busy / len(self.pads)

    def get_stats(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for p in self.pads.values():
            status_counts[p.status.value] = status_counts.get(p.status.value, 0) + 1
        return {
            "vertiport_id": self.vertiport_id,
            "pads_total": len(self.pads),
            "reservations": len(self.reservations),
            "wait_queue": len(self.wait_queue),
            "occupancy": self.occupancy_rate(),
            "status_counts": status_counts,
        }
