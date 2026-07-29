"""Phase 684: FAA LAANC 연동 인터페이스 시뮬레이션."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class AuthorizationStatus(Enum):
    """``AuthorizationStatus`` 관련 기능을 제공한다."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AirspaceClassFAA(Enum):
    """``AirspaceClassFAA`` 관련 기능을 제공한다."""
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    G = "G"


class OperationType(Enum):
    """``OperationType`` 관련 기능을 제공한다."""
    PART_107 = "part_107"
    RECREATIONAL = "recreational"
    PUBLIC_SAFETY = "public_safety"
    WAIVER = "waiver"


@dataclass
class LAANCRequest:
    """``LAANCRequest`` 데이터를 표현한다."""
    operator_id: str
    drone_registration: str
    operation_area: tuple[float, float, float, float]  # min_lat, min_lon, max_lat, max_lon
    max_altitude_ft: float
    start_time: float
    end_time: float
    operation_type: OperationType = OperationType.PART_107


@dataclass
class LAANCAuthorization:
    """``LAANCAuthorization`` 관련 기능을 제공한다."""
    request_id: str
    status: AuthorizationStatus
    authorized_altitude_ft: float
    conditions: list[str] = field(default_factory=list)
    valid_from: float = 0.0
    valid_until: float = 0.0
    facility_map_id: str = ""


@dataclass
class TFR:
    """``TFR`` 관련 기능을 제공한다."""
    tfr_id: str
    area: tuple[float, float, float, float]
    altitude_min_ft: float
    altitude_max_ft: float
    reason: str
    valid_from: float
    valid_until: float


# Simulated UASFM grid: airspace class -> max altitude (ft AGL)
UASFM_DEFAULTS: dict[str, int] = {
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
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self._next_id = 0
        self.authorizations: dict[str, LAANCAuthorization] = {}
        self.tfrs: list[TFR] = []
        self.facility_map: dict[str, int] = dict(UASFM_DEFAULTS)

    def _gen_id(self) -> str:
        self._next_id += 1
        return f"LAANC-{self._next_id:06d}"

    def request_authorization(self, request: LAANCRequest) -> LAANCAuthorization:
        """``request_authorization`` 동작을 수행한다."""
        req_id = self._gen_id()

        center_lat = (request.operation_area[0] + request.operation_area[2]) / 2
        center_lon = (request.operation_area[1] + request.operation_area[3]) / 2
        airspace = self.check_airspace_class(center_lat, center_lon)

        max_allowed = UASFM_DEFAULTS.get(airspace, 400)

        conditions: list[str] = []
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
        """`authorization status` 결과를 계산하거나 판정한다."""
        if request_id not in self.authorizations:
            return "not_found"
        return self.authorizations[request_id].status.value

    def cancel_authorization(self, request_id: str) -> bool:
        """``cancel_authorization`` 동작을 수행한다."""
        if request_id not in self.authorizations:
            return False
        self.authorizations[request_id].status = AuthorizationStatus.CANCELLED
        return True

    def get_facility_map(self, area: tuple[float, float, float, float]) -> dict[str, Any]:
        """`facility map` 정보를 조회한다."""
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
        """`airspace class` 결과를 계산하거나 판정한다."""
        for ap_lat, ap_lon, ap_class in SAMPLE_AIRPORTS:
            dist = np.sqrt((lat - ap_lat) ** 2 + (lon - ap_lon) ** 2) * 111320
            if dist < 9260:  # ~5 NM
                return ap_class
        return "G"

    def is_near_airport(self, lat: float, lon: float, radius_nm: float = 5.0) -> bool:
        """`near airport` 여부를 반환한다."""
        radius_m = radius_nm * 1852.0
        for ap_lat, ap_lon, _ in SAMPLE_AIRPORTS:
            dist = np.sqrt((lat - ap_lat) ** 2 + (lon - ap_lon) ** 2) * 111320
            if dist < radius_m:
                return True
        return False

    def get_tfrs(self, area: tuple[float, float, float, float]) -> list[TFR]:
        """`tfrs` 정보를 조회한다."""
        now = time.time()
        active = []
        for tfr in self.tfrs:
            if tfr.valid_until > now and (tfr.area[0] <= area[2] and tfr.area[2] >= area[0] and
                    tfr.area[1] <= area[3] and tfr.area[3] >= area[1]):
                active.append(tfr)
        return active

    def add_tfr(self, tfr: TFR) -> None:
        """`tfr` 항목을 추가한다."""
        self.tfrs.append(tfr)

    def validate_part107_compliance(self, operation: dict[str, Any]) -> dict[str, Any]:
        """`part107 compliance` 결과를 계산하거나 판정한다."""
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
