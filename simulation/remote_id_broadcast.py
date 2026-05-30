"""ASTM F3411-22a Remote ID 네트워크 브로드캐스트 계층.

기존 remote_id.py 위에 네트워크 브로드캐스트 모드를 추가한다.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RemoteIDBroadcaster:
    """드론 Remote ID를 네트워크 브로드캐스트 모드로 송출한다."""

    operator_id: str = "UNKNOWN_OPERATOR"

    def __post_init__(self) -> None:
        self._seq: dict[str, int] = {}

    def broadcast(
        self,
        drone_id: str,
        lat: float,
        lon: float,
        alt: float,
        timestamp: float,
    ) -> dict[str, Any]:
        """ASTM F3411-22a 호환 브로드캐스트 패킷을 생성·반환한다.

        Args:
            drone_id: 드론 식별자 (UAS ID).
            lat: 위도 (decimal degrees, -90~90).
            lon: 경도 (decimal degrees, -180~180).
            alt: 고도 (m, WGS-84).
            timestamp: UNIX 타임스탬프 (초).

        Returns:
            브로드캐스트 패킷 딕셔너리.
        """
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"위도 범위 초과: {lat}")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"경도 범위 초과: {lon}")

        seq = self._seq.get(drone_id, 0)
        self._seq[drone_id] = seq + 1

        return {
            "id": drone_id,
            "lat": round(lat, 7),
            "lon": round(lon, 7),
            "alt": round(alt, 2),
            "ts": timestamp,
            "seq": seq,
            "mode": "broadcast",
            "operator_id": self.operator_id,
        }


class NetworkRemoteIDReceiver:
    """수신된 Remote ID 패킷을 저장하고 조회한다."""

    def __init__(self, max_age_s: float = 30.0) -> None:
        """
        Args:
            max_age_s: 이 시간(초) 이상 오래된 항목은 get_seen_ids()에서 제외.
        """
        self.max_age_s = max_age_s
        # drone_id → 가장 최근 패킷
        self._seen: dict[str, dict[str, Any]] = {}

    def receive(self, packet: dict[str, Any]) -> None:
        """패킷을 수신하여 내부 목록에 기록한다.

        Args:
            packet: RemoteIDBroadcaster.broadcast()가 반환한 패킷.
        """
        required = {"id", "lat", "lon", "alt", "ts", "seq", "mode"}
        missing = required - packet.keys()
        if missing:
            raise ValueError(f"패킷에 필드 누락: {missing}")

        drone_id: str = packet["id"]
        existing = self._seen.get(drone_id)
        if existing is None or packet["seq"] >= existing["seq"]:
            self._seen[drone_id] = packet

    def get_seen_ids(self, reference_time: float | None = None) -> list[str]:
        """최근 max_age_s 이내에 수신된 드론 ID 목록을 반환한다.

        Args:
            reference_time: 기준 시각 (None이면 현재 시각 사용).

        Returns:
            활성 드론 ID 목록.
        """
        now = reference_time if reference_time is not None else time.time()
        return [
            did
            for did, pkt in self._seen.items()
            if (now - pkt["ts"]) <= self.max_age_s
        ]

    def get_last_packet(self, drone_id: str) -> dict[str, Any] | None:
        """특정 드론의 마지막 수신 패킷 반환."""
        return self._seen.get(drone_id)

    def clear(self) -> None:
        """수신 이력 초기화."""
        self._seen.clear()
