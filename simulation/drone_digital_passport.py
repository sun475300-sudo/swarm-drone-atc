"""
Phase 517: Drone Digital Passport
드론 신원 관리, 인증서 체인, 비행 이력 기록.
"""

import numpy as np
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime


class CertificateType(Enum):
    AIRWORTHINESS = "airworthiness"
    OPERATOR_LICENSE = "operator_license"
    TYPE_CERTIFICATE = "type_certificate"
    INSURANCE = "insurance"
    REGISTRATION = "registration"


class PassportStatus(Enum):
    VALID = "valid"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING = "pending"


@dataclass
class Certificate:
    cert_id: str
    cert_type: CertificateType
    issuer: str
    subject: str
    valid_from: float
    valid_until: float
    signature: str
    revoked: bool = False


@dataclass
class FlightEntry:
    flight_id: str
    departure: str
    destination: str
    duration_s: float
    distance_km: float
    incidents: int = 0
    timestamp: float = 0.0


@dataclass
class DigitalPassport:
    passport_id: str
    drone_id: str
    manufacturer: str
    model: str
    serial: str
    status: PassportStatus
    certificates: List[Certificate] = field(default_factory=list)
    flight_history: List[FlightEntry] = field(default_factory=list)
    total_flight_hours: float = 0.0
    maintenance_due: bool = False


class CertificateAuthority:
    """Issue and verify drone certificates."""

    def __init__(self, ca_name: str = "SDACS-CA", seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.ca_name = ca_name
        self.issued: List[Certificate] = []
        self.revoked: set = set()
        self._counter = 0

    def issue(self, cert_type: CertificateType, subject: str,
              validity_days: float = 365) -> Certificate:
        self._counter += 1
        now = self._counter * 86400.0
        sig = hashlib.sha256(f"{self.ca_name}:{subject}:{self._counter}".encode()).hexdigest()[:24]
        cert = Certificate(
            f"CERT-{self._counter:06d}", cert_type, self.ca_name, subject,
            now, now + validity_days * 86400, sig)
        self.issued.append(cert)
        return cert

    def revoke(self, cert_id: str):
        self.revoked.add(cert_id)
        for c in self.issued:
            if c.cert_id == cert_id:
                c.revoked = True

    def verify(self, cert: Certificate, current_time: float = None) -> bool:
        if cert.cert_id in self.revoked:
            return False
        if cert.revoked:
            return False
        t = current_time or cert.valid_from + 1
        return cert.valid_from <= t <= cert.valid_until


class DroneDigitalPassport:
    """Comprehensive drone identity and history management."""

    def __init__(self, n_drones: int = 20, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.ca = CertificateAuthority(seed=seed)
        self.passports: Dict[str, DigitalPassport] = {}
        self._flight_counter = 0

        manufacturers = ["DroneCorp", "SkyTech", "AeroSystems", "SwarmWorks"]
        models = ["X-100", "Falcon-V2", "Scout-Pro", "Titan-Heavy"]

        for i in range(n_drones):
            did = f"drone_{i}"
            serial = hashlib.sha256(f"sn_{i}".encode()).hexdigest()[:12]
            passport = DigitalPassport(
                f"PP-{i:05d}", did,
                self.rng.choice(manufacturers),
                self.rng.choice(models), serial,
                PassportStatus.VALID)

            for ct in CertificateType:
                cert = self.ca.issue(ct, did, self.rng.uniform(90, 730))
                passport.certificates.append(cert)

            passport.total_flight_hours = round(self.rng.uniform(10, 500), 1)
            passport.maintenance_due = passport.total_flight_hours > 400
            self.passports[did] = passport

    def record_flight(self, drone_id: str, departure: str = "A",
                      destination: str = "B", duration_s: float = 600,
                      distance_km: float = 5.0) -> Optional[FlightEntry]:
        pp = self.passports.get(drone_id)
        if not pp or pp.status != PassportStatus.VALID:
            return None
        self._flight_counter += 1
        entry = FlightEntry(f"FLT-{self._flight_counter:06d}",
                           departure, destination, duration_s, distance_km,
                           0, float(self._flight_counter))
        pp.flight_history.append(entry)
        pp.total_flight_hours += duration_s / 3600
        if pp.total_flight_hours > 400:
            pp.maintenance_due = True
        return entry

    def suspend(self, drone_id: str, reason: str = "violation"):
        pp = self.passports.get(drone_id)
        if pp:
            pp.status = PassportStatus.SUSPENDED

    def validate(self, drone_id: str) -> Dict:
        pp = self.passports.get(drone_id)
        if not pp:
            return {"valid": False, "reason": "no passport"}
        cert_valid = all(self.ca.verify(c) for c in pp.certificates)
        return {
            "valid": pp.status == PassportStatus.VALID and cert_valid,
            "status": pp.status.value,
            "certificates_valid": cert_valid,
            "flight_hours": round(pp.total_flight_hours, 1),
            "maintenance_due": pp.maintenance_due,
            "flights": len(pp.flight_history),
        }

    def audit(self) -> Dict:
        valid = sum(1 for p in self.passports.values() if p.status == PassportStatus.VALID)
        maint = sum(1 for p in self.passports.values() if p.maintenance_due)
        return {
            "total_drones": len(self.passports),
            "valid": valid,
            "suspended": sum(1 for p in self.passports.values() if p.status == PassportStatus.SUSPENDED),
            "maintenance_due": maint,
            "total_flights": self._flight_counter,
            "total_certs": len(self.ca.issued),
        }

    def summary(self) -> Dict:
        return self.audit()
