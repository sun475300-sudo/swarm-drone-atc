"""
Phase 488: Mission Critical Validator
비행 임무 사전/실시간 검증, 안전 제약 조건 체크, 비상 절차 검증.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set


class ValidationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKER = "blocker"


class MissionPhase(Enum):
    PRE_FLIGHT = "pre_flight"
    TAKEOFF = "takeoff"
    EN_ROUTE = "en_route"
    ON_STATION = "on_station"
    RETURN = "return"
    LANDING = "landing"


class CheckCategory(Enum):
    BATTERY = "battery"
    WEATHER = "weather"
    AIRSPACE = "airspace"
    HARDWARE = "hardware"
    COMMUNICATION = "communication"
    GEOFENCE = "geofence"
    PAYLOAD = "payload"
    REDUNDANCY = "redundancy"


@dataclass
class ValidationResult:
    check_id: str
    category: CheckCategory
    level: ValidationLevel
    message: str
    passed: bool
    value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class MissionPlan:
    mission_id: str
    drone_ids: List[str]
    waypoints: List[np.ndarray]
    max_altitude_m: float = 120.0
    duration_min: float = 30.0
    payload_kg: float = 0.0
    requires_rtk: bool = False
    emergency_landing_sites: List[np.ndarray] = field(default_factory=list)


@dataclass
class SafetyEnvelope:
    min_altitude_m: float = 5.0
    max_altitude_m: float = 150.0
    max_speed_mps: float = 20.0
    min_battery_pct: float = 20.0
    max_wind_mps: float = 12.0
    min_satellites: int = 8
    max_distance_m: float = 5000.0
    min_comm_signal_dbm: float = -80.0


class MissionCriticalValidator:
    """Comprehensive mission validation engine."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.envelope = SafetyEnvelope()
        self.results: List[ValidationResult] = []
        self._check_counter = 0

    def _add_result(self, category: CheckCategory, level: ValidationLevel,
                    message: str, passed: bool, value: float = None,
                    threshold: float = None) -> ValidationResult:
        self._check_counter += 1
        result = ValidationResult(
            f"CHK-{self._check_counter:04d}", category, level,
            message, passed, value, threshold)
        self.results.append(result)
        return result

    def validate_battery(self, battery_pct: float, flight_time_min: float,
                         consumption_rate: float = 1.5) -> List[ValidationResult]:
        results = []
        required_pct = flight_time_min * consumption_rate + self.envelope.min_battery_pct
        results.append(self._add_result(
            CheckCategory.BATTERY, ValidationLevel.CRITICAL,
            f"Battery {battery_pct:.0f}% vs required {required_pct:.0f}%",
            battery_pct >= required_pct, battery_pct, required_pct))

        if battery_pct < 50:
            results.append(self._add_result(
                CheckCategory.BATTERY, ValidationLevel.WARNING,
                f"Battery below 50%: {battery_pct:.0f}%",
                False, battery_pct, 50))
        return results

    def validate_weather(self, wind_speed: float, visibility_m: float = 5000,
                         precipitation: bool = False) -> List[ValidationResult]:
        results = []
        results.append(self._add_result(
            CheckCategory.WEATHER, ValidationLevel.CRITICAL,
            f"Wind {wind_speed:.1f} m/s vs limit {self.envelope.max_wind_mps}",
            wind_speed <= self.envelope.max_wind_mps, wind_speed, self.envelope.max_wind_mps))
        results.append(self._add_result(
            CheckCategory.WEATHER, ValidationLevel.WARNING,
            f"Visibility {visibility_m:.0f}m",
            visibility_m >= 1000, visibility_m, 1000))
        if precipitation:
            results.append(self._add_result(
                CheckCategory.WEATHER, ValidationLevel.WARNING,
                "Precipitation detected", False))
        return results

    def validate_airspace(self, waypoints: List[np.ndarray],
                          restricted_zones: List[Dict] = None) -> List[ValidationResult]:
        results = []
        for i, wp in enumerate(waypoints):
            alt = wp[2] if len(wp) > 2 else 0
            if alt > self.envelope.max_altitude_m:
                results.append(self._add_result(
                    CheckCategory.AIRSPACE, ValidationLevel.BLOCKER,
                    f"WP{i} altitude {alt:.0f}m exceeds {self.envelope.max_altitude_m:.0f}m",
                    False, alt, self.envelope.max_altitude_m))
            if alt < self.envelope.min_altitude_m:
                results.append(self._add_result(
                    CheckCategory.AIRSPACE, ValidationLevel.CRITICAL,
                    f"WP{i} altitude {alt:.0f}m below minimum {self.envelope.min_altitude_m:.0f}m",
                    False, alt, self.envelope.min_altitude_m))

        if restricted_zones:
            for zone in restricted_zones:
                center = np.array(zone.get("center", [0, 0, 0]))
                radius = zone.get("radius", 100)
                for i, wp in enumerate(waypoints):
                    dist = np.linalg.norm(wp[:2] - center[:2])
                    if dist < radius:
                        results.append(self._add_result(
                            CheckCategory.AIRSPACE, ValidationLevel.BLOCKER,
                            f"WP{i} inside restricted zone (dist={dist:.0f}m)",
                            False, dist, radius))

        if not results:
            results.append(self._add_result(
                CheckCategory.AIRSPACE, ValidationLevel.INFO,
                "All waypoints within safe airspace", True))
        return results

    def validate_mission(self, plan: MissionPlan, battery_pct: float = 95,
                         wind_speed: float = 5.0) -> Dict:
        self.results = []
        self._check_counter = 0

        self.validate_battery(battery_pct, plan.duration_min)
        self.validate_weather(wind_speed)
        self.validate_airspace(plan.waypoints)

        total_dist = 0
        for i in range(1, len(plan.waypoints)):
            total_dist += np.linalg.norm(plan.waypoints[i] - plan.waypoints[i-1])
        if total_dist > self.envelope.max_distance_m:
            self._add_result(CheckCategory.GEOFENCE, ValidationLevel.CRITICAL,
                           f"Total distance {total_dist:.0f}m exceeds {self.envelope.max_distance_m}m",
                           False, total_dist, self.envelope.max_distance_m)

        if not plan.emergency_landing_sites:
            self._add_result(CheckCategory.REDUNDANCY, ValidationLevel.WARNING,
                           "No emergency landing sites defined", False)
        else:
            self._add_result(CheckCategory.REDUNDANCY, ValidationLevel.INFO,
                           f"{len(plan.emergency_landing_sites)} emergency sites defined", True)

        if len(plan.drone_ids) > 1:
            self._add_result(CheckCategory.COMMUNICATION, ValidationLevel.INFO,
                           f"Multi-drone mission: {len(plan.drone_ids)} drones", True)

        blockers = [r for r in self.results if r.level == ValidationLevel.BLOCKER and not r.passed]
        criticals = [r for r in self.results if r.level == ValidationLevel.CRITICAL and not r.passed]
        go = len(blockers) == 0 and len(criticals) == 0

        return {
            "mission_id": plan.mission_id,
            "go_no_go": "GO" if go else "NO-GO",
            "total_checks": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "blockers": len(blockers),
            "criticals": len(criticals),
            "warnings": sum(1 for r in self.results if r.level == ValidationLevel.WARNING and not r.passed),
        }

    def summary(self) -> Dict:
        return {
            "total_validations": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "by_category": {cat.value: sum(1 for r in self.results if r.category == cat)
                          for cat in CheckCategory if any(r.category == cat for r in self.results)},
        }
