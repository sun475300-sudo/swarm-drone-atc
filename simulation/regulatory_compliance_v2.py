"""
Phase 480: Regulatory Compliance V2
K-UTM 통합, 항공법 검증, 실시간 규제 준수 모니터링.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set
import hashlib


class RegulationType(Enum):
    KUTM = "k_utm"             # 한국 무인항공기 교통관리
    FAA_PART107 = "faa_107"    # FAA Small UAS
    EASA_OPEN = "easa_open"    # EU Open Category
    ICAO_RPAS = "icao_rpas"    # ICAO RPAS Standards
    LOCAL = "local"


class ComplianceStatus(Enum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    WARNING = "warning"
    PENDING_REVIEW = "pending_review"
    EXEMPT = "exempt"


class AirspaceClass(Enum):
    G = "class_g"      # Uncontrolled
    E = "class_e"      # Controlled (above 400ft)
    D = "class_d"      # Controlled (tower)
    C = "class_c"      # Controlled (approach)
    B = "class_b"      # Controlled (terminal)
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"


@dataclass
class DroneRegistration:
    drone_id: str
    operator_id: str
    registration_number: str
    max_altitude_m: float = 150.0
    max_weight_kg: float = 25.0
    has_remote_id: bool = True
    insurance_valid: bool = True
    pilot_certified: bool = True
    regulations: Set[RegulationType] = field(default_factory=lambda: {RegulationType.KUTM})


@dataclass
class FlightAuthorization:
    auth_id: str
    drone_id: str
    area_center: tuple  # (lat, lon)
    area_radius_m: float
    max_altitude_m: float
    start_time: float
    end_time: float
    airspace_class: AirspaceClass
    status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    conditions: List[str] = field(default_factory=list)


@dataclass
class ComplianceViolation:
    violation_id: str
    drone_id: str
    regulation: RegulationType
    rule: str
    severity: float  # 0-1
    description: str
    timestamp: float
    auto_resolved: bool = False


@dataclass
class RegulationRule:
    rule_id: str
    regulation: RegulationType
    description: str
    check_fn_name: str
    penalty_severity: float = 0.5


class RegulatoryComplianceV2:
    """K-UTM integrated regulatory compliance engine."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.registrations: Dict[str, DroneRegistration] = {}
        self.authorizations: Dict[str, FlightAuthorization] = {}
        self.violations: List[ComplianceViolation] = []
        self.rules: List[RegulationRule] = []
        self._violation_counter = 0
        self._auth_counter = 0
        self._init_rules()

    def _init_rules(self):
        kutm_rules = [
            ("KUTM-ALT", "Maximum altitude 150m AGL", "check_altitude", 0.7),
            ("KUTM-VLOS", "Visual line-of-sight required", "check_vlos", 0.6),
            ("KUTM-REG", "Valid registration required", "check_registration", 0.9),
            ("KUTM-RID", "Remote ID broadcast required", "check_remote_id", 0.8),
            ("KUTM-NFZ", "No-fly zone avoidance", "check_nfz", 1.0),
            ("KUTM-INS", "Valid insurance required", "check_insurance", 0.5),
            ("KUTM-NIGHT", "Night operations restrictions", "check_night_ops", 0.4),
            ("KUTM-WEIGHT", "Weight limit compliance", "check_weight", 0.6),
        ]
        for rid, desc, fn, sev in kutm_rules:
            self.rules.append(RegulationRule(rid, RegulationType.KUTM, desc, fn, sev))

        faa_rules = [
            ("FAA107-ALT", "400ft AGL maximum", "check_altitude_faa", 0.7),
            ("FAA107-SPEED", "100mph max ground speed", "check_speed", 0.5),
            ("FAA107-DAYLIGHT", "Daylight operations only", "check_daylight", 0.4),
        ]
        for rid, desc, fn, sev in faa_rules:
            self.rules.append(RegulationRule(rid, RegulationType.FAA_PART107, desc, fn, sev))

    def register_drone(self, drone_id: str, operator_id: str,
                       max_alt: float = 150.0, weight: float = 10.0) -> DroneRegistration:
        reg_num = hashlib.sha256(f"{drone_id}:{operator_id}".encode()).hexdigest()[:12].upper()
        reg = DroneRegistration(drone_id, operator_id, reg_num, max_alt, weight)
        self.registrations[drone_id] = reg
        return reg

    def request_authorization(self, drone_id: str, area_center: tuple,
                              radius_m: float, max_alt: float,
                              start_time: float, end_time: float,
                              airspace: AirspaceClass = AirspaceClass.G) -> Optional[FlightAuthorization]:
        if drone_id not in self.registrations:
            return None
        reg = self.registrations[drone_id]
        self._auth_counter += 1
        auth = FlightAuthorization(
            auth_id=f"AUTH-{self._auth_counter:06d}",
            drone_id=drone_id, area_center=area_center,
            area_radius_m=radius_m, max_altitude_m=min(max_alt, reg.max_altitude_m),
            start_time=start_time, end_time=end_time,
            airspace_class=airspace
        )

        if airspace in (AirspaceClass.PROHIBITED, AirspaceClass.RESTRICTED):
            auth.status = ComplianceStatus.VIOLATION
            auth.conditions.append("DENIED: Prohibited/Restricted airspace")
        elif airspace in (AirspaceClass.B, AirspaceClass.C):
            auth.status = ComplianceStatus.PENDING_REVIEW
            auth.conditions.append("Requires ATC coordination")
        else:
            if reg.has_remote_id and reg.insurance_valid and reg.pilot_certified:
                auth.status = ComplianceStatus.COMPLIANT
            else:
                auth.status = ComplianceStatus.WARNING
                if not reg.has_remote_id:
                    auth.conditions.append("Remote ID not available")
                if not reg.insurance_valid:
                    auth.conditions.append("Insurance expired")

        self.authorizations[auth.auth_id] = auth
        return auth

    def check_flight_compliance(self, drone_id: str, altitude_m: float,
                                speed_mps: float, position: tuple,
                                timestamp: float) -> List[ComplianceViolation]:
        new_violations = []
        reg = self.registrations.get(drone_id)
        if not reg:
            new_violations.append(self._create_violation(
                drone_id, RegulationType.KUTM, "KUTM-REG",
                1.0, "Unregistered drone detected", timestamp))
            return new_violations

        if altitude_m > reg.max_altitude_m:
            new_violations.append(self._create_violation(
                drone_id, RegulationType.KUTM, "KUTM-ALT",
                0.7, f"Altitude {altitude_m:.0f}m exceeds limit {reg.max_altitude_m:.0f}m",
                timestamp))

        if not reg.has_remote_id:
            new_violations.append(self._create_violation(
                drone_id, RegulationType.KUTM, "KUTM-RID",
                0.8, "Remote ID not broadcasting", timestamp))

        if speed_mps > 44.7:  # ~100mph
            new_violations.append(self._create_violation(
                drone_id, RegulationType.FAA_PART107, "FAA107-SPEED",
                0.5, f"Speed {speed_mps:.1f} m/s exceeds 44.7 m/s limit", timestamp))

        if not reg.insurance_valid:
            new_violations.append(self._create_violation(
                drone_id, RegulationType.KUTM, "KUTM-INS",
                0.5, "Insurance not valid", timestamp))

        return new_violations

    def _create_violation(self, drone_id: str, regulation: RegulationType,
                          rule: str, severity: float, description: str,
                          timestamp: float) -> ComplianceViolation:
        self._violation_counter += 1
        v = ComplianceViolation(
            violation_id=f"VIO-{self._violation_counter:06d}",
            drone_id=drone_id, regulation=regulation,
            rule=rule, severity=severity,
            description=description, timestamp=timestamp
        )
        self.violations.append(v)
        return v

    def auto_enforce(self, drone_id: str) -> List[str]:
        """Generate enforcement actions for active violations."""
        actions = []
        drone_violations = [v for v in self.violations
                           if v.drone_id == drone_id and not v.auto_resolved]
        for v in drone_violations:
            if v.severity >= 0.9:
                actions.append(f"GROUND: {drone_id} — {v.description}")
                v.auto_resolved = True
            elif v.severity >= 0.6:
                actions.append(f"RTH: {drone_id} — {v.description}")
                v.auto_resolved = True
            else:
                actions.append(f"WARN: {drone_id} — {v.description}")
        return actions

    def compliance_score(self, drone_id: str) -> float:
        drone_violations = [v for v in self.violations if v.drone_id == drone_id]
        if not drone_violations:
            return 1.0
        total_severity = sum(v.severity for v in drone_violations)
        resolved = sum(1 for v in drone_violations if v.auto_resolved)
        penalty = total_severity * 0.1
        recovery = resolved * 0.05
        return round(max(0, 1.0 - penalty + recovery), 4)

    def generate_kutm_report(self) -> Dict:
        by_regulation = {}
        for v in self.violations:
            key = v.regulation.value
            by_regulation[key] = by_regulation.get(key, 0) + 1
        return {
            "total_drones": len(self.registrations),
            "authorizations": len(self.authorizations),
            "approved": sum(1 for a in self.authorizations.values()
                          if a.status == ComplianceStatus.COMPLIANT),
            "violations": len(self.violations),
            "by_regulation": by_regulation,
            "avg_severity": round(
                float(np.mean([v.severity for v in self.violations])), 3
            ) if self.violations else 0,
        }

    def summary(self) -> Dict:
        return {
            "registered_drones": len(self.registrations),
            "authorizations": len(self.authorizations),
            "total_violations": len(self.violations),
            "resolved_violations": sum(1 for v in self.violations if v.auto_resolved),
            "rules_count": len(self.rules),
            "regulations": list(set(r.regulation.value for r in self.rules)),
        }
