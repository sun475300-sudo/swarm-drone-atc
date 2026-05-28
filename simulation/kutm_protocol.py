"""Phase 681: K-UTM 표준 프로토콜 준수 시뮬레이션."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np


class AirspaceClass(Enum):
    """``AirspaceClass`` 관련 기능을 제공한다."""
    RESTRICTED = "restricted"
    CONTROLLED = "controlled"
    OPEN = "open"


class PlanStatus(Enum):
    """``PlanStatus`` 관련 기능을 제공한다."""
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class FlightPlan:
    """``FlightPlan`` 관련 기능을 제공한다."""
    plan_id: str
    operator_id: str
    drone_id: str
    departure_time: float
    arrival_time: float
    waypoints: list[tuple[float, float, float]]  # (lat, lon, alt)
    altitude_min: float
    altitude_max: float
    purpose: str = "survey"
    status: PlanStatus = PlanStatus.SUBMITTED


@dataclass
class NOTAM:
    """``NOTAM`` 관련 기능을 제공한다."""
    notam_id: str
    area_center: tuple[float, float]
    radius_m: float
    altitude_min: float
    altitude_max: float
    description: str
    valid_from: float
    valid_until: float


@dataclass
class DroneRegistration:
    """``DroneRegistration`` 관련 기능을 제공한다."""
    registration_id: str
    drone_id: str
    manufacturer: str
    model: str
    max_takeoff_weight_kg: float
    serial_number: str


class KUTMProtocol:
    """Korean UTM standard protocol simulation."""

    def __init__(self, seed: int = 42) -> None:
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self._next_id = 0
        self.flight_plans: dict[str, FlightPlan] = {}
        self.notams: list[NOTAM] = []
        self.registered_drones: dict[str, DroneRegistration] = {}
        self.operators: dict[str, dict[str, Any]] = {}
        self.telemetry_log: list[dict[str, Any]] = []

        self.airspace_grid: dict[tuple[int, int], AirspaceClass] = {}

    def _gen_id(self, prefix: str = "KU") -> str:
        self._next_id += 1
        return f"{prefix}-{self._next_id:06d}"

    def register_drone(self, drone_spec: dict[str, Any]) -> str:
        """`drone` 항목을 추가한다."""
        reg_id = self._gen_id("REG")
        self.registered_drones[reg_id] = DroneRegistration(
            registration_id=reg_id,
            drone_id=drone_spec.get("drone_id", "unknown"),
            manufacturer=drone_spec.get("manufacturer", "unknown"),
            model=drone_spec.get("model", "unknown"),
            max_takeoff_weight_kg=drone_spec.get("mtow_kg", 2.0),
            serial_number=drone_spec.get("serial", ""),
        )
        return reg_id

    def validate_operator_credentials(self, operator_id: str) -> bool:
        """`operator credentials` 결과를 계산하거나 판정한다."""
        if operator_id not in self.operators:
            self.operators[operator_id] = {
                "certified": self.rng.random() > 0.1,
                "license_valid": True,
            }
        return self.operators[operator_id].get("certified", False)

    def submit_flight_plan(self, plan: FlightPlan) -> dict[str, Any]:
        """``submit_flight_plan`` 동작을 수행한다."""
        conflicts = self.check_airspace_availability(
            plan.waypoints, (plan.departure_time, plan.arrival_time)
        )
        if conflicts:
            plan.status = PlanStatus.REJECTED
            self.flight_plans[plan.plan_id] = plan
            return {"approved": False, "reason": "Airspace conflict", "conflicts": conflicts}

        if plan.altitude_max > 120.0:
            plan.status = PlanStatus.REJECTED
            self.flight_plans[plan.plan_id] = plan
            return {"approved": False, "reason": "Altitude exceeds 120m limit"}

        plan.status = PlanStatus.APPROVED
        self.flight_plans[plan.plan_id] = plan
        approval_id = self._gen_id("APR")
        return {"approved": True, "approval_id": approval_id, "plan_id": plan.plan_id}

    def cancel_flight_plan(self, plan_id: str) -> bool:
        """``cancel_flight_plan`` 동작을 수행한다."""
        if plan_id not in self.flight_plans:
            return False
        self.flight_plans[plan_id].status = PlanStatus.CANCELLED
        return True

    def update_flight_plan(self, plan_id: str, updates: dict[str, Any]) -> bool:
        """`flight plan` 상태를 갱신한다."""
        if plan_id not in self.flight_plans:
            return False
        plan = self.flight_plans[plan_id]
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        return True

    def get_flight_plan_status(self, plan_id: str) -> str:
        """`flight plan status` 정보를 조회한다."""
        if plan_id not in self.flight_plans:
            return "not_found"
        return self.flight_plans[plan_id].status.value

    def report_telemetry(
        self, drone_id: str, position: tuple[float, float, float],
        velocity: tuple[float, float, float], battery: float,
    ) -> bool:
        """``report_telemetry`` 동작을 수행한다."""
        self.telemetry_log.append({
            "drone_id": drone_id,
            "position": position,
            "velocity": velocity,
            "battery": battery,
            "timestamp": time.time(),
        })
        return True

    def check_airspace_availability(
        self, waypoints: list[tuple[float, float, float]],
        time_window: tuple[float, float],
    ) -> list[dict[str, Any]]:
        """`airspace availability` 결과를 계산하거나 판정한다."""
        conflicts = []
        for wp in waypoints:
            for notam in self.notams:
                dx = wp[0] - notam.area_center[0]
                dy = wp[1] - notam.area_center[1]
                dist = np.sqrt(dx * dx + dy * dy)
                if dist < notam.radius_m and notam.altitude_min <= wp[2] <= notam.altitude_max:
                    conflicts.append({
                        "notam_id": notam.notam_id,
                        "waypoint": wp,
                        "type": "NOTAM conflict",
                    })
        return conflicts

    def get_notams(self, area_center: tuple[float, float], radius_m: float = 5000.0) -> list[NOTAM]:
        """`notams` 정보를 조회한다."""
        result = []
        now = time.time()
        for notam in self.notams:
            dx = area_center[0] - notam.area_center[0]
            dy = area_center[1] - notam.area_center[1]
            if np.sqrt(dx * dx + dy * dy) < radius_m and notam.valid_until > now:
                result.append(notam)
        return result

    def add_notam(self, notam: NOTAM) -> None:
        """`notam` 항목을 추가한다."""
        self.notams.append(notam)

    def get_stats(self) -> dict[str, Any]:
        """`stats` 정보를 조회한다."""
        statuses = {}
        for plan in self.flight_plans.values():
            s = plan.status.value
            statuses[s] = statuses.get(s, 0) + 1
        return {
            "total_plans": len(self.flight_plans),
            "plans_by_status": statuses,
            "registered_drones": len(self.registered_drones),
            "active_notams": len(self.notams),
            "telemetry_reports": len(self.telemetry_log),
        }
