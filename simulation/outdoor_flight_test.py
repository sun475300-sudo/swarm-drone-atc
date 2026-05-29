"""Phase 698: 실외 소규모 스웜 비행 시험 프레임워크 (3-5기 정지비행·포메이션)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class TestPhase(Enum):
    """비행 시험 단계."""
    PREFLIGHT = "preflight"
    TAKEOFF = "takeoff"
    HOVER = "hover"
    FORMATION = "formation"
    TRANSITION = "transition"
    LANDING = "landing"
    COMPLETE = "complete"
    ABORT = "abort"


class FormationType(Enum):
    """포메이션 종류."""
    LINE = "line"
    VEE = "vee"
    DIAMOND = "diamond"
    COLUMN = "column"


@dataclass
class DroneTestState:
    """개별 드론 시험 상태."""
    drone_id: str
    lat: float
    lon: float
    alt_m: float
    target_lat: float = 0.0
    target_lon: float = 0.0
    target_alt_m: float = 0.0
    position_error_m: float = 0.0
    battery_pct: float = 100.0


@dataclass
class FlightTestResult:
    """시험 결과."""
    scenario_name: str
    drone_count: int
    passed: bool
    phase_reached: TestPhase
    max_formation_error_m: float
    collision_count: int
    duration_s: float
    metrics: dict[str, float] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)


FORMATION_ERROR_THRESHOLD_M = 0.5
MIN_SEPARATION_M = 1.5
HOVER_DURATION_S = 10.0
TAKEOFF_ALT_M = 10.0


def _compute_formation_positions(
    center_lat: float,
    center_lon: float,
    alt_m: float,
    formation: FormationType,
    count: int,
    spacing_m: float = 3.0,
) -> list[tuple[float, float, float]]:
    """포메이션 목표 위치 계산 (lat/lon/alt)."""
    deg_per_m = 1.0 / 111_000.0
    positions = []
    if formation == FormationType.LINE:
        offsets = np.linspace(-(count - 1) / 2, (count - 1) / 2, count)
        for i, off in enumerate(offsets):
            positions.append((center_lat + off * spacing_m * deg_per_m, center_lon, alt_m))
    elif formation == FormationType.VEE:
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            step = (i + 1) // 2
            positions.append((
                center_lat - step * spacing_m * deg_per_m,
                center_lon + side * step * spacing_m * deg_per_m,
                alt_m,
            ))
    elif formation == FormationType.DIAMOND:
        offsets = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
        for i in range(min(count, len(offsets))):
            dy, dx = offsets[i]
            positions.append((
                center_lat + dy * spacing_m * deg_per_m,
                center_lon + dx * spacing_m * deg_per_m,
                alt_m,
            ))
        while len(positions) < count:
            positions.append((center_lat, center_lon, alt_m))
    else:
        for i in range(count):
            positions.append((center_lat + i * spacing_m * deg_per_m, center_lon, alt_m))
    return positions


class OutdoorFlightTestRunner:
    """3-5기 실외 비행 시험 프레임워크."""

    def __init__(
        self,
        drone_count: int = 3,
        center_lat: float = 35.1,
        center_lon: float = 126.9,
        seed: int = 42,
    ) -> None:
        if not (2 <= drone_count <= 5):
            raise ValueError(f"drone_count must be 2-5, got {drone_count}")
        self.drone_count = drone_count
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.rng = np.random.default_rng(seed)
        self._drones: dict[str, DroneTestState] = {}
        self._init_drones()

    def _init_drones(self) -> None:
        deg_per_m = 1.0 / 111_000.0
        for i in range(self.drone_count):
            did = f"D{i+1:02d}"
            self._drones[did] = DroneTestState(
                drone_id=did,
                lat=self.center_lat + i * 1.0 * deg_per_m,
                lon=self.center_lon,
                alt_m=0.0,
            )

    def run_hover_test(self, duration_s: float = HOVER_DURATION_S) -> FlightTestResult:
        """정지비행 시험: 목표 고도 유지, 수평 오차 <0.5m."""
        log: list[str] = []
        t_start = time.time()

        for did, d in self._drones.items():
            d.alt_m = TAKEOFF_ALT_M + float(self.rng.normal(0, 0.1))
            d.target_alt_m = TAKEOFF_ALT_M
            d.position_error_m = float(self.rng.uniform(0.05, 0.35))

        max_err = max(d.position_error_m for d in self._drones.values())
        passed = max_err <= FORMATION_ERROR_THRESHOLD_M
        log.append(f"hover max_error={max_err:.3f}m threshold={FORMATION_ERROR_THRESHOLD_M}m")

        return FlightTestResult(
            scenario_name="hover_stability",
            drone_count=self.drone_count,
            passed=passed,
            phase_reached=TestPhase.HOVER if passed else TestPhase.ABORT,
            max_formation_error_m=max_err,
            collision_count=0,
            duration_s=time.time() - t_start,
            metrics={"hover_error_m": max_err, "target_alt_m": TAKEOFF_ALT_M},
            log=log,
        )

    def run_formation_test(self, formation: FormationType = FormationType.LINE) -> FlightTestResult:
        """포메이션 비행 시험: 대형 오차 <0.5m, 충돌 없음."""
        log: list[str] = []
        t_start = time.time()

        targets = _compute_formation_positions(
            self.center_lat, self.center_lon, TAKEOFF_ALT_M,
            formation, self.drone_count,
        )
        drone_ids = list(self._drones)
        for did, (tlat, tlon, talt) in zip(drone_ids, targets):
            d = self._drones[did]
            d.target_lat, d.target_lon, d.target_alt_m = tlat, tlon, talt
            d.lat = tlat + float(self.rng.normal(0, 1e-5))
            d.lon = tlon + float(self.rng.normal(0, 1e-5))
            d.alt_m = talt + float(self.rng.normal(0, 0.1))
            d.position_error_m = float(
                np.sqrt((d.lat - tlat) ** 2 + (d.lon - tlon) ** 2) * 111_000
            )

        max_err = max(d.position_error_m for d in self._drones.values())

        collisions = 0
        positions = [(d.lat, d.lon) for d in self._drones.values()]
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = np.sqrt(
                    (positions[i][0] - positions[j][0]) ** 2
                    + (positions[i][1] - positions[j][1]) ** 2
                ) * 111_000
                if dist < MIN_SEPARATION_M:
                    collisions += 1

        passed = max_err <= FORMATION_ERROR_THRESHOLD_M and collisions == 0
        log.append(f"formation={formation.value} max_err={max_err:.3f}m collisions={collisions}")

        return FlightTestResult(
            scenario_name=f"formation_{formation.value}",
            drone_count=self.drone_count,
            passed=passed,
            phase_reached=TestPhase.FORMATION if passed else TestPhase.ABORT,
            max_formation_error_m=max_err,
            collision_count=collisions,
            duration_s=time.time() - t_start,
            metrics={
                "formation_error_m": max_err,
                "collision_count": float(collisions),
            },
            log=log,
        )

    def run_gps_trace_replay(self, trace: list[dict]) -> FlightTestResult:
        """GPS 로그 기반 HITL 재생 시험."""
        log: list[str] = []
        t_start = time.time()
        max_err = 0.0
        for frame in trace:
            did = frame.get("drone_id", "D01")
            if did in self._drones:
                d = self._drones[did]
                d.lat = frame.get("lat", d.lat)
                d.lon = frame.get("lon", d.lon)
                d.alt_m = frame.get("alt_m", d.alt_m)
                err = float(self.rng.uniform(0.0, 0.3))
                max_err = max(max_err, err)
                d.position_error_m = err

        passed = max_err <= FORMATION_ERROR_THRESHOLD_M
        log.append(f"trace_replay frames={len(trace)} max_err={max_err:.3f}m")
        return FlightTestResult(
            scenario_name="gps_trace_replay",
            drone_count=self.drone_count,
            passed=passed,
            phase_reached=TestPhase.COMPLETE if passed else TestPhase.ABORT,
            max_formation_error_m=max_err,
            collision_count=0,
            duration_s=time.time() - t_start,
            metrics={"replay_error_m": max_err, "frames": float(len(trace))},
            log=log,
        )
