"""Phase 683: ASTM F3411 Remote ID 지원 시뮬레이션."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class UAType(Enum):
    HELICOPTER = 0
    AIRPLANE = 1
    MULTIROTOR = 2
    VTOL = 3
    OTHER = 15


class IDType(Enum):
    SERIAL_NUMBER = 1
    REGISTRATION_ID = 2
    UTM_ASSIGNED = 3
    SPECIFIC_SESSION = 4


class OperationalStatus(Enum):
    UNDECLARED = 0
    GROUND = 1
    AIRBORNE = 2
    EMERGENCY = 3
    REMOTE_ID_FAILURE = 4


@dataclass
class RemoteIDMessage:
    ua_type: UAType = UAType.MULTIROTOR
    id_type: IDType = IDType.SERIAL_NUMBER
    uas_id: str = ""
    operator_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    geodetic_altitude: float = 0.0
    pressure_altitude: float = 0.0
    height_above_takeoff: float = 0.0
    track_direction: float = 0.0
    speed: float = 0.0
    vertical_speed: float = 0.0
    timestamp: float = field(default_factory=time.time)
    operational_status: OperationalStatus = OperationalStatus.UNDECLARED
    operator_latitude: float = 0.0
    operator_longitude: float = 0.0
    operator_altitude: float = 0.0
    area_count: int = 1
    area_radius: float = 0.0
    area_ceiling: float = 0.0
    area_floor: float = 0.0

    REQUIRED_FIELDS = [
        "uas_id", "latitude", "longitude", "geodetic_altitude",
        "speed", "track_direction", "timestamp", "operational_status",
    ]


class RemoteIDTransmitter:
    """Simulated Remote ID transmitter (Bluetooth 5.0 + Network)."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.broadcast_interval_s = 1.0
        self.last_broadcast: Optional[float] = None
        self.broadcast_count = 0
        self.network_publish_count = 0

    def broadcast(self, message: RemoteIDMessage) -> bool:
        """Broadcast via Bluetooth 5.0 legacy advertising."""
        if not message.uas_id:
            return False
        self.last_broadcast = time.time()
        self.broadcast_count += 1
        return True

    def network_publish(self, message: RemoteIDMessage) -> bool:
        """Publish via network Remote ID."""
        if not message.uas_id:
            return False
        self.network_publish_count += 1
        return True

    def set_broadcast_interval(self, seconds: float) -> None:
        self.broadcast_interval_s = max(0.1, seconds)

    def get_compliance_status(self) -> Dict[str, Any]:
        return {
            "is_broadcasting": self.broadcast_count > 0,
            "broadcast_count": self.broadcast_count,
            "network_publish_count": self.network_publish_count,
            "broadcast_interval_s": self.broadcast_interval_s,
            "last_broadcast": self.last_broadcast,
        }


class RemoteIDReceiver:
    """Simulated Remote ID receiver/scanner."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.received_messages: Dict[str, RemoteIDMessage] = {}
        self.scan_count = 0

    def receive(self, message: RemoteIDMessage) -> None:
        """Receive a Remote ID message."""
        self.received_messages[message.uas_id] = message

    def scan(self) -> List[RemoteIDMessage]:
        """Scan for nearby Remote ID broadcasts."""
        self.scan_count += 1
        return list(self.received_messages.values())

    def get_nearby_uas(self, center_lat: float, center_lon: float, radius_m: float = 1000.0) -> List[RemoteIDMessage]:
        results = []
        for msg in self.received_messages.values():
            lat_diff = (msg.latitude - center_lat) * 111320.0
            lon_diff = (msg.longitude - center_lon) * 111320.0 * np.cos(np.radians(center_lat))
            dist = np.sqrt(lat_diff ** 2 + lon_diff ** 2)
            if dist <= radius_m:
                results.append(msg)
        return results

    def verify_message(self, message: RemoteIDMessage) -> Dict[str, Any]:
        """Validate required fields per ASTM F3411."""
        missing = []
        if not message.uas_id:
            missing.append("uas_id")
        if message.latitude == 0.0 and message.longitude == 0.0:
            missing.append("position")
        if message.operational_status == OperationalStatus.UNDECLARED:
            missing.append("operational_status")

        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "message_age_s": time.time() - message.timestamp,
        }
