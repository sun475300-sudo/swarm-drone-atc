"""P693: ASTM F3411-22a Remote ID 네트워크 방송 계층.

기존 simulation/remote_id.py (Phase 683)의 데이터 모델을 재사용,
이 모듈은 Broadcast/Network 모드 전송 시뮬레이션을 추가.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# 기존 Remote ID 데이터 모델 재사용
from simulation.remote_id import (
    IDType,
    OperationalStatus,
    RemoteIDMessage,
    UAType,
)


class BroadcastMode(Enum):
    BROADCAST = "Broadcast"             # BT5 / Wi-Fi Beacon (로컬 수신)
    NETWORK = "Network"                 # USS(UAS Service Supplier) 업링크
    HYBRID = "Hybrid"                   # 양쪽 동시 방송


class TransmitResult(Enum):
    SUCCESS = "success"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    INVALID_PAYLOAD = "invalid_payload"


# F3411: 최소 1Hz, 권장 1-5Hz
MIN_BROADCAST_HZ = 1.0
MAX_BROADCAST_HZ = 5.0


@dataclass
class BroadcastFrame:
    """F3411-22a 방송 프레임 (시뮬레이션 표현)."""
    drone_id: str
    mode: BroadcastMode
    msg: RemoteIDMessage
    timestamp: float = field(default_factory=time.monotonic)
    seq: int = 0


@dataclass
class BroadcastStats:
    total_sent: int = 0
    network_errors: int = 0
    rate_limited: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_sent == 0:
            return 0.0
        return (self.total_sent - self.network_errors - self.rate_limited) / self.total_sent


class RemoteIDBroadcaster:
    """드론별 Remote ID 방송기.

    실기 환경: BT5/Wi-Fi Beacon + USS REST API 전송.
    시뮬레이션: 콜백 기반 메시지 전달.
    """

    def __init__(self, drone_id: str, mode: BroadcastMode = BroadcastMode.BROADCAST,
                 rate_hz: float = 1.0) -> None:
        if not MIN_BROADCAST_HZ <= rate_hz <= MAX_BROADCAST_HZ:
            raise ValueError(f"방송 주기 {rate_hz}Hz 범위 초과 ({MIN_BROADCAST_HZ}~{MAX_BROADCAST_HZ})")
        self.drone_id = drone_id
        self.mode = mode
        self.rate_hz = rate_hz
        self._seq = 0
        self._stats = BroadcastStats()
        self._subscribers: list[Any] = []

    @property
    def stats(self) -> BroadcastStats:
        return self._stats

    def subscribe(self, fn: Any) -> None:
        """방송 수신 구독 (USS, 수신기 시뮬레이션 등)."""
        self._subscribers.append(fn)

    def broadcast(self, msg: RemoteIDMessage) -> TransmitResult:
        """Remote ID 메시지 방송."""
        frame = BroadcastFrame(
            drone_id=self.drone_id,
            mode=self.mode,
            msg=msg,
            seq=self._seq,
        )
        self._seq += 1
        self._stats.total_sent += 1

        for sub in self._subscribers:
            sub(frame)

        return TransmitResult.SUCCESS

    def build_message(self, lat: float, lon: float, alt_m: float,
                      speed_ms: float, heading_deg: float,
                      status: OperationalStatus = OperationalStatus.AIRBORNE) -> RemoteIDMessage:
        """표준 Remote ID 메시지 생성."""
        return RemoteIDMessage(
            uas_id=self.drone_id,
            id_type=IDType.REGISTRATION_ID,
            ua_type=UAType.MULTIROTOR,
            operational_status=status,
            latitude=lat,
            longitude=lon,
            geodetic_altitude=alt_m,
            speed=speed_ms,
            track_direction=heading_deg,
        )


class FleetRemoteIDManager:
    """군집 전체 Remote ID 방송 관리."""

    def __init__(self) -> None:
        self._broadcasters: dict[str, RemoteIDBroadcaster] = {}

    def register(self, drone_id: str, mode: BroadcastMode = BroadcastMode.BROADCAST,
                 rate_hz: float = 1.0) -> RemoteIDBroadcaster:
        bc = RemoteIDBroadcaster(drone_id, mode, rate_hz)
        self._broadcasters[drone_id] = bc
        return bc

    def get(self, drone_id: str) -> RemoteIDBroadcaster | None:
        return self._broadcasters.get(drone_id)

    def fleet_stats(self) -> dict[str, Any]:
        return {
            did: {
                "mode": bc.mode.value,
                "rate_hz": bc.rate_hz,
                "total_sent": bc.stats.total_sent,
                "success_rate": round(bc.stats.success_rate, 4),
            }
            for did, bc in self._broadcasters.items()
        }

    def active_count(self) -> int:
        return len(self._broadcasters)
