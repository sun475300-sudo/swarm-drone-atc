"""Phase 691: NOTAM (Notice to Air Missions) 전자 관리 시스템."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class NotamCategory(Enum):
    AIRSPACE = "airspace"
    OBSTACLE = "obstacle"
    HAZARD = "hazard"
    RESTRICTION = "restriction"
    SERVICE = "service"


class NotamStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class NotamRecord:
    notam_id: str
    category: NotamCategory
    area_center: Tuple[float, float]
    radius_m: float
    altitude_min: float
    altitude_max: float
    valid_from: float
    valid_until: float
    description: str
    issuer: str = "ATC"
    status: NotamStatus = NotamStatus.ACTIVE
    created_at: float = field(default_factory=time.time)


_DEFAULT_HISTORY_CAP = 10_000
_DEFAULT_NOTAM_CAP = 50_000


class NotamManager:
    """전자 NOTAM 생성/갱신/만료/검색을 담당하는 매니저."""

    def __init__(
        self,
        seed: int = 42,
        max_history: int = _DEFAULT_HISTORY_CAP,
        max_notams: int = _DEFAULT_NOTAM_CAP,
    ) -> None:
        if max_history <= 0:
            raise ValueError("max_history must be positive")
        if max_notams <= 0:
            raise ValueError("max_notams must be positive")
        self.rng = np.random.default_rng(seed)
        self._next_id = 0
        self.notams: Dict[str, NotamRecord] = {}
        self.max_history = max_history
        self.max_notams = max_notams
        self.history: List[Dict[str, Any]] = []

    def _gen_id(self) -> str:
        self._next_id += 1
        return f"NOTAM-{self._next_id:06d}"

    def create_notam(
        self,
        category: NotamCategory,
        area_center: Tuple[float, float],
        radius_m: float,
        altitude_min: float,
        altitude_max: float,
        duration_hours: float,
        description: str,
        issuer: str = "ATC",
    ) -> str:
        if not isinstance(category, NotamCategory):
            raise ValueError(
                f"category must be a NotamCategory enum, got {type(category).__name__!r}"
            )
        if not math.isfinite(radius_m) or radius_m <= 0:
            raise ValueError(f"radius_m must be a finite positive number, got {radius_m}")
        if not math.isfinite(altitude_min) or not math.isfinite(altitude_max):
            raise ValueError("altitude_min and altitude_max must be finite")
        if altitude_min >= altitude_max:
            raise ValueError(
                f"altitude_min ({altitude_min}) must be strictly less than altitude_max ({altitude_max})"
            )
        if not math.isfinite(duration_hours) or duration_hours <= 0:
            raise ValueError(f"duration_hours must be a finite positive number, got {duration_hours}")
        if len(area_center) != 2:
            raise ValueError(
                f"area_center must be a 2-element (lat, lon) tuple, got {len(area_center)} elements"
            )
        now = time.time()
        notam_id = self._gen_id()
        record = NotamRecord(
            notam_id=notam_id,
            category=category,
            area_center=area_center,
            radius_m=radius_m,
            altitude_min=altitude_min,
            altitude_max=altitude_max,
            valid_from=now,
            valid_until=now + duration_hours * 3600.0,
            description=description,
            issuer=issuer,
        )
        self.notams[notam_id] = record
        self._record_history({"action": "create", "notam_id": notam_id, "ts": now})
        # max_notams 초과 시 종료 상태 레코드 자동 제거
        if len(self.notams) > self.max_notams:
            self.purge_terminal()
        # 제거 후에도 여전히 초과 중이면 삽입 순서대로 가장 오래된 항목 강제 제거
        if len(self.notams) > self.max_notams:
            oldest = next(iter(self.notams))
            del self.notams[oldest]
        return notam_id

    def _record_history(self, event: Dict[str, Any]) -> None:
        self.history.append(event)
        overflow = len(self.history) - self.max_history
        if overflow > 0:
            del self.history[:overflow]

    def cancel_notam(self, notam_id: str) -> bool:
        if notam_id not in self.notams:
            return False
        self.notams[notam_id].status = NotamStatus.CANCELLED
        self._record_history({"action": "cancel", "notam_id": notam_id, "ts": time.time()})
        return True

    def expire_old(self) -> int:
        now = time.time()
        expired = 0
        for rec in self.notams.values():
            if rec.status == NotamStatus.ACTIVE and rec.valid_until < now:
                rec.status = NotamStatus.EXPIRED
                self._record_history({"action": "expire", "notam_id": rec.notam_id, "ts": now})
                expired += 1
        return expired

    def purge_terminal(self) -> int:
        """EXPIRED/CANCELLED NOTAM을 dict에서 제거해 메모리를 회수한다.

        max_notams 초과 시 자동 호출되며, 수동으로도 호출 가능하다.
        반환값: 제거된 레코드 수.
        """
        terminal = {
            k for k, v in self.notams.items()
            if v.status in (NotamStatus.EXPIRED, NotamStatus.CANCELLED)
        }
        for k in terminal:
            del self.notams[k]
        return len(terminal)

    def extend_notam(self, notam_id: str, extra_hours: float) -> bool:
        if notam_id not in self.notams or extra_hours <= 0:
            return False
        rec = self.notams[notam_id]
        if rec.status != NotamStatus.ACTIVE:
            return False
        rec.valid_until += extra_hours * 3600.0
        self._record_history({
            "action": "extend",
            "notam_id": notam_id,
            "extra_hours": extra_hours,
            "new_valid_until": rec.valid_until,
            "ts": time.time(),
        })
        return True

    def query_active(
        self,
        area_center: Optional[Tuple[float, float]] = None,
        radius_m: float = 10000.0,
        altitude: Optional[float] = None,
    ) -> List[NotamRecord]:
        if radius_m < 0:
            raise ValueError("radius_m must be non-negative")
        if altitude is not None and not math.isfinite(altitude):
            raise ValueError(f"altitude must be finite, got {altitude}")
        now = time.time()
        result = []
        for rec in self.notams.values():
            if rec.status != NotamStatus.ACTIVE or rec.valid_until < now:
                continue
            if area_center is not None:
                dx = area_center[0] - rec.area_center[0]
                dy = area_center[1] - rec.area_center[1]
                if np.sqrt(dx * dx + dy * dy) > (radius_m + rec.radius_m):
                    continue
            if altitude is not None and not (rec.altitude_min <= altitude <= rec.altitude_max):
                continue
            result.append(rec)
        return result

    def get(self, notam_id: str) -> Optional[NotamRecord]:
        return self.notams.get(notam_id)

    def count_by_status(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for rec in self.notams.values():
            s = rec.status.value
            counts[s] = counts.get(s, 0) + 1
        return counts

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self.notams),
            "by_status": self.count_by_status(),
            "history_events": len(self.history),
        }
