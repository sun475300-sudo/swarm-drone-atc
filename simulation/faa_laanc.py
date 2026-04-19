"""Phase 684: FAA LAANC 연동 인터페이스 시뮬레이션."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class AuthorizationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AirspaceClassFAA(Enum):
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    G = "G"


class OperationType(Enum):
    PART_107 = "part_107"
    RECREATIONAL = "recreational"
    PUBLIC_SAFETY = "public_safety"
    WAIVER = "waiver"


@dataclass
class LAANCRequest:
    operator_id: str
    drone_registration: str
    operation_area: Tuple[float, float, float, float]  # min_lat, min_lon, max_lat, max_lon
    max_altitude_ft: float
    start_time: float
    end_time: float
    operation_type: OperationType = OperationType.PART_107


@dataclass
class LAANCAuthorization:
    request_id: str
    status: AuthorizationStatus
    authorized_altitude_ft: float
    conditions: List[str] = field(default_factory=list)
    valid_from: float = 0.0
    valid_until: float = 0.0
    facility_map_id: str = ""


@dataclass
class TFR:
    tfr_id: str
    area: Tuple[float, float, float, float]
    altitude_min_ft: float
    altitude_max_ft: float
    reason: str
    valid_from: float
    valid_until: float


# Simulated UASFM grid: airspace class -> max altitude (ft AGL)
UASFM_DEFAULTS: Dict[str, int] = {
    "B": 0, "C": 0, "D": 0, "E-surface": 0,
    "E-other": 400, "G": 400,
}

# Simulated airport locations (lat, lon, class)
SAMPLE_AIRPORTS = [
    (37.5665, 126.9780, "B"),  # Incheon
    (35.1796, 128.9382, "C"),  # Gimhae
    (33.5104, 126.4914, "D"),  # Jeju
]


class FAA_LAANC:
    """Simulated FAA LAANC authorization system."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self._next_id = 0
        self.authorizations: Dict[str, LAANCAuthorization] = {}
        self.tfrs: List[TFR] = []
        self.facility_map: Dict[str, int] = dict(UASFM_DEFAULTS)

    def _gen_id(self) -> str:
        self._next_id += 1
        return f"LAANC-{self._next_id:06d}"

    def request_authorization(self, request: LAANCRequest) -> LAANCAuthorization:
        req_id = self._gen_id()

        center_lat = (request.operation_area[0] + request.operation_area[2]) / 2
        center_lon = (request.operation_area[1] + request.operation_area[3]) / 2
        airspace = self.check_airspace_class(center_lat, center_lon)

        max_allowed = UASFM_DEFAULTS.get(airspace, 400)

        conditions: List[str] = []
        if request.max_altitude_ft > 400:
            status = AuthorizationStatus.REJECTED
            authorized_alt = 0.0
            conditions.append("Exceeds 400ft AGL limit")
        elif request.max_altitude_ft > max_allowed and max_allowed == 0:
            status = AuthorizationStatus.REJECTED
            authorized_alt = 0.0
            conditions.append(f"Class {airspace} airspace - no auto-authorization")
        else:
            status = AuthorizationStatus.APPROVED
            authorized_alt = min(request.max_altitude_ft, max_allowed if max_allowed > 0 else 400)
            conditions.append("Standard Part 107 conditions apply")

        auth = LAANCAuthorization(
            request_id=req_id,
            status=status,
            authorized_altitude_ft=authorized_alt,
            conditions=conditions,
            valid_from=request.start_time,
            valid_until=request.end_time,
            facility_map_id=f"UASFM-{airspace}",
        )
        self.authorizations[req_id] = auth
        return auth

    def check_authorization_status(self, request_id: str) -> str:
        if request_id not in self.authorizations:
            return "not_found"
        return self.authorizations[request_id].status.value

    def cancel_authorization(self, request_id: str) -> bool:
        if request_id not in self.authorizations:
            return False
        self.authorizations[request_id].status = AuthorizationStatus.CANCELLED
        return True

    def get_facility_map(self, area: Tuple[float, float, float, float]) -> Dict[str, Any]:
        center_lat = (area[0] + area[2]) / 2
        center_lon = (area[1] + area[3]) / 2
        airspace = self.check_airspace_class(center_lat, center_lon)
        return {
            "airspace_class": airspace,
            "max_altitude_ft": UASFM_DEFAULTS.get(airspace, 400),
            "area": area,
            "grid_cells": 1,
        }

    def check_airspace_class(self, lat: float, lon: float) -> str:
        for ap_lat, ap_lon, ap_class in SAMPLE_AIRPORTS:
            dist = np.sqrt((lat - ap_lat) ** 2 + (lon - ap_lon) ** 2) * 111320
            if dist < 9260:  # ~5 NM
                return ap_class
        return "G"

    def is_near_airport(self, lat: float, lon: float, radius_nm: float = 5.0) -> bool:
        radius_m = radius_nm * 1852.0
        for ap_lat, ap_lon, _ in SAMPLE_AIRPORTS:
            dist = np.sqrt((lat - ap_lat) ** 2 + (lon - ap_lon) ** 2) * 111320
            if dist < radius_m:
                return True
        return False

    def get_tfrs(self, area: Tuple[float, float, float, float]) -> List[TFR]:
        now = time.time()
        active = []
        for tfr in self.tfrs:
            if tfr.valid_until > now:
                if (tfr.area[0] <= area[2] and tfr.area[2] >= area[0] and
                        tfr.area[1] <= area[3] and tfr.area[3] >= area[1]):
                    active.append(tfr)
        return active

    def add_tfr(self, tfr: TFR) -> None:
        self.tfrs.append(tfr)

    def validate_part107_compliance(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        violations = []
        if operation.get("altitude_ft", 0) > 400:
            violations.append("Exceeds 400ft AGL")
        if operation.get("speed_kt", 0) > 100:
            violations.append("Exceeds 100 knots ground speed")
        if operation.get("night_ops", False) and not operation.get("anti_collision_light", False):
            violations.append("Night ops without anti-collision lighting")
        if not operation.get("visual_line_of_sight", True):
            violations.append("Beyond visual line of sight without waiver")
        if operation.get("over_people", False) and not operation.get("category_certified", False):
            violations.append("Over people without category certification")

        return {"compliant": len(violations) == 0, "violations": violations}
