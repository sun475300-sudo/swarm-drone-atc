"""P697: Vicon/Optitrack VRPN→MAVLink HITL 브릿지 시뮬레이션.

실내 Motion Capture 시스템에서 수신한 정밀 위치를
MAVLink ATT_POS_MOCAP 메시지로 변환해 드론에 주입.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MocapSystem(Enum):
    VICON = "Vicon"
    OPTITRACK = "OptiTrack"
    QUALISYS = "Qualisys"


# MAVLink 메시지 ID
MAVLINK_MSG_ATT_POS_MOCAP = 138
MAVLINK_MSG_VISION_POSITION_ESTIMATE = 102


@dataclass
class VRPNPose:
    """VRPN 6-DOF 포즈 (트래킹 좌표계)."""
    tracker_name: str
    x: float        # m
    y: float        # m
    z: float        # m
    qw: float = 1.0
    qx: float = 0.0
    qy: float = 0.0
    qz: float = 0.0
    timestamp_us: int = field(default_factory=lambda: int(time.monotonic() * 1e6))


@dataclass
class MAVLinkMocapMessage:
    """ATT_POS_MOCAP #138 페이로드."""
    time_usec: int
    q: tuple[float, float, float, float]    # quaternion [w, x, y, z]
    x: float
    y: float
    z: float
    covariance: list[float] = field(default_factory=lambda: [0.0] * 21)

    def pack(self) -> bytes:
        """21개 공분산 포함 바이너리 직렬화 (little-endian).

        ATT_POS_MOCAP #138: time_usec(8) + q×4(16) + xyz×3(12) + cov×21(84) = 120 bytes
        """
        return struct.pack(
            "<Q4f3f21f",
            self.time_usec,
            *self.q,
            self.x, self.y, self.z,
            *self.covariance,
        )


def vrpn_to_ned(pose: VRPNPose) -> tuple[float, float, float]:
    """Vicon/OptiTrack 좌표(Z-up, X-forward) → NED 변환."""
    # Vicon: X-right, Y-up, Z-backward → NED: X-north, Y-east, Z-down
    return pose.x, -pose.z, -pose.y


class MocapHITLBridge:
    """Motion Capture 시스템 → MAVLink HITL 브릿지.

    실기 환경에서는 UDP 소켓으로 VRPN 스트림을 수신하고
    MAVLink 직렬 포트로 전송. 여기서는 시뮬레이션 인터페이스만 구현.
    """

    def __init__(self, system: MocapSystem = MocapSystem.VICON, update_rate_hz: float = 100.0) -> None:
        self.system = system
        self.update_rate_hz = update_rate_hz
        self._last_pose: dict[str, VRPNPose] = {}
        self._message_count = 0
        self._callbacks: list[Any] = []

    def ingest_vrpn(self, pose: VRPNPose) -> MAVLinkMocapMessage:
        """VRPN 포즈 수신 → MAVLink HITL 메시지 변환·발행."""
        self._last_pose[pose.tracker_name] = pose
        ned_x, ned_y, ned_z = vrpn_to_ned(pose)
        msg = MAVLinkMocapMessage(
            time_usec=pose.timestamp_us,
            q=(pose.qw, pose.qx, pose.qy, pose.qz),
            x=ned_x, y=ned_y, z=ned_z,
        )
        self._message_count += 1
        for cb in self._callbacks:
            cb(pose.tracker_name, msg)
        return msg

    def get_pose(self, tracker_name: str) -> VRPNPose | None:
        return self._last_pose.get(tracker_name)

    def register_output_callback(self, fn: Any) -> None:
        """MAVLink 메시지 생성 시 호출 (예: 실제 UART write 함수)."""
        self._callbacks.append(fn)

    @property
    def message_count(self) -> int:
        return self._message_count

    def latency_budget_us(self) -> float:
        """100Hz 업데이트 기준 허용 레이턴시 예산 (μs)."""
        return 1_000_000.0 / self.update_rate_hz * 0.5   # 50% budget

    def status(self) -> dict[str, Any]:
        return {
            "system": self.system.value,
            "rate_hz": self.update_rate_hz,
            "tracked_objects": list(self._last_pose.keys()),
            "message_count": self._message_count,
        }
