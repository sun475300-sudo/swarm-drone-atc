"""Phase 694: RTK-GPS 센티미터 정밀도 측위 및 AirspaceController 피드백."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class RTKFixType(Enum):
    """RTK 측위 상태."""
    NO_FIX = 0
    SINGLE = 1
    DGPS = 2
    FLOAT = 4
    FIX = 5


@dataclass
class RTKPosition:
    """RTK 측위 결과."""
    drone_id: str
    lat: float
    lon: float
    alt_m: float
    fix_type: RTKFixType
    hdop: float
    vdop: float
    accuracy_h_m: float
    accuracy_v_m: float
    satellites: int
    timestamp: float = field(default_factory=time.time)

    @property
    def is_centimeter(self) -> bool:
        return self.fix_type == RTKFixType.FIX and self.accuracy_h_m <= 0.05

    @property
    def is_usable(self) -> bool:
        return self.fix_type in (RTKFixType.FLOAT, RTKFixType.FIX, RTKFixType.DGPS)


@dataclass
class RTCMStats:
    """RTCM 보정 스트림 통계."""
    messages_received: int = 0
    correction_age_s: float = 0.0
    base_lat: float = 0.0
    base_lon: float = 0.0
    baseline_m: float = 0.0


ACCURACY_BY_FIX: dict[RTKFixType, tuple[float, float]] = {
    RTKFixType.NO_FIX: (999.0, 999.0),
    RTKFixType.SINGLE: (2.5, 4.0),
    RTKFixType.DGPS: (1.0, 1.5),
    RTKFixType.FLOAT: (0.3, 0.5),
    RTKFixType.FIX: (0.02, 0.03),
}

FIX_TRANSITION_PROB: dict[RTKFixType, RTKFixType] = {
    RTKFixType.NO_FIX: RTKFixType.SINGLE,
    RTKFixType.SINGLE: RTKFixType.DGPS,
    RTKFixType.DGPS: RTKFixType.FLOAT,
    RTKFixType.FLOAT: RTKFixType.FIX,
    RTKFixType.FIX: RTKFixType.FIX,
}


class RTKGPSHandler:
    """RTK-GPS 측위 핸들러 (RTCM3 보정 스트림 파서 포함)."""

    WARMUP_STEPS = 5

    def __init__(
        self,
        base_lat: float = 35.1,
        base_lon: float = 126.9,
        seed: int = 42,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.rtcm = RTCMStats(base_lat=base_lat, base_lon=base_lon)
        self._fix_states: dict[str, RTKFixType] = {}
        self._step_counts: dict[str, int] = {}
        self._positions: dict[str, tuple[float, float, float]] = {}

    def register_drone(
        self,
        drone_id: str,
        init_lat: float,
        init_lon: float,
        init_alt: float,
    ) -> None:
        self._positions[drone_id] = (init_lat, init_lon, init_alt)
        self._fix_states[drone_id] = RTKFixType.NO_FIX
        self._step_counts[drone_id] = 0

    def ingest_rtcm(self, correction_data: bytes) -> bool:
        """RTCM3 보정 스트림 수신 처리 (시뮬: 길이만 검증)."""
        if len(correction_data) < 3:
            return False
        self.rtcm.messages_received += 1
        self.rtcm.correction_age_s = 0.0
        return True

    def _advance_fix(self, drone_id: str) -> RTKFixType:
        """워밍업 후 FIX 상태로 수렴."""
        count = self._step_counts.get(drone_id, 0)
        current = self._fix_states.get(drone_id, RTKFixType.NO_FIX)
        if count >= self.WARMUP_STEPS and current != RTKFixType.FIX:
            next_fix = FIX_TRANSITION_PROB.get(current, RTKFixType.SINGLE)
            self._fix_states[drone_id] = next_fix
        self._step_counts[drone_id] = count + 1
        return self._fix_states[drone_id]

    def get_position(self, drone_id: str) -> RTKPosition:
        """현재 RTK 측위 결과 반환."""
        if drone_id not in self._positions:
            init_lat = 35.1 + float(self.rng.uniform(-0.01, 0.01))
            init_lon = 126.9 + float(self.rng.uniform(-0.01, 0.01))
            self.register_drone(drone_id, init_lat, init_lon, 50.0)

        fix = self._advance_fix(drone_id)
        acc_h, acc_v = ACCURACY_BY_FIX[fix]
        lat, lon, alt = self._positions[drone_id]

        noise_scale = acc_h * 1e-5
        lat += float(self.rng.normal(0, noise_scale))
        lon += float(self.rng.normal(0, noise_scale))
        alt += float(self.rng.normal(0, acc_v))
        self._positions[drone_id] = (lat, lon, alt)

        dist_to_base = np.sqrt(
            (lat - self.rtcm.base_lat) ** 2 + (lon - self.rtcm.base_lon) ** 2
        ) * 111_000
        self.rtcm.baseline_m = float(dist_to_base)

        return RTKPosition(
            drone_id=drone_id,
            lat=lat, lon=lon, alt_m=alt,
            fix_type=fix,
            hdop=float(self.rng.uniform(0.8, 1.5)),
            vdop=float(self.rng.uniform(1.0, 2.0)),
            accuracy_h_m=acc_h,
            accuracy_v_m=acc_v,
            satellites=int(self.rng.integers(8, 16)),
        )

    def to_airspace_feedback(self, drone_id: str) -> dict:
        """AirspaceController가 소비하는 피드백 형식으로 변환."""
        pos = self.get_position(drone_id)
        return {
            "drone_id": pos.drone_id,
            "position": [pos.lat, pos.lon, pos.alt_m],
            "fix_type": pos.fix_type.value,
            "accuracy_h_m": pos.accuracy_h_m,
            "usable": pos.is_usable,
            "centimeter": pos.is_centimeter,
            "timestamp": pos.timestamp,
        }

    def fleet_feedback(self, drone_ids: list[str]) -> list[dict]:
        return [self.to_airspace_feedback(d) for d in drone_ids]
