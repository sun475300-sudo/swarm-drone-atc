"""Phase 697: 실내 Motion Capture (Vicon/Optitrack) HITL 브릿지."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class MocapSystem(Enum):
    """MoCap 시스템 종류."""
    VICON = "vicon"
    OPTITRACK = "optitrack"
    SIMULATION = "simulation"


class HITLState(Enum):
    """HITL 루프 상태."""
    IDLE = "idle"
    RECEIVING = "receiving"
    PUBLISHING = "publishing"
    ERROR = "error"


@dataclass
class Pose6DoF:
    """6DoF 포즈 (위치 + 자세)."""
    x_m: float
    y_m: float
    z_m: float
    roll_rad: float
    pitch_rad: float
    yaw_rad: float
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0


@dataclass
class VisionPositionEstimate:
    """MAVLink VISION_POSITION_ESTIMATE 메시지."""
    usec: int
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float
    covariance: list[float] = field(default_factory=lambda: [0.01] * 21)

    def to_dict(self) -> dict[str, Any]:
        return {
            "msg_type": "VISION_POSITION_ESTIMATE",
            "usec": self.usec,
            "x": self.x, "y": self.y, "z": self.z,
            "roll": self.roll, "pitch": self.pitch, "yaw": self.yaw,
        }


@dataclass
class HITLStats:
    """HITL 루프 통계."""
    frames_received: int = 0
    msgs_published: int = 0
    latency_sum_us: float = 0.0
    latency_count: int = 0
    errors: int = 0

    @property
    def avg_latency_us(self) -> float:
        if self.latency_count == 0:
            return 0.0
        return self.latency_sum_us / self.latency_count


VRPN_PORT = 3883
PUBLISH_INTERVAL_S = 0.02
LATENCY_TARGET_US = 2000.0


class MocapHITLBridge:
    """Vicon/Optitrack VRPN UDP 스트림 → MAVLink VISION_POSITION_ESTIMATE 브릿지."""

    def __init__(
        self,
        system: MocapSystem = MocapSystem.SIMULATION,
        vrpn_host: str = "192.168.1.100",
        vrpn_port: int = VRPN_PORT,
        seed: int = 42,
    ) -> None:
        self.system = system
        self.vrpn_host = vrpn_host
        self.vrpn_port = vrpn_port
        self.rng = np.random.default_rng(seed)
        self.state = HITLState.IDLE
        self.stats = HITLStats()
        self._pose_cache: dict[str, Pose6DoF] = {}
        self._latency_history: list[float] = []

    def start(self) -> bool:
        """HITL 루프 시작."""
        self.state = HITLState.RECEIVING
        return True

    def stop(self) -> None:
        """HITL 루프 정지."""
        self.state = HITLState.IDLE

    def ingest_vrpn_frame(self, drone_id: str, raw_data: bytes | None = None) -> Pose6DoF:
        """VRPN UDP 프레임 수신 처리 (시뮬: 랜덤 포즈 생성)."""
        if raw_data is not None and len(raw_data) >= 48:
            arr = np.frombuffer(raw_data[:48], dtype=np.float64)
            pose = Pose6DoF(
                x_m=float(arr[0]), y_m=float(arr[1]), z_m=float(arr[2]),
                roll_rad=float(arr[3]), pitch_rad=float(arr[4]), yaw_rad=float(arr[5]),
            )
        else:
            if drone_id in self._pose_cache:
                prev = self._pose_cache[drone_id]
                pose = Pose6DoF(
                    x_m=prev.x_m + float(self.rng.normal(0, 0.002)),
                    y_m=prev.y_m + float(self.rng.normal(0, 0.002)),
                    z_m=max(0.0, prev.z_m + float(self.rng.normal(0, 0.001))),
                    roll_rad=prev.roll_rad + float(self.rng.normal(0, 0.001)),
                    pitch_rad=prev.pitch_rad + float(self.rng.normal(0, 0.001)),
                    yaw_rad=prev.yaw_rad + float(self.rng.normal(0, 0.002)),
                )
            else:
                pose = Pose6DoF(
                    x_m=float(self.rng.uniform(-5, 5)),
                    y_m=float(self.rng.uniform(-5, 5)),
                    z_m=float(self.rng.uniform(0.5, 3.0)),
                    roll_rad=float(self.rng.normal(0, 0.05)),
                    pitch_rad=float(self.rng.normal(0, 0.05)),
                    yaw_rad=float(self.rng.uniform(-np.pi, np.pi)),
                )

        self._pose_cache[drone_id] = pose
        self.stats.frames_received += 1
        return pose

    def pose_to_vision_estimate(self, pose: Pose6DoF) -> VisionPositionEstimate:
        """Pose6DoF → MAVLink VISION_POSITION_ESTIMATE 변환."""
        now_us = int(time.time() * 1e6)
        return VisionPositionEstimate(
            usec=now_us,
            x=pose.x_m, y=pose.y_m, z=-pose.z_m,
            roll=pose.roll_rad, pitch=pose.pitch_rad, yaw=pose.yaw_rad,
        )

    def process(self, drone_id: str, raw_data: bytes | None = None) -> dict[str, Any]:
        """수신 → 변환 → 발행 1-스텝 처리."""
        t0 = time.time()
        pose = self.ingest_vrpn_frame(drone_id, raw_data)
        vision_msg = self.pose_to_vision_estimate(pose)
        latency_us = (time.time() - t0) * 1e6
        self.stats.msgs_published += 1
        self.stats.latency_sum_us += latency_us
        self.stats.latency_count += 1
        self._latency_history.append(latency_us)
        if len(self._latency_history) > 1000:
            self._latency_history.pop(0)
        return vision_msg.to_dict()

    def get_latency_report(self) -> dict[str, float]:
        if not self._latency_history:
            return {"mean_us": 0.0, "p99_us": 0.0, "target_us": LATENCY_TARGET_US, "compliant": True}
        arr = np.array(self._latency_history)
        p99 = float(np.percentile(arr, 99))
        return {
            "mean_us": float(arr.mean()),
            "p99_us": p99,
            "target_us": LATENCY_TARGET_US,
            "compliant": p99 <= LATENCY_TARGET_US,
        }
