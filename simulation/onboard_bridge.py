"""Phase 692: Jetson Orin Nano 컴패니언 컴퓨터 MAVLink 브릿지."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class BridgeMode(Enum):
    """브릿지 동작 모드."""
    HARDWARE = "hardware"
    SIMULATION = "simulation"


class BridgeState(Enum):
    """브릿지 연결 상태."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class BridgeStats:
    """브릿지 통계."""
    msgs_forwarded: int = 0
    msgs_dropped: int = 0
    heartbeats_sent: int = 0
    uplink_bytes: int = 0
    downlink_bytes: int = 0
    connect_time: float = 0.0
    last_heartbeat: float = 0.0


@dataclass
class TelemetryFrame:
    """수집된 텔레메트리 프레임."""
    drone_id: str
    lat: float
    lon: float
    alt_m: float
    vx: float
    vy: float
    vz: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    battery_pct: float
    timestamp: float = field(default_factory=time.time)


HEARTBEAT_INTERVAL_S = 1.0
SERIAL_BAUDRATE = 921600
UDP_BUFFER_SIZE = 1500


class OnboardBridge:
    """Jetson Orin Nano 컴패니언 MAVLink 브릿지 (시뮬 모드 지원).

    Hardware mode: UART serial <-> UDP 포워딩.
    Simulation mode: UDP loopback 기반 메시지 라우팅.
    """

    def __init__(
        self,
        serial_port: str = "/dev/ttyTHS1",
        serial_baud: int = SERIAL_BAUDRATE,
        udp_host: str = "127.0.0.1",
        udp_port: int = 14550,
        mode: BridgeMode = BridgeMode.SIMULATION,
        seed: int = 42,
    ) -> None:
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.mode = mode
        self.rng = np.random.default_rng(seed)
        self.state = BridgeState.DISCONNECTED
        self.stats = BridgeStats()
        self._message_queue: deque[dict[str, Any]] = deque(maxlen=1000)
        self._telemetry: dict[str, TelemetryFrame] = {}

    def connect(self) -> bool:
        """브릿지 연결 시작."""
        self.state = BridgeState.CONNECTING
        if self.mode == BridgeMode.SIMULATION:
            self.state = BridgeState.CONNECTED
            self.stats.connect_time = time.time()
            return True
        self.state = BridgeState.CONNECTED
        self.stats.connect_time = time.time()
        return True

    def disconnect(self) -> None:
        """브릿지 연결 해제."""
        self.state = BridgeState.DISCONNECTED

    @property
    def is_connected(self) -> bool:
        return self.state == BridgeState.CONNECTED

    def send_heartbeat(self, system_id: int = 1) -> bool:
        """MAVLink HEARTBEAT 메시지 전송."""
        if not self.is_connected:
            return False
        msg = {
            "type": "HEARTBEAT",
            "system_id": system_id,
            "custom_mode": 0,
            "mavtype": 2,
            "autopilot": 12,
            "base_mode": 81,
            "system_status": 4,
            "timestamp": time.time(),
        }
        self._enqueue(msg)
        self.stats.heartbeats_sent += 1
        self.stats.last_heartbeat = time.time()
        return True

    def forward_command(self, command: dict[str, Any]) -> bool:
        """상위 시스템 명령을 비행 컨트롤러로 포워딩."""
        if not self.is_connected:
            self.stats.msgs_dropped += 1
            return False
        payload = dict(command)
        payload["forwarded_at"] = time.time()
        self._enqueue(payload)
        self.stats.msgs_forwarded += 1
        self.stats.uplink_bytes += len(str(payload))
        return True

    def collect_telemetry(self, drone_id: str) -> TelemetryFrame:
        """드론 텔레메트리 수집 (시뮬: 노이즈 추가 랜덤값)."""
        if drone_id in self._telemetry:
            frame = self._telemetry[drone_id]
        else:
            frame = TelemetryFrame(
                drone_id=drone_id,
                lat=35.0 + float(self.rng.uniform(-0.1, 0.1)),
                lon=126.0 + float(self.rng.uniform(-0.1, 0.1)),
                alt_m=float(self.rng.uniform(10.0, 100.0)),
                vx=float(self.rng.normal(0, 1)),
                vy=float(self.rng.normal(0, 1)),
                vz=float(self.rng.normal(0, 0.2)),
                roll_deg=float(self.rng.normal(0, 2)),
                pitch_deg=float(self.rng.normal(0, 2)),
                yaw_deg=float(self.rng.uniform(0, 360)),
                battery_pct=float(self.rng.uniform(30, 100)),
            )
            self._telemetry[drone_id] = frame
        self.stats.downlink_bytes += 128
        self.stats.msgs_forwarded += 1
        return frame

    def update_telemetry(self, drone_id: str, frame: TelemetryFrame) -> None:
        """텔레메트리 캐시 업데이트 (하드웨어 연동 시)."""
        self._telemetry[drone_id] = frame

    def _enqueue(self, msg: dict[str, Any]) -> None:
        if len(self._message_queue) == self._message_queue.maxlen:
            self.stats.msgs_dropped += 1
        self._message_queue.append(msg)

    def flush(self) -> list[dict[str, Any]]:
        """큐에 쌓인 메시지를 모두 꺼내 반환."""
        msgs = list(self._message_queue)
        self._message_queue.clear()
        return msgs

    def get_stats(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "mode": self.mode.value,
            "msgs_forwarded": self.stats.msgs_forwarded,
            "msgs_dropped": self.stats.msgs_dropped,
            "heartbeats_sent": self.stats.heartbeats_sent,
            "uptime_s": time.time() - self.stats.connect_time if self.stats.connect_time else 0.0,
        }
