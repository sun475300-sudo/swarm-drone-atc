"""Phase 692: TFR (Temporary Flight Restriction) 핸들러."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class TfrReason(Enum):
    """``TfrReason`` 관련 기능을 제공한다."""
    VIP = "vip_movement"
    DISASTER = "disaster_response"
    SPORTS = "sporting_event"
    SECURITY = "security_operation"
    HAZMAT = "hazmat_incident"
    WILDFIRE = "wildfire"


@dataclass
class Tfr:
    """``Tfr`` 관련 기능을 제공한다."""
    tfr_id: str
    reason: TfrReason
    center: tuple[float, float]
    radius_m: float
    altitude_floor: float
    altitude_ceiling: float
    start_time: float
    end_time: float
    authorized_callsigns: list[str] = field(default_factory=list)


_DEFAULT_VIOLATION_CAP = 10_000
_DEFAULT_TFR_CAP = 20_000


class TfrHandler:
    """TFR 생성, 위반 감지, 인가 목록을 관리한다."""

    def __init__(
        self,
        seed: int = 42,
        max_violations: int = _DEFAULT_VIOLATION_CAP,
        max_tfrs: int = _DEFAULT_TFR_CAP,
        max_history: int | None = None,
    ) -> None:
        """인스턴스를 초기화한다."""
        if max_violations <= 0:
            raise ValueError("max_violations must be positive")
        if max_tfrs <= 0:
            raise ValueError("max_tfrs must be positive")
        self.rng = np.random.default_rng(seed)
        self._next_id = 0
        self.tfrs: dict[str, Tfr] = {}
        self.max_violations = max_violations
        self.max_tfrs = max_tfrs
        # max_history defaults to max_violations but is an independent cap for
        # the audit trail (declare/revoke/authorize events). Keeping them separate
        # prevents a small violation cap from silently truncating the audit log.
        self.max_history = max_history if max_history is not None else max_violations
        self.violation_log: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []

    def _gen_id(self) -> str:
        self._next_id += 1
        return f"TFR-{self._next_id:05d}"

    def declare_tfr(
        self,
        reason: TfrReason,
        center: tuple[float, float],
        radius_m: float,
        altitude_floor: float,
        altitude_ceiling: float,
        duration_hours: float,
        authorized: list[str] | None = None,
    ) -> str:
        """``declare_tfr`` 동작을 수행한다."""
        if not isinstance(reason, TfrReason):
            raise ValueError(
                f"reason must be a TfrReason enum, got {type(reason).__name__!r}"
            )
        if not math.isfinite(radius_m) or radius_m <= 0:
            raise ValueError(f"radius_m must be a finite positive number, got {radius_m}")
        if not math.isfinite(altitude_floor) or not math.isfinite(altitude_ceiling):
            raise ValueError("altitude_floor and altitude_ceiling must be finite")
        if altitude_floor >= altitude_ceiling:
            raise ValueError(
                f"altitude_floor ({altitude_floor}) must be strictly less than "
                f"altitude_ceiling ({altitude_ceiling})"
            )
        if not math.isfinite(duration_hours) or duration_hours <= 0:
            raise ValueError(f"duration_hours must be a finite positive number, got {duration_hours}")
        if len(center) != 2:
            raise ValueError(
                f"center must be a 2-element (lat, lon) tuple, got {len(center)} elements"
            )
        if not math.isfinite(center[0]) or not math.isfinite(center[1]):
            raise ValueError(
                f"center coordinates must be finite, got {center}"
            )
        tid = self._gen_id()
        now = time.time()
        self.tfrs[tid] = Tfr(
            tfr_id=tid,
            reason=reason,
            center=center,
            radius_m=radius_m,
            altitude_floor=altitude_floor,
            altitude_ceiling=altitude_ceiling,
            start_time=now,
            end_time=now + duration_hours * 3600.0,
            authorized_callsigns=list(authorized or []),
        )
        self._record_history({"action": "declare", "tfr_id": tid, "reason": reason.value, "ts": now})
        # max_tfrs 초과 시 만료된 TFR 자동 제거
        if len(self.tfrs) > self.max_tfrs:
            self.purge_expired()
        # 제거 후에도 초과 중이면 가장 오래된 항목 강제 제거
        if len(self.tfrs) > self.max_tfrs:
            oldest = next(iter(self.tfrs))
            del self.tfrs[oldest]
        return tid

    def _record_history(self, event: dict[str, Any]) -> None:
        self.history.append(event)
        overflow = len(self.history) - self.max_history
        if overflow > 0:
            del self.history[:overflow]

    def revoke(self, tfr_id: str) -> bool:
        """`대상` 상태를 정리한다."""
        if tfr_id not in self.tfrs:
            return False
        del self.tfrs[tfr_id]
        self._record_history({"action": "revoke", "tfr_id": tfr_id, "ts": time.time()})
        return True

    def purge_expired(self) -> int:
        """만료된 TFR을 dict에서 제거해 메모리를 회수한다.

        반환값: 제거된 TFR 수.
        """
        now = time.time()
        expired_keys = [k for k, v in self.tfrs.items() if v.end_time < now]
        for k in expired_keys:
            del self.tfrs[k]
        return len(expired_keys)

    def is_active(self, tfr_id: str) -> bool:
        """`active` 여부를 반환한다."""
        rec = self.tfrs.get(tfr_id)
        if rec is None:
            return False
        now = time.time()
        return rec.start_time <= now <= rec.end_time

    def check_violation(
        self, callsign: str, position: tuple[float, float, float]
    ) -> list[str]:
        """`violation` 결과를 계산하거나 판정한다."""
        if len(position) != 3:
            raise ValueError(
                f"position must be a 3-element (lat, lon, alt) tuple, got {len(position)} elements"
            )
        if not all(math.isfinite(v) for v in position):
            raise ValueError(f"position components must be finite, got {position}")
        violations: list[str] = []
        now = time.time()
        for rec in self.tfrs.values():
            if not (rec.start_time <= now <= rec.end_time):
                continue
            if callsign in rec.authorized_callsigns:
                continue
            dx = position[0] - rec.center[0]
            dy = position[1] - rec.center[1]
            dist = np.sqrt(dx * dx + dy * dy)
            if dist <= rec.radius_m and rec.altitude_floor <= position[2] <= rec.altitude_ceiling:
                violations.append(rec.tfr_id)
                self.violation_log.append({
                    "callsign": callsign,
                    "tfr_id": rec.tfr_id,
                    "position": position,
                    "ts": now,
                })
        # loop 완료 후 1회만 trim — 루프 내 N회 중복 방지
        overflow = len(self.violation_log) - self.max_violations
        if overflow > 0:
            del self.violation_log[:overflow]
        return violations

    def check_conflict_readonly(
        self, callsign: str, position: tuple[float, float, float]
    ) -> list[str]:
        """감사 로그를 기록하지 않고 TFR 충돌만 반환하는 읽기 전용 메서드.

        브리핑 사전 검사 등 부작용이 없어야 하는 경우에 사용한다.
        """
        if len(position) != 3:
            raise ValueError(
                f"position must be a 3-element (lat, lon, alt) tuple, got {len(position)} elements"
            )
        if not all(math.isfinite(v) for v in position):
            raise ValueError(f"position components must be finite, got {position}")
        conflicts: list[str] = []
        now = time.time()
        for rec in self.tfrs.values():
            if not (rec.start_time <= now <= rec.end_time):
                continue
            if callsign in rec.authorized_callsigns:
                continue
            dx = position[0] - rec.center[0]
            dy = position[1] - rec.center[1]
            dist = np.sqrt(dx * dx + dy * dy)
            if dist <= rec.radius_m and rec.altitude_floor <= position[2] <= rec.altitude_ceiling:
                conflicts.append(rec.tfr_id)
        return conflicts

    def authorize(self, tfr_id: str, callsign: str) -> bool:
        """``authorize`` 동작을 수행한다."""
        rec = self.tfrs.get(tfr_id)
        if rec is None:
            return False
        if callsign not in rec.authorized_callsigns:
            rec.authorized_callsigns.append(callsign)
        self._record_history({
            "action": "authorize",
            "tfr_id": tfr_id,
            "callsign": callsign,
            "ts": time.time(),
        })
        return True

    def get(self, tfr_id: str) -> Tfr | None:
        """Return the Tfr record for the given ID, or None if not found."""
        return self.tfrs.get(tfr_id)

    def active_tfrs(self) -> list[Tfr]:
        """``active_tfrs`` 동작을 수행한다."""
        now = time.time()
        return [t for t in self.tfrs.values() if t.start_time <= now <= t.end_time]

    def get_stats(self) -> dict[str, Any]:
        """`stats` 정보를 조회한다."""
        return {
            "total": len(self.tfrs),
            "active": len(self.active_tfrs()),
            "violations": len(self.violation_log),
        }
