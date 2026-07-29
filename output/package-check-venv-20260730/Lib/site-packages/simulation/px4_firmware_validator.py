"""Phase 691: PX4 v1.15+ 펌웨어 검증 및 파라미터 확인 스크립트."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class FirmwareStatus(Enum):
    """펌웨어 검증 상태."""
    UNKNOWN = "unknown"
    VALID = "valid"
    VERSION_MISMATCH = "version_mismatch"
    PARAM_INVALID = "param_invalid"
    NO_HEARTBEAT = "no_heartbeat"


@dataclass
class FirmwareInfo:
    """PX4 펌웨어 정보."""
    version_major: int = 0
    version_minor: int = 0
    version_patch: int = 0
    custom_mode: int = 0
    vehicle_type: str = "multirotor"
    board_id: int = 0

    @property
    def version_str(self) -> str:
        return f"{self.version_major}.{self.version_minor}.{self.version_patch}"

    def meets_minimum(self, major: int, minor: int) -> bool:
        if self.version_major != major:
            return self.version_major > major
        return self.version_minor >= minor


@dataclass
class ParamValidationResult:
    """파라미터 검증 결과."""
    param_name: str
    expected: Any
    actual: Any
    passed: bool
    note: str = ""


@dataclass
class ValidationReport:
    """전체 검증 보고서."""
    status: FirmwareStatus = FirmwareStatus.UNKNOWN
    firmware: FirmwareInfo = field(default_factory=FirmwareInfo)
    heartbeat_latency_ms: float = 0.0
    param_results: list[ParamValidationResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validated_at: float = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return self.status == FirmwareStatus.VALID

    @property
    def param_pass_rate(self) -> float:
        if not self.param_results:
            return 1.0
        return sum(1 for r in self.param_results if r.passed) / len(self.param_results)


# PX4 v1.15 필수 파라미터 기준값
PX4_REQUIRED_PARAMS: dict[str, Any] = {
    "COM_RC_LOSS_T": 0.5,
    "COM_OF_LOSS_T": 1.0,
    "GF_ACTION": 1,
    "RTL_RETURN_ALT": 30.0,
    "EKF2_AID_MASK": 1,
    "MC_YAW_P": 2.8,
    "MPC_XY_P": 0.95,
    "MPC_Z_P": 1.0,
}

PARAM_TOLERANCE = 0.05


class PX4FirmwareValidator:
    """PX4 v1.15+ 펌웨어 및 파라미터 검증기 (시뮬레이션/실기 공용)."""

    MIN_VERSION_MAJOR = 1
    MIN_VERSION_MINOR = 15
    HEARTBEAT_TIMEOUT_MS = 5000.0

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self._simulated_params: dict[str, Any] = dict(PX4_REQUIRED_PARAMS)
        self._sim_firmware = FirmwareInfo(
            version_major=1, version_minor=15, version_patch=0,
            vehicle_type="multirotor", board_id=50,
        )

    def simulate_heartbeat(self) -> float:
        """시뮬레이션 모드: 하트비트 레이턴시(ms) 반환."""
        return float(self.rng.uniform(1.0, 15.0))

    def probe_heartbeat(self, host: str = "127.0.0.1", port: int = 14550) -> float:
        """MAVLink 하트비트 레이턴시 측정 (시뮬 모드: UDP 연결 없이 난수 반환)."""
        return self.simulate_heartbeat()

    def fetch_firmware_info(self) -> FirmwareInfo:
        """펌웨어 정보 조회 (시뮬 모드: 고정값 반환)."""
        return self._sim_firmware

    def fetch_params(self) -> dict[str, Any]:
        """파라미터 조회 (시뮬 모드: 내부 dict 반환)."""
        return dict(self._simulated_params)

    def set_sim_param(self, name: str, value: Any) -> None:
        """시뮬레이션용 파라미터 강제 설정."""
        self._simulated_params[name] = value

    def validate(self) -> ValidationReport:
        """전체 검증 실행."""
        report = ValidationReport()

        latency = self.probe_heartbeat()
        report.heartbeat_latency_ms = latency
        if latency > self.HEARTBEAT_TIMEOUT_MS:
            report.status = FirmwareStatus.NO_HEARTBEAT
            report.errors.append(f"heartbeat timeout: {latency:.1f}ms")
            return report

        fw = self.fetch_firmware_info()
        report.firmware = fw
        if not fw.meets_minimum(self.MIN_VERSION_MAJOR, self.MIN_VERSION_MINOR):
            report.status = FirmwareStatus.VERSION_MISMATCH
            report.errors.append(
                f"version {fw.version_str} < required {self.MIN_VERSION_MAJOR}.{self.MIN_VERSION_MINOR}"
            )
            return report

        params = self.fetch_params()
        all_ok = True
        for name, expected in PX4_REQUIRED_PARAMS.items():
            actual = params.get(name)
            if actual is None:
                passed = False
                note = "missing"
            elif isinstance(expected, float):
                passed = abs(actual - expected) <= PARAM_TOLERANCE * max(abs(expected), 1e-6)
                note = "" if passed else f"{actual:.3f} ≠ {expected:.3f}"
            else:
                passed = actual == expected
                note = "" if passed else f"{actual} ≠ {expected}"
            result = ParamValidationResult(name, expected, actual, passed, note)
            report.param_results.append(result)
            if not passed:
                all_ok = False
                report.errors.append(f"param {name}: {note}")

        report.status = FirmwareStatus.VALID if all_ok else FirmwareStatus.PARAM_INVALID
        return report
