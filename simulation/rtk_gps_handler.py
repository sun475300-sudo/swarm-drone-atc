"""P694: RTK-GPS RTCM3 파서 + AirspaceController 위치 피드백."""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FixType(Enum):
    NO_FIX = 0
    GPS = 1
    DGPS = 2
    RTK_FLOAT = 4
    RTK_FIXED = 5


# RTCM3 메시지 타입 (RTK 관련)
RTCM3_MSG_1004 = 1004   # Extended GPS RTK
RTCM3_MSG_1012 = 1012   # Extended GLONASS RTK
RTCM3_MSG_1074 = 1074   # GPS MSM4
RTCM3_MSG_1084 = 1084   # GLONASS MSM4
RTCM3_PREAMBLE = 0xD3
RTCM3_CRC_POLY = 0x864CFB


def _crc24q(data: bytes) -> int:
    """CRC-24Q (RTCM3 표준 CRC)."""
    crc = 0
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= RTCM3_CRC_POLY
    return crc & 0xFFFFFF


@dataclass
class RTCMFrame:
    msg_type: int
    payload: bytes
    crc_valid: bool

    @classmethod
    def parse(cls, raw: bytes) -> "RTCMFrame | None":
        """RTCM3 프레임 파싱. 파싱 실패 시 None 반환."""
        if len(raw) < 6 or raw[0] != RTCM3_PREAMBLE:
            return None
        length = ((raw[1] & 0x03) << 8) | raw[2]
        if len(raw) < length + 6:
            return None
        msg_type = (raw[3] << 4) | (raw[4] >> 4)
        payload = raw[3: 3 + length]
        crc_bytes = raw[3 + length: 3 + length + 3]
        # RTCM3: CRC 범위는 헤더(3바이트) + 메시지 본문 전체
        expected_crc = _crc24q(raw[0: 3 + length])
        actual_crc = (crc_bytes[0] << 16) | (crc_bytes[1] << 8) | crc_bytes[2]
        return cls(msg_type=msg_type, payload=payload, crc_valid=(expected_crc == actual_crc))


@dataclass
class RTKPosition:
    """센티미터급 RTK 위치 (ECEF 기반)."""
    lat: float          # 위도 (deg)
    lon: float          # 경도 (deg)
    alt: float          # 고도 MSL (m)
    fix_type: FixType
    h_accuracy: float   # 수평 정확도 (m, RTK_FIXED ≈ 0.02)
    v_accuracy: float   # 수직 정확도 (m)
    timestamp: float = field(default_factory=time.monotonic)

    @property
    def is_rtk_fixed(self) -> bool:
        return self.fix_type == FixType.RTK_FIXED


@dataclass
class RTKStats:
    total_frames: int = 0
    valid_frames: int = 0
    crc_errors: int = 0
    rtk_fixed_count: int = 0

    @property
    def valid_rate(self) -> float:
        return self.valid_frames / self.total_frames if self.total_frames > 0 else 0.0


class RTKGPSHandler:
    """RTK-GPS RTCM3 파서 및 AirspaceController 피드백 인터페이스.

    실기 하드웨어(here3, u-blox F9P 등)에서 수신한 RTCM3 스트림을 파싱,
    센티미터급 위치를 AirspaceController에 공급.
    """

    def __init__(self, drone_id: str, correction_source: str = "NTRIP"):
        self.drone_id = drone_id
        self.correction_source = correction_source
        self._position: RTKPosition | None = None
        self._stats = RTKStats()
        self._callbacks: list[Any] = []

    @property
    def position(self) -> RTKPosition | None:
        return self._position

    @property
    def stats(self) -> RTKStats:
        return self._stats

    def register_position_callback(self, fn: Any) -> None:
        """위치 갱신 콜백 등록 (AirspaceController 등)."""
        self._callbacks.append(fn)

    def ingest_rtcm(self, raw: bytes) -> RTCMFrame | None:
        """RTCM3 원시 바이트 수신 처리."""
        self._stats.total_frames += 1
        frame = RTCMFrame.parse(raw)
        if frame is None or not frame.crc_valid:
            self._stats.crc_errors += 1
            return None
        self._stats.valid_frames += 1
        return frame

    def update_position(self, pos: RTKPosition) -> None:
        """파서가 새 위치를 확보했을 때 콜백 체인 실행."""
        self._position = pos
        if pos.fix_type == FixType.RTK_FIXED:
            self._stats.rtk_fixed_count += 1
        for cb in self._callbacks:
            cb(self.drone_id, pos)

    def build_fake_rtcm_frame(self, msg_type: int = RTCM3_MSG_1074) -> bytes:
        """테스트용 최소 유효 RTCM3 프레임 생성 (parse()와 동일 CRC 범위 사용)."""
        payload = bytes([
            (msg_type >> 4) & 0xFF,
            ((msg_type & 0x0F) << 4),
        ])
        length = len(payload)
        header = bytes([RTCM3_PREAMBLE, (length >> 8) & 0x03, length & 0xFF])
        # CRC: 헤더 + 본문 (parse()와 동일)
        crc_val = _crc24q(header + payload)
        crc_bytes = bytes([(crc_val >> 16) & 0xFF, (crc_val >> 8) & 0xFF, crc_val & 0xFF])
        return header + payload + crc_bytes
