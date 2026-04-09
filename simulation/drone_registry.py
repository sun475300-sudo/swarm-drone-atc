"""
드론 인증 관리
==============
등록/인증/블랙리스트 + 비행 허가 검증.

사용법:
    reg = DroneRegistry()
    reg.register("d1", owner="pilot_A", drone_type="COMMERCIAL")
    ok = reg.authorize_flight("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RegistrationStatus(Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BLACKLISTED = "BLACKLISTED"
    EXPIRED = "EXPIRED"


@dataclass
class DroneRecord:
    """드론 등록 기록"""
    drone_id: str
    owner: str
    drone_type: str
    status: RegistrationStatus = RegistrationStatus.ACTIVE
    registration_date: str = ""
    cert_expiry: str = ""
    flight_hours: float = 0.0
    violations: int = 0
    max_altitude_m: float = 120.0
    max_speed_ms: float = 15.0


class DroneRegistry:
    """드론 인증 관리."""

    def __init__(self) -> None:
        self._registry: dict[str, DroneRecord] = {}
        self._flight_log: list[dict[str, Any]] = []

    def register(
        self,
        drone_id: str,
        owner: str = "unknown",
        drone_type: str = "COMMERCIAL",
        max_altitude: float = 120.0,
        max_speed: float = 15.0,
    ) -> DroneRecord:
        record = DroneRecord(
            drone_id=drone_id,
            owner=owner,
            drone_type=drone_type,
            registration_date=datetime.now().strftime("%Y-%m-%d"),
            max_altitude_m=max_altitude,
            max_speed_ms=max_speed,
        )
        self._registry[drone_id] = record
        return record

    def is_registered(self, drone_id: str) -> bool:
        return drone_id in self._registry

    def authorize_flight(self, drone_id: str) -> bool:
        """비행 허가 검증"""
        record = self._registry.get(drone_id)
        if not record:
            return False
        if record.status != RegistrationStatus.ACTIVE:
            return False
        if record.violations >= 5:
            record.status = RegistrationStatus.SUSPENDED
            return False
        return True

    def suspend(self, drone_id: str, reason: str = "") -> bool:
        record = self._registry.get(drone_id)
        if record:
            record.status = RegistrationStatus.SUSPENDED
            self._flight_log.append({
                "drone_id": drone_id, "action": "SUSPEND", "reason": reason,
            })
            return True
        return False

    def blacklist(self, drone_id: str, reason: str = "") -> bool:
        record = self._registry.get(drone_id)
        if record:
            record.status = RegistrationStatus.BLACKLISTED
            self._flight_log.append({
                "drone_id": drone_id, "action": "BLACKLIST", "reason": reason,
            })
            return True
        return False

    def reinstate(self, drone_id: str) -> bool:
        record = self._registry.get(drone_id)
        if record and record.status in (RegistrationStatus.SUSPENDED, RegistrationStatus.EXPIRED):
            record.status = RegistrationStatus.ACTIVE
            record.violations = 0
            return True
        return False

    def add_violation(self, drone_id: str) -> int:
        record = self._registry.get(drone_id)
        if record:
            record.violations += 1
            return record.violations
        return 0

    def log_flight(self, drone_id: str, duration_s: float) -> None:
        record = self._registry.get(drone_id)
        if record:
            record.flight_hours += duration_s / 3600

    def get_record(self, drone_id: str) -> DroneRecord | None:
        return self._registry.get(drone_id)

    def active_drones(self) -> list[str]:
        return [
            did for did, r in self._registry.items()
            if r.status == RegistrationStatus.ACTIVE
        ]

    def by_owner(self, owner: str) -> list[DroneRecord]:
        return [r for r in self._registry.values() if r.owner == owner]

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for r in self._registry.values():
            by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
        return {
            "total_registered": len(self._registry),
            "by_status": by_status,
            "total_violations": sum(r.violations for r in self._registry.values()),
        }
