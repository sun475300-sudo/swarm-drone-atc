"""Phase 671: PX4/ArduPilot SITL 연동 시뮬레이션 브릿지."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class FlightMode(Enum):
    GUIDED = "GUIDED"
    AUTO = "AUTO"
    LOITER = "LOITER"
    RTL = "RTL"
    LAND = "LAND"
    STABILIZE = "STABILIZE"


@dataclass
class MAVLinkMessage:
    msg_type: str
    seq: int
    system_id: int
    component_id: int
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class VehicleState:
    drone_id: str
    position: np.ndarray  # (3,) lat, lon, alt
    velocity: np.ndarray  # (3,) vn, ve, vd
    attitude: np.ndarray  # (3,) roll, pitch, yaw
    battery_pct: float = 100.0
    gps_fix: int = 3  # 0=no fix, 2=2D, 3=3D
    armed: bool = False
    mode: FlightMode = FlightMode.STABILIZE


class PX4SITLBridge:
    """Simulated PX4/ArduPilot SITL bridge for testing without hardware."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.connected = False
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.vehicles: Dict[str, VehicleState] = {}
        self.msg_seq = 0
        self.stats = {
            "msgs_sent": 0, "msgs_received": 0,
            "connect_time": 0.0, "errors": 0,
        }

    def connect(self, host: str = "127.0.0.1", port: int = 14540) -> bool:
        self.host = host
        self.port = port
        self.connected = True
        self.stats["connect_time"] = time.time()
        return True

    def disconnect(self) -> None:
        self.connected = False
        self.host = None
        self.port = None

    def _check_connection(self) -> bool:
        if not self.connected:
            self.stats["errors"] += 1
        return self.connected

    def _ensure_vehicle(self, drone_id: str) -> VehicleState:
        if drone_id not in self.vehicles:
            self.vehicles[drone_id] = VehicleState(
                drone_id=drone_id,
                position=self.rng.uniform(-100, 100, size=3),
                velocity=np.zeros(3),
                attitude=np.zeros(3),
            )
        return self.vehicles[drone_id]

    def send_command(self, command_type: str, params: Dict[str, Any]) -> bool:
        if not self._check_connection():
            return False
        self.msg_seq += 1
        self.stats["msgs_sent"] += 1
        return True

    def receive_telemetry(self) -> Optional[MAVLinkMessage]:
        if not self._check_connection():
            return None
        self.msg_seq += 1
        self.stats["msgs_received"] += 1

        vehicle_ids = list(self.vehicles.keys())
        if not vehicle_ids:
            return MAVLinkMessage(
                msg_type="HEARTBEAT", seq=self.msg_seq,
                system_id=1, component_id=1, payload={"type": "heartbeat"},
            )

        vid = self.rng.choice(vehicle_ids)
        vs = self.vehicles[vid]
        return MAVLinkMessage(
            msg_type="GLOBAL_POSITION_INT", seq=self.msg_seq,
            system_id=int(vid.split("_")[-1]) if "_" in vid else 1,
            component_id=1,
            payload={
                "drone_id": vid,
                "lat": float(vs.position[0]),
                "lon": float(vs.position[1]),
                "alt": float(vs.position[2]),
                "vx": float(vs.velocity[0]),
                "vy": float(vs.velocity[1]),
                "vz": float(vs.velocity[2]),
            },
        )

    def arm_drone(self, drone_id: str) -> bool:
        if not self._check_connection():
            return False
        vs = self._ensure_vehicle(drone_id)
        vs.armed = True
        self.stats["msgs_sent"] += 1
        return True

    def disarm_drone(self, drone_id: str) -> bool:
        if not self._check_connection():
            return False
        vs = self._ensure_vehicle(drone_id)
        vs.armed = False
        self.stats["msgs_sent"] += 1
        return True

    def set_mode(self, drone_id: str, mode: str) -> bool:
        if not self._check_connection():
            return False
        vs = self._ensure_vehicle(drone_id)
        try:
            vs.mode = FlightMode(mode)
        except ValueError:
            self.stats["errors"] += 1
            return False
        self.stats["msgs_sent"] += 1
        return True

    def send_waypoint(self, drone_id: str, lat: float, lon: float, alt: float) -> bool:
        if not self._check_connection():
            return False
        vs = self._ensure_vehicle(drone_id)
        target = np.array([lat, lon, alt])
        direction = target - vs.position
        dist = np.linalg.norm(direction)
        if dist > 0:
            vs.velocity = direction / dist * 5.0  # 5 m/s cruise
        vs.position = vs.position + vs.velocity * 0.1
        self.stats["msgs_sent"] += 1
        return True

    def get_vehicle_state(self, drone_id: str) -> Dict[str, Any]:
        vs = self._ensure_vehicle(drone_id)
        return {
            "drone_id": vs.drone_id,
            "position": vs.position.tolist(),
            "velocity": vs.velocity.tolist(),
            "attitude": vs.attitude.tolist(),
            "battery_pct": vs.battery_pct,
            "gps_fix": vs.gps_fix,
            "armed": vs.armed,
            "mode": vs.mode.value,
        }

    def get_connection_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "connected": self.connected,
            "host": self.host,
            "port": self.port,
            "vehicle_count": len(self.vehicles),
        }
