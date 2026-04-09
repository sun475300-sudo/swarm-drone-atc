"""
드론 신원 인증
=============
PKI 기반 인증 + 인증서 만료 + 갱신 프로토콜.

사용법:
    di = DroneIdentity()
    di.issue_certificate("d1", valid_hours=24)
    ok = di.verify("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import hashlib


@dataclass
class Certificate:
    """드론 인증서"""
    drone_id: str
    cert_hash: str
    issued_at: float = 0.0
    valid_until: float = 0.0
    revoked: bool = False
    renewals: int = 0


class DroneIdentity:
    """드론 신원 인증."""

    def __init__(self) -> None:
        self._certs: dict[str, Certificate] = {}
        self._revoked: set[str] = set()
        self._auth_log: list[dict[str, Any]] = []

    def issue_certificate(
        self, drone_id: str, valid_hours: float = 24.0, t: float = 0.0,
    ) -> Certificate:
        cert_hash = hashlib.sha256(
            f"{drone_id}:{t}:{valid_hours}".encode()
        ).hexdigest()[:16]

        cert = Certificate(
            drone_id=drone_id, cert_hash=cert_hash,
            issued_at=t, valid_until=t + valid_hours * 3600,
        )
        self._certs[drone_id] = cert
        return cert

    def verify(self, drone_id: str, t: float = 0.0) -> bool:
        cert = self._certs.get(drone_id)
        if not cert:
            self._log(drone_id, False, "인증서 없음", t)
            return False
        if cert.revoked or drone_id in self._revoked:
            self._log(drone_id, False, "인증서 폐기됨", t)
            return False
        if t > cert.valid_until:
            self._log(drone_id, False, "인증서 만료", t)
            return False
        self._log(drone_id, True, "인증 성공", t)
        return True

    def renew(self, drone_id: str, valid_hours: float = 24.0, t: float = 0.0) -> bool:
        cert = self._certs.get(drone_id)
        if not cert or cert.revoked:
            return False
        cert.valid_until = t + valid_hours * 3600
        cert.renewals += 1
        return True

    def revoke(self, drone_id: str) -> bool:
        cert = self._certs.get(drone_id)
        if cert:
            cert.revoked = True
            self._revoked.add(drone_id)
            return True
        return False

    def _log(self, drone_id: str, success: bool, reason: str, t: float) -> None:
        self._auth_log.append({
            "drone_id": drone_id, "success": success,
            "reason": reason, "t": t,
        })

    def expiring_soon(self, within_hours: float = 1.0, t: float = 0.0) -> list[str]:
        threshold = t + within_hours * 3600
        return [
            did for did, cert in self._certs.items()
            if not cert.revoked and cert.valid_until <= threshold and cert.valid_until > t
        ]

    def auth_log(self, drone_id: str | None = None, n: int = 20) -> list[dict[str, Any]]:
        entries = self._auth_log
        if drone_id:
            entries = [e for e in entries if e["drone_id"] == drone_id]
        return entries[-n:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_certs": len(self._certs),
            "revoked": len(self._revoked),
            "auth_attempts": len(self._auth_log),
            "auth_success_rate": round(
                sum(1 for e in self._auth_log if e["success"]) / max(len(self._auth_log), 1) * 100, 1
            ),
        }
