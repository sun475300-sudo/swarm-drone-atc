"""Phase 693: 버티포트 (eVTOL 이착륙장) 운영 관리."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PadStatus(Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"


@dataclass
class LandingPad:
    pad_id: str
    position: Tuple[float, float]
    status: PadStatus = PadStatus.AVAILABLE
    max_weight_kg: float = 3000.0
    current_callsign: Optional[str] = None


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
        self.pads: Dict[str, LandingPad] = {}
        self.reservations: Dict[str, SlotReservation] = {}
        self.wait_queue: List[str] = []
        self.max_queue_size = max_queue_size
        self._next_slot = 0

    def add_pad(self, pad_id: str, position: Tuple[float, float], max_weight: float = 3000.0) -> None:
        self.pads[pad_id] = LandingPad(pad_id=pad_id, position=position, max_weight_kg=max_weight)

    def reserve_slot(
        self,
        callsign: str,
        desired_time: float,
        duration_s: float = 600.0,
        weight_kg: float = 1500.0,
        priority: int = 5,
    ) -> Optional[str]:
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
        return slot_id

    def _find_available_pad(self, start: float, duration_s: float, weight_kg: float) -> Optional[str]:
        end = start + duration_s
        for pad_id, pad in self.pads.items():
            if pad.max_weight_kg < weight_kg:
                continue
            if pad.status == PadStatus.MAINTENANCE:
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
        if not any(r.pad_id == pad_id for r in self.reservations.values()):
            self.pads[pad_id].status = PadStatus.AVAILABLE
        return True

    def land(self, slot_id: str) -> bool:
        res = self.reservations.get(slot_id)
        if res is None:
            return False
        pad = self.pads.get(res.pad_id)
        if pad is None:
            return False
        pad.status = PadStatus.OCCUPIED
        pad.current_callsign = res.callsign
        return True

    def depart(self, pad_id: str) -> bool:
        pad = self.pads.get(pad_id)
        if pad is None:
            return False
        pad.status = PadStatus.AVAILABLE
        pad.current_callsign = None
        return True

    def set_maintenance(self, pad_id: str, enabled: bool = True) -> bool:
        pad = self.pads.get(pad_id)
        if pad is None:
            return False
        pad.status = PadStatus.MAINTENANCE if enabled else PadStatus.AVAILABLE
        return True

    def occupancy_rate(self) -> float:
        if not self.pads:
            return 0.0
        busy = sum(
            1 for p in self.pads.values()
            if p.status in (PadStatus.OCCUPIED, PadStatus.RESERVED)
        )
        return busy / len(self.pads)

    def get_stats(self) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}
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
