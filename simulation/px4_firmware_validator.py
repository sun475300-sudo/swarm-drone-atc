"""P691: PX4 v1.15+ 펌웨어 버전·파라미터 검증 모듈."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FirmwareFamily(Enum):
    PX4 = "PX4"
    ARDUPILOT = "ArduPilot"
    UNKNOWN = "Unknown"


class ValidationResult(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


# PX4 v1.15+에서 요구되는 최소 파라미터 값 (안전 기준)
REQUIRED_PARAMS: dict[str, dict[str, Any]] = {
    "COM_RCL_EXCEPT": {"min": 0, "max": 3, "desc": "RC loss exception mask"},
    "NAV_RCL_ACT": {"allowed": [1, 2, 3, 4], "desc": "RC loss failsafe action"},
    "NAV_DLL_ACT": {"allowed": [1, 2, 3, 4], "desc": "Data link loss action"},
    "MIS_TAKEOFF_ALT": {"min": 1.0, "max": 300.0, "desc": "Takeoff altitude (m)"},
    "MPC_THR_MIN": {"min": 0.05, "max": 0.3, "desc": "Min throttle"},
    "MPC_THR_MAX": {"min": 0.7, "max": 1.0, "desc": "Max throttle"},
    "GF_ACTION": {"allowed": [1, 2, 3, 4], "desc": "Geofence violation action"},
    "EKF2_AID_MASK": {"min": 1, "desc": "EKF2 sensor fusion sources"},
    "CBRK_SUPPLY_CHK": {"allowed": [0], "desc": "Supply voltage check (must be enabled)"},
    "SDLOG_MODE": {"allowed": [0, 1, 2], "desc": "Logging mode"},
}

MIN_PX4_VERSION = (1, 15, 0)
MIN_ARDUPILOT_VERSION = (4, 4, 0)


@dataclass
class VersionInfo:
    family: FirmwareFamily
    major: int
    minor: int
    patch: int
    git_hash: str = ""

    @classmethod
    def parse(cls, version_string: str) -> "VersionInfo":
        """'PX4 v1.15.2-abc1234' 형식 파싱."""
        s = version_string.strip()
        family = FirmwareFamily.UNKNOWN
        if s.startswith("PX4"):
            family = FirmwareFamily.PX4
            s = s.removeprefix("PX4").strip().lstrip("v")
        elif s.startswith("ArduPilot") or s.startswith("ArduCopter"):
            family = FirmwareFamily.ARDUPILOT
            s = s.split()[-1].lstrip("v")

        parts = s.split("-", 1)
        git_hash = parts[1] if len(parts) > 1 else ""
        version_nums = parts[0].split(".")
        try:
            major, minor, patch = int(version_nums[0]), int(version_nums[1] if len(version_nums) > 1 else 0), int(version_nums[2] if len(version_nums) > 2 else 0)
        except (ValueError, IndexError):
            major, minor, patch = 0, 0, 0

        return cls(family=family, major=major, minor=minor, patch=patch, git_hash=git_hash)

    @property
    def tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


@dataclass
class ParamCheck:
    param: str
    value: Any
    result: ValidationResult
    message: str


@dataclass
class ValidationReport:
    version: VersionInfo
    version_ok: bool
    param_checks: list[ParamCheck] = field(default_factory=list)
    overall: ValidationResult = ValidationResult.PASS

    @property
    def failures(self) -> list[ParamCheck]:
        return [c for c in self.param_checks if c.result == ValidationResult.FAIL]

    @property
    def warnings(self) -> list[ParamCheck]:
        return [c for c in self.param_checks if c.result == ValidationResult.WARN]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": f"{self.version.family.value} {self.version.major}.{self.version.minor}.{self.version.patch}",
            "version_ok": self.version_ok,
            "overall": self.overall.value,
            "failures": len(self.failures),
            "warnings": len(self.warnings),
        }


class PX4FirmwareValidator:
    """PX4/ArduPilot 펌웨어 버전 및 안전 파라미터 검증기."""

    def validate(self, version_string: str, params: dict[str, Any]) -> ValidationReport:
        version = VersionInfo.parse(version_string)
        version_ok = self._check_version(version)

        checks = [self._check_param(name, params.get(name), spec)
                  for name, spec in REQUIRED_PARAMS.items()]

        report = ValidationReport(version=version, version_ok=version_ok, param_checks=checks)
        if not version_ok or any(c.result == ValidationResult.FAIL for c in checks):
            report.overall = ValidationResult.FAIL
        elif any(c.result == ValidationResult.WARN for c in checks):
            report.overall = ValidationResult.WARN

        return report

    def _check_version(self, v: VersionInfo) -> bool:
        if v.family == FirmwareFamily.PX4:
            return v.tuple >= MIN_PX4_VERSION
        if v.family == FirmwareFamily.ARDUPILOT:
            return v.tuple >= MIN_ARDUPILOT_VERSION
        return False

    def _check_param(self, name: str, value: Any, spec: dict[str, Any]) -> ParamCheck:
        if value is None:
            return ParamCheck(name, value, ValidationResult.WARN, f"{name}: 파라미터 없음 (기본값 사용)")

        if "allowed" in spec:
            if value not in spec["allowed"]:
                return ParamCheck(name, value, ValidationResult.FAIL,
                                  f"{name}={value} 허용값 외 ({spec['allowed']}): {spec['desc']}")
        if "min" in spec and value < spec["min"]:
            return ParamCheck(name, value, ValidationResult.FAIL,
                              f"{name}={value} < min={spec['min']}: {spec['desc']}")
        if "max" in spec and value > spec["max"]:
            return ParamCheck(name, value, ValidationResult.FAIL,
                              f"{name}={value} > max={spec['max']}: {spec['desc']}")

        return ParamCheck(name, value, ValidationResult.PASS, f"{name}={value} OK")
