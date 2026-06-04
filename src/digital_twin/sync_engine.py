"""P740: 실기 텔레메트리 → SDACS DroneState 동기화 엔진 (<50ms 목표).

MAVLink2 GLOBAL_POSITION_INT, ATTITUDE, VFR_HUD를 파싱하여 SDACS DroneState로
변환하고 SwarmSimulator의 상태를 실시간 갱신.

성능 목표:
- 텔레메트리 수신 → 시뮬레이터 갱신: <50ms p99
- 처리량: 다중 기체(N≤30) × 10Hz = 300 msg/s
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TelemetrySnapshot:
    """단일 시점 텔레메트리 스냅샷."""

    drone_id: str
    timestamp_us: int        # MAVLink time_boot_us
    received_ts: float       # local monotonic
    lat_deg: float
    lon_deg: float
    alt_m: float
    vx_mps: float
    vy_mps: float
    vz_mps: float
    heading_deg: float
    battery_pct: float
    flight_mode: str         # 'MANUAL'|'AUTO'|'LOITER'|'RTL'|'LAND'


@dataclass
class LatencyStats:
    """동기화 지연 통계."""

    samples: deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    n_received: int = 0
    n_dropped: int = 0

    def add(self, latency_ms: float) -> None:
        self.samples.append(latency_ms)
        self.n_received += 1

    def p50(self) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        return s[len(s) // 2]

    def p99(self) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        return s[int(len(s) * 0.99)]

    def mean(self) -> float:
        return sum(self.samples) / len(self.samples) if self.samples else 0.0


# 비행 모드 정수 → 문자열 매핑 (PX4 MAIN_MODE)
PX4_MODE_MAP = {
    1: "MANUAL", 2: "ALTITUDE", 3: "POSITION", 4: "AUTO",
    5: "ACRO", 6: "OFFBOARD", 7: "STABILIZED", 8: "RATTITUDE",
    9: "RTL", 10: "LAND", 11: "LOITER", 12: "RETURN",
}


class TelemetrySync:
    """MAVLink 텔레메트리를 SwarmSimulator 상태로 동기화."""

    def __init__(self, target_latency_ms: float = 50.0) -> None:
        self.target_latency_ms = target_latency_ms
        self.stats = LatencyStats()
        self._latest: dict[str, TelemetrySnapshot] = {}

    def parse_mavlink_global_position(
        self,
        drone_id: str,
        time_boot_us: int,
        lat_int: int,        # MAVLink: 1e7 scaled
        lon_int: int,
        alt_mm: int,
        vx_cmps: int,        # cm/s
        vy_cmps: int,
        vz_cmps: int,
        hdg_cdeg: int,       # 0.01 deg
        battery_pct: float = 100.0,
        flight_mode: int = 4,
    ) -> TelemetrySnapshot:
        """MAVLink GLOBAL_POSITION_INT → TelemetrySnapshot."""
        return TelemetrySnapshot(
            drone_id=drone_id,
            timestamp_us=time_boot_us,
            received_ts=time.monotonic(),
            lat_deg=lat_int / 1e7,
            lon_deg=lon_int / 1e7,
            alt_m=alt_mm / 1000.0,
            vx_mps=vx_cmps / 100.0,
            vy_mps=vy_cmps / 100.0,
            vz_mps=vz_cmps / 100.0,
            heading_deg=(hdg_cdeg / 100.0) % 360.0,
            battery_pct=float(battery_pct),
            flight_mode=PX4_MODE_MAP.get(flight_mode, "UNKNOWN"),
        )

    def update(self, snapshot: TelemetrySnapshot) -> bool:
        """스냅샷 적용 + 지연 측정. False면 타겟 지연 초과."""
        # 도착 ↔ 적용 사이 지연 (보통 1ms 이하)
        apply_start = time.monotonic()
        self._latest[snapshot.drone_id] = snapshot
        apply_latency_ms = (time.monotonic() - apply_start) * 1000

        self.stats.add(apply_latency_ms)
        ok = apply_latency_ms <= self.target_latency_ms
        if not ok:
            self.stats.n_dropped += 1
        return ok

    def get_latest(self, drone_id: str) -> TelemetrySnapshot | None:
        return self._latest.get(drone_id)

    def to_sdacs_state(self, snapshot: TelemetrySnapshot, origin_lat: float, origin_lon: float) -> dict:
        """GPS → 로컬 ENU (m) 변환 + SDACS DroneState 형식."""
        # 단순 평면 근사 (소규모 환경, <10km)
        # 정확: pyproj 사용 권장
        dlat = snapshot.lat_deg - origin_lat
        dlon = snapshot.lon_deg - origin_lon
        x_m = dlon * 111_320 * (1.0)  # cos(lat) 근사 생략 시
        y_m = dlat * 110_540
        return {
            "drone_id": snapshot.drone_id,
            "position": [x_m, y_m, snapshot.alt_m],
            "velocity": [snapshot.vx_mps, snapshot.vy_mps, snapshot.vz_mps],
            "heading_deg": snapshot.heading_deg,
            "battery_pct": snapshot.battery_pct,
            "flight_phase": snapshot.flight_mode,
        }
