"""P698: 3-5기 포메이션·GPS 재생 비행 시험 프레임워크.

실기 비행이 필요한 항목은 @pytest.mark.hardware 로 마킹.
시뮬레이션 가능한 GPS 재생·포메이션 검증은 소프트웨어로 처리.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class FormationType(Enum):
    LINE = "line"           # 일렬 종대
    V_SHAPE = "v_shape"     # V 포메이션
    DIAMOND = "diamond"     # 마름모
    CIRCLE = "circle"       # 원형
    GRID = "grid"           # 격자


@dataclass
class GPSPoint:
    """WGS-84 GPS 좌표."""
    lat: float          # 위도 (deg)
    lon: float          # 경도 (deg)
    alt_msl: float      # MSL 고도 (m)
    timestamp_sec: float = 0.0

    def distance_to(self, other: "GPSPoint") -> float:
        """평면 근사 거리 (m) — 소규모 비행 시험 전용."""
        R = 6_371_000.0
        dlat = np.radians(other.lat - self.lat)
        dlon = np.radians(other.lon - self.lon)
        lat_m = R * dlat
        lon_m = R * dlon * np.cos(np.radians(self.lat))
        return float(np.sqrt(lat_m**2 + lon_m**2))


@dataclass
class FormationSlot:
    """포메이션 내 드론 슬롯."""
    slot_id: int
    drone_id: str
    offset_x: float     # 리더 대비 X 오프셋 (m, 동쪽)
    offset_y: float     # 리더 대비 Y 오프셋 (m, 북쪽)
    offset_z: float     # 리더 대비 Z 오프셋 (m, 위)


def generate_formation(ftype: FormationType, n_drones: int,
                       spacing_m: float = 5.0) -> list[tuple[float, float, float]]:
    """포메이션 오프셋 생성 (리더 기준, m)."""
    if ftype == FormationType.LINE:
        return [(0.0, -i * spacing_m, 0.0) for i in range(n_drones)]
    if ftype == FormationType.V_SHAPE:
        offsets = [(0.0, 0.0, 0.0)]
        for i in range(1, n_drones):
            side = 1 if i % 2 == 1 else -1
            row = (i + 1) // 2
            offsets.append((side * row * spacing_m, -row * spacing_m, 0.0))
        return offsets[:n_drones]
    if ftype == FormationType.CIRCLE:
        angles = np.linspace(0, 2 * np.pi, n_drones, endpoint=False)
        return [(float(spacing_m * np.sin(a)), float(spacing_m * np.cos(a)), 0.0) for a in angles]
    if ftype == FormationType.DIAMOND:
        base = [(0, spacing_m, 0), (-spacing_m, 0, 0), (spacing_m, 0, 0), (0, -spacing_m, 0)]
        return [(float(x), float(y), float(z)) for x, y, z in (base * n_drones)[:n_drones]]
    # GRID default
    cols = int(np.ceil(np.sqrt(n_drones)))
    return [(float((i % cols) * spacing_m), float((i // cols) * spacing_m), 0.0)
            for i in range(n_drones)]


@dataclass
class GPSLog:
    """GPS 재생용 드론 비행 로그."""
    drone_id: str
    waypoints: list[GPSPoint] = field(default_factory=list)

    def add(self, lat: float, lon: float, alt: float, t: float) -> None:
        self.waypoints.append(GPSPoint(lat, lon, alt, t))

    def duration_sec(self) -> float:
        if len(self.waypoints) < 2:
            return 0.0
        return self.waypoints[-1].timestamp_sec - self.waypoints[0].timestamp_sec

    def max_separation_m(self) -> float:
        """연속 웨이포인트 최대 이격 거리."""
        if len(self.waypoints) < 2:
            return 0.0
        return max(self.waypoints[i].distance_to(self.waypoints[i + 1])
                   for i in range(len(self.waypoints) - 1))


@dataclass
class FlightTestConfig:
    n_drones: int = 3
    formation: FormationType = FormationType.LINE
    spacing_m: float = 5.0
    takeoff_alt_m: float = 10.0
    test_duration_sec: float = 60.0
    max_wind_ms: float = 8.0
    min_separation_m: float = 3.0   # 최소 이격 거리 (안전 기준)


@dataclass
class FlightTestResult:
    config: FlightTestConfig
    separation_violations: int = 0
    gps_dropouts: int = 0
    formation_error_m: float = 0.0  # 평균 포메이션 오차
    passed: bool = True
    notes: str = ""


class OutdoorFlightTestRunner:
    """포메이션 비행 시험 러너 (소프트웨어 검증 부분).

    실기 비행 테스트 (pytest.mark.hardware) 없이
    GPS 로그 재생·포메이션 오류 측정·이격 거리 검증을 수행.
    """

    def __init__(self, rng: np.random.Generator | None = None) -> None:
        self._rng = rng if rng is not None else np.random.default_rng(0)

    def replay_gps_logs(self, logs: list[GPSLog], config: FlightTestConfig) -> FlightTestResult:
        """GPS 로그 재생 및 포메이션 검증."""
        result = FlightTestResult(config=config)

        if len(logs) < 2:
            result.notes = "드론 수 부족 (최소 2기)"
            result.passed = False
            return result

        # 포메이션 오류: 드론 간 실제 거리 vs 설계 이격 거리
        offsets = generate_formation(config.formation, len(logs), config.spacing_m)
        max_time_steps = min(len(log.waypoints) for log in logs)
        errors = []
        for t in range(max_time_steps):
            for i in range(len(logs)):
                for j in range(i + 1, len(logs)):
                    pi = logs[i].waypoints[t]
                    pj = logs[j].waypoints[t]
                    actual_sep = pi.distance_to(pj)
                    if actual_sep < config.min_separation_m:
                        result.separation_violations += 1
                    dx = offsets[j][0] - offsets[i][0]
                    dy = offsets[j][1] - offsets[i][1]
                    design_sep = float(np.sqrt(dx**2 + dy**2))
                    errors.append(abs(actual_sep - design_sep))

        result.formation_error_m = float(np.mean(errors)) if errors else 0.0
        result.passed = result.separation_violations == 0

        return result

    def generate_synthetic_logs(self, config: FlightTestConfig,
                                base_lat: float = 34.9, base_lon: float = 126.9) -> list[GPSLog]:
        """시뮬레이션용 합성 GPS 로그 생성."""
        offsets = generate_formation(config.formation, config.n_drones, config.spacing_m)
        logs = []
        steps = int(config.test_duration_sec)

        for i, (ox, oy, _) in enumerate(offsets):
            log = GPSLog(drone_id=f"drone_{i}")
            for t in range(steps):
                # 북쪽으로 천천히 이동 + 가우시안 노이즈
                noise_x = float(self._rng.normal(0, 0.2))
                noise_y = float(self._rng.normal(0, 0.2))
                lat = base_lat + (oy + noise_y + t * 0.5) / 111_000
                lon = base_lon + (ox + noise_x) / (111_000 * np.cos(np.radians(base_lat)))
                log.add(lat, lon, config.takeoff_alt_m, float(t))
            logs.append(log)

        return logs
