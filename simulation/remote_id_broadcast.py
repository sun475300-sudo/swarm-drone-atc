"""Phase 693: ASTM F3411-22a 실기 Remote ID 방송 (Broadcast / Network 모드)."""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class BroadcastMode(Enum):
    """Remote ID 방송 모드."""
    BLUETOOTH = "bluetooth_5_0"
    WIFI_NAN = "wifi_nan"
    NETWORK = "network_remote_id"


class MessageType(Enum):
    """F3411 메시지 타입."""
    BASIC_ID = 0x00
    LOCATION = 0x10
    AUTH = 0x20
    SELF_ID = 0x30
    SYSTEM = 0x40
    OPERATOR_ID = 0x50


@dataclass
class BroadcastPacket:
    """직렬화된 방송 패킷."""
    msg_type: MessageType
    drone_id: str
    payload_bytes: bytes
    mode: BroadcastMode
    timestamp: float = field(default_factory=time.time)

    @property
    def packet_size(self) -> int:
        return len(self.payload_bytes) + 4


@dataclass
class BroadcastStats:
    """방송 통계."""
    total_broadcasts: int = 0
    bluetooth_count: int = 0
    network_count: int = 0
    operator_msgs: int = 0
    last_broadcast: float = 0.0


BROADCAST_INTERVAL_S = 1.0
MAX_PACKET_SIZE = 25
SPEED_MULTIPLIER = 0.25


def _encode_basic_id(uas_id: str, ua_type: int = 2) -> bytes:
    """BasicID 메시지 직렬화 (F3411-22a §7.4.1)."""
    id_bytes = uas_id.encode("ascii")[:20].ljust(20, b"\x00")
    return struct.pack("!BB", ua_type, 1) + id_bytes + b"\x00\x04"


def _encode_location(
    lat: float, lon: float, alt_m: float,
    speed_ms: float, track_deg: float, vspeed_ms: float,
) -> bytes:
    """Location/Vector 메시지 직렬화 (F3411-22a §7.4.2)."""
    lat_i = int(lat * 1e7)
    lon_i = int(lon * 1e7)
    alt_i = int((alt_m + 1000.0) * 5)
    speed_i = int(min(speed_ms / SPEED_MULTIPLIER, 254))
    track_i = int(track_deg * 2) & 0xFFFF
    vs_i = int(vspeed_ms * 10) & 0xFF
    return struct.pack("!iiHHHBB", lat_i, lon_i, alt_i, track_i, speed_i, vs_i, 0)


def _encode_system(
    op_lat: float, op_lon: float, area_count: int = 1,
) -> bytes:
    """System 메시지 직렬화 (F3411-22a §7.4.5)."""
    op_lat_i = int(op_lat * 1e7)
    op_lon_i = int(op_lon * 1e7)
    return struct.pack("!iiHBB", op_lat_i, op_lon_i, 0, area_count, 0)


class RemoteIDBroadcaster:
    """ASTM F3411-22a 방송/네트워크 Remote ID 브로드캐스터."""

    def __init__(
        self,
        modes: list[BroadcastMode] | None = None,
        interval_s: float = BROADCAST_INTERVAL_S,
        seed: int = 42,
    ) -> None:
        self.modes = modes or [BroadcastMode.BLUETOOTH, BroadcastMode.NETWORK]
        self.interval_s = interval_s
        self.rng = np.random.default_rng(seed)
        self.stats = BroadcastStats()
        self._last_broadcast: dict[str, float] = {}
        self._packet_log: list[BroadcastPacket] = []

    def is_due(self, drone_id: str) -> bool:
        """방송 시간이 됐는지 확인."""
        last = self._last_broadcast.get(drone_id, 0.0)
        return (time.time() - last) >= self.interval_s

    def broadcast(
        self,
        drone_id: str,
        lat: float,
        lon: float,
        alt_m: float,
        speed_ms: float = 0.0,
        track_deg: float = 0.0,
        vspeed_ms: float = 0.0,
        operator_lat: float = 35.0,
        operator_lon: float = 126.0,
        force: bool = False,
    ) -> list[BroadcastPacket]:
        """위치 정보를 담은 패킷 세트 방송."""
        if not force and not self.is_due(drone_id):
            return []

        packets: list[BroadcastPacket] = []
        for mode in self.modes:
            for msg_type, payload in [
                (MessageType.BASIC_ID, _encode_basic_id(drone_id)),
                (MessageType.LOCATION, _encode_location(lat, lon, alt_m, speed_ms, track_deg, vspeed_ms)),
                (MessageType.SYSTEM, _encode_system(operator_lat, operator_lon)),
            ]:
                pkt = BroadcastPacket(
                    msg_type=msg_type,
                    drone_id=drone_id,
                    payload_bytes=payload,
                    mode=mode,
                )
                packets.append(pkt)
                self._packet_log.append(pkt)
                if mode == BroadcastMode.BLUETOOTH:
                    self.stats.bluetooth_count += 1
                elif mode == BroadcastMode.NETWORK:
                    self.stats.network_count += 1

        self.stats.total_broadcasts += 1
        self.stats.last_broadcast = time.time()
        self._last_broadcast[drone_id] = self.stats.last_broadcast
        return packets

    def broadcast_fleet(
        self,
        fleet: dict[str, dict],
    ) -> dict[str, list[BroadcastPacket]]:
        """다수 드론 일괄 방송."""
        result: dict[str, list[BroadcastPacket]] = {}
        for drone_id, state in fleet.items():
            pkts = self.broadcast(
                drone_id=drone_id,
                lat=state.get("lat", 0.0),
                lon=state.get("lon", 0.0),
                alt_m=state.get("alt_m", 0.0),
                speed_ms=state.get("speed_ms", 0.0),
                track_deg=state.get("track_deg", 0.0),
                vspeed_ms=state.get("vspeed_ms", 0.0),
                force=state.get("force", False),
            )
            if pkts:
                result[drone_id] = pkts
        return result

    def get_compliance_status(self, drone_id: str) -> dict:
        """F3411 준수 상태 반환."""
        last = self._last_broadcast.get(drone_id, 0.0)
        age_s = time.time() - last if last else float("inf")
        return {
            "drone_id": drone_id,
            "compliant": age_s <= 3.0,
            "last_broadcast_age_s": age_s,
            "total_broadcasts": self.stats.total_broadcasts,
        }
