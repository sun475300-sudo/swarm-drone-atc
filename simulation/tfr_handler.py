"""Phase 692: TFR (Temporary Flight Restriction) 핸들러."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class TfrReason(Enum):
    VIP = "vip_movement"
    DISASTER = "disaster_response"
    SPORTS = "sporting_event"
    SECURITY = "security_operation"
    HAZMAT = "hazmat_incident"
    WILDFIRE = "wildfire"


@dataclass
class Tfr:
    tfr_id: str
    reason: TfrReason
    center: Tuple[float, float]
    radius_m: float
    altitude_floor: float
    altitude_ceiling: float
    start_time: float
    end_time: float
    authorized_callsigns: List[str] = field(default_factory=list)


_DEFAULT_VIOLATION_CAP = 10_000
_DEFAULT_TFR_CAP = 20_000


class TfrHandler:
    """TFR 생성, 위반 감지, 인가 목록을 관리한다."""

    def __init__(
        self,
        seed: int = 42,
        max_violations: int = _DEFAULT_VIOLATION_CAP,
        max_tfrs: int = _DEFAULT_TFR_CAP,
    ) -> None:
        if max_violations <= 0:
            raise ValueError("max_violations must be positive")
        if max_tfrs <= 0:
            raise ValueError("max_tfrs must be positive")
        self.rng = np.random.default_rng(seed)
        self._next_id = 0
        self.tfrs: Dict[str, Tfr] = {}
        self.max_violations = max_violations
        self.max_tfrs = max_tfrs
        self.violation_log: List[Dict[str, Any]] = []

    def _gen_id(self) -> str:
        self._next_id += 1
        return f"TFR-{self._next_id:05d}"

    def declare_tfr(
        self,
        reason: TfrReason,
        center: Tuple[float, float],
        radius_m: float,
        altitude_floor: float,
        altitude_ceiling: float,
        duration_hours: float,
        authorized: Optional[List[str]] = None,
    ) -> str:
        if radius_m <= 0 or altitude_floor > altitude_ceiling or duration_hours <= 0:
            raise ValueError("Invalid TFR geometry or duration")
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
        # max_tfrs 초과 시 만료된 TFR 자동 제거
        if len(self.tfrs) > self.max_tfrs:
            self.purge_expired()
        return tid

    def revoke(self, tfr_id: str) -> bool:
        if tfr_id not in self.tfrs:
            return False
        del self.tfrs[tfr_id]
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
        rec = self.tfrs.get(tfr_id)
        if rec is None:
            return False
        now = time.time()
        return rec.start_time <= now <= rec.end_time

    def check_violation(
        self, callsign: str, position: Tuple[float, float, float]
    ) -> List[str]:
        violations: List[str] = []
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
        self, callsign: str, position: Tuple[float, float, float]
    ) -> List[str]:
        """감사 로그를 기록하지 않고 TFR 충돌만 반환하는 읽기 전용 메서드.

        브리핑 사전 검사 등 부작용이 없어야 하는 경우에 사용한다.
        """
        conflicts: List[str] = []
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
        rec = self.tfrs.get(tfr_id)
        if rec is None:
            return False
        if callsign not in rec.authorized_callsigns:
            rec.authorized_callsigns.append(callsign)
        return True

    def active_tfrs(self) -> List[Tfr]:
        now = time.time()
        return [t for t in self.tfrs.values() if t.start_time <= now <= t.end_time]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self.tfrs),
            "active": len(self.active_tfrs()),
            "violations": len(self.violation_log),
        }
