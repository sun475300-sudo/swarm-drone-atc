"""Phase 685: ICAO Doc 10019 국제 표준 준수 시뮬레이션."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


class OperationCategory:
    OPEN = "Open"
    SPECIFIC = "Specific"
    CERTIFIED = "Certified"


class C2LinkType:
    DIRECT_RF = "direct_rf"
    SATELLITE = "satellite"
    CELLULAR = "cellular"
    MESH = "mesh"


@dataclass
class RPASOperator:
    operator_id: str
    name: str
    certificate_number: str
    certificate_type: str  # "remote_pilot", "operator_certificate"
    valid_until: float
    country_code: str = "KR"


@dataclass
class RPASAircraft:
    registration: str
    type_certificate: str
    serial_number: str
    mtow_kg: float
    max_altitude_m: float
    max_speed_ms: float
    endurance_min: float
    c2_link_type: str = C2LinkType.DIRECT_RF


@dataclass
class ComplianceResult:
    compliant: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    category: str = ""


# ICAO Annex requirements mapping
ANNEX_REQUIREMENTS: Dict[int, List[str]] = {
    2: ["Rules of the Air applicable to RPAS", "Right of way rules", "Flight plan requirements"],
    6: ["Operator certificate", "Maintenance program", "Flight crew licensing"],
    7: ["Aircraft registration marks", "RPAS nationality marks"],
    8: ["Type certificate or equivalent", "Airworthiness requirements", "Design standards"],
    10: ["C2 link spectrum allocation", "Communication requirements"],
    11: ["Air traffic service provision", "Separation standards"],
    13: ["Accident/incident investigation", "Occurrence reporting"],
    15: ["NOTAM publication", "Aeronautical information"],
}

# C2 link performance requirements by operation category
C2_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    OperationCategory.OPEN: {
        "required": False,
        "max_latency_ms": 500,
        "min_availability": 0.95,
    },
    OperationCategory.SPECIFIC: {
        "required": True,
        "max_latency_ms": 200,
        "min_availability": 0.99,
        "allowed_types": [C2LinkType.DIRECT_RF, C2LinkType.SATELLITE, C2LinkType.CELLULAR],
    },
    OperationCategory.CERTIFIED: {
        "required": True,
        "max_latency_ms": 100,
        "min_availability": 0.999,
        "allowed_types": [C2LinkType.DIRECT_RF, C2LinkType.SATELLITE],
    },
}

# Weight thresholds for operation categories (kg)
WEIGHT_THRESHOLDS = {
    OperationCategory.OPEN: 25.0,
    OperationCategory.SPECIFIC: 150.0,
}


class ICAODoc10019:
    """ICAO Manual on RPAS (Doc 10019) compliance checker."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)

    def validate_operator(self, operator: RPASOperator) -> ComplianceResult:
        violations = []
        warnings = []

        if not operator.certificate_number:
            violations.append("Missing operator certificate number")
        if not operator.name:
            violations.append("Missing operator name")
        if operator.valid_until < 0:
            violations.append("Certificate expired")
        if operator.certificate_type not in ("remote_pilot", "operator_certificate"):
            warnings.append(f"Non-standard certificate type: {operator.certificate_type}")

        return ComplianceResult(
            compliant=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )

    def validate_aircraft(self, aircraft: RPASAircraft) -> ComplianceResult:
        violations = []
        warnings = []

        if not aircraft.registration:
            violations.append("Missing aircraft registration")
        if not aircraft.type_certificate:
            violations.append("Missing type certificate")
        if not aircraft.serial_number:
            violations.append("Missing serial number")
        if aircraft.mtow_kg <= 0:
            violations.append("Invalid MTOW")
        if aircraft.max_altitude_m > 120 and aircraft.mtow_kg > 25:
            warnings.append("High altitude + heavy aircraft may require Certified category")
        if aircraft.endurance_min < 5:
            warnings.append("Very short endurance - limited operational utility")

        return ComplianceResult(
            compliant=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )

    def check_c2_link_requirements(
        self, link_type: str, operation_category: str
    ) -> Dict[str, Any]:
        reqs = C2_REQUIREMENTS.get(operation_category, C2_REQUIREMENTS[OperationCategory.OPEN])

        if not reqs.get("required", False):
            return {"compliant": True, "message": "C2 link not required for Open category"}

        allowed = reqs.get("allowed_types", [])
        if allowed and link_type not in allowed:
            return {
                "compliant": False,
                "message": f"Link type '{link_type}' not allowed for {operation_category}",
                "allowed_types": allowed,
            }

        return {
            "compliant": True,
            "max_latency_ms": reqs["max_latency_ms"],
            "min_availability": reqs["min_availability"],
        }

    def classify_operation(
        self, altitude_m: float, vlos: bool, over_people: bool, mtow_kg: float = 2.0
    ) -> str:
        if mtow_kg > WEIGHT_THRESHOLDS[OperationCategory.SPECIFIC]:
            return OperationCategory.CERTIFIED
        if not vlos or over_people or altitude_m > 120:
            if mtow_kg > WEIGHT_THRESHOLDS[OperationCategory.OPEN]:
                return OperationCategory.CERTIFIED
            return OperationCategory.SPECIFIC
        if mtow_kg <= WEIGHT_THRESHOLDS[OperationCategory.OPEN]:
            return OperationCategory.OPEN
        return OperationCategory.SPECIFIC

    def get_required_certifications(self, operation_class: str) -> List[str]:
        base = ["Remote pilot certificate"]
        if operation_class == OperationCategory.SPECIFIC:
            base.extend(["Operational authorization", "Risk assessment (SORA)"])
        elif operation_class == OperationCategory.CERTIFIED:
            base.extend([
                "Type certificate", "Airworthiness certificate",
                "Operator certificate (AOC equivalent)",
                "C2 link performance certificate",
            ])
        return base

    def check_detect_and_avoid(
        self, aircraft: RPASAircraft, traffic: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check DAA (Detect and Avoid) capability requirements."""
        needs_daa = aircraft.max_altitude_m > 120 or aircraft.mtow_kg > 25

        nearby_traffic = [
            t for t in traffic
            if t.get("distance_m", float("inf")) < 5000
        ]

        return {
            "daa_required": needs_daa,
            "nearby_traffic_count": len(nearby_traffic),
            "recommendation": "DAA system required" if needs_daa and nearby_traffic else "No immediate DAA concern",
        }

    def generate_compliance_report(
        self, operator: RPASOperator, aircraft: RPASAircraft,
        operation: Dict[str, Any],
    ) -> Dict[str, Any]:
        op_result = self.validate_operator(operator)
        ac_result = self.validate_aircraft(aircraft)
        category = self.classify_operation(
            altitude_m=operation.get("altitude_m", 50),
            vlos=operation.get("vlos", True),
            over_people=operation.get("over_people", False),
            mtow_kg=aircraft.mtow_kg,
        )
        c2_check = self.check_c2_link_requirements(aircraft.c2_link_type, category)
        certs = self.get_required_certifications(category)

        all_violations = op_result.violations + ac_result.violations
        if not c2_check.get("compliant", True):
            all_violations.append(c2_check.get("message", "C2 link non-compliant"))

        return {
            "overall_compliant": len(all_violations) == 0,
            "operation_category": category,
            "operator_compliant": op_result.compliant,
            "aircraft_compliant": ac_result.compliant,
            "c2_compliant": c2_check.get("compliant", True),
            "violations": all_violations,
            "warnings": op_result.warnings + ac_result.warnings,
            "required_certifications": certs,
        }

    def get_annex_requirements(self, annex_number: int) -> List[str]:
        return ANNEX_REQUIREMENTS.get(annex_number, [f"No specific requirements for Annex {annex_number}"])
