"""Vicon/Optitrack VRPN→MAVLink ATT_POS_MOCAP #138 브리지 시뮬레이션."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class MocapPose:
    """모션캡처 시스템에서 수신한 6-DOF 포즈."""

    x: float          # 위치 X (m)
    y: float          # 위치 Y (m)
    z: float          # 위치 Z (m)
    qw: float         # 쿼터니언 w (스칼라)
    qx: float         # 쿼터니언 x
    qy: float         # 쿼터니언 y
    qz: float         # 쿼터니언 z
    timestamp: float  # UNIX 타임스탬프 (초)

    def is_unit_quaternion(self, tol: float = 1e-3) -> bool:
        """쿼터니언 정규화 여부 확인."""
        norm = math.sqrt(self.qw**2 + self.qx**2 + self.qy**2 + self.qz**2)
        return abs(norm - 1.0) < tol


class VRPNMocapBridge:
    """VRPN 포맷 딕셔너리를 MocapPose 및 MAVLink #138 메시지로 변환한다."""

    # VRPN 좌표계(Y-up, right-hand) → MAVLink NED 변환
    # MAVLink ATT_POS_MOCAP: NED 좌표계 (North-East-Down)
    def parse_vrpn(self, raw_data: dict) -> MocapPose:
        """VRPN 딕셔너리를 MocapPose로 변환한다.

        VRPN 예상 키: x, y, z (m), qw, qx, qy, qz, time (초).
        좌표 변환: VRPN(Z-up, right-hand) → NED
          NED_x =  VRPN_y  (North)
          NED_y =  VRPN_x  (East)
          NED_z = -VRPN_z  (Down)

        Args:
            raw_data: VRPN 클라이언트 딕셔너리.

        Returns:
            NED 기준 MocapPose.

        Raises:
            KeyError: 필수 필드 누락.
            ValueError: 쿼터니언이 단위벡터가 아닐 때.
        """
        required = {"x", "y", "z", "qw", "qx", "qy", "qz", "time"}
        missing = required - raw_data.keys()
        if missing:
            raise KeyError(f"VRPN 딕셔너리 필드 누락: {missing}")

        # 좌표계 변환 (Z-up → NED)
        ned_x = float(raw_data["y"])
        ned_y = float(raw_data["x"])
        ned_z = -float(raw_data["z"])

        qw = float(raw_data["qw"])
        qx = float(raw_data["qx"])
        qy = float(raw_data["qy"])
        qz = float(raw_data["qz"])

        norm = math.sqrt(qw**2 + qx**2 + qy**2 + qz**2)
        if norm < 1e-6:
            raise ValueError("쿼터니언 노름이 0에 가까워 정규화 불가")
        qw, qx, qy, qz = qw / norm, qx / norm, qy / norm, qz / norm

        return MocapPose(
            x=ned_x,
            y=ned_y,
            z=ned_z,
            qw=qw,
            qx=qx,
            qy=qy,
            qz=qz,
            timestamp=float(raw_data["time"]),
        )

    def to_mavlink_138(self, pose: MocapPose) -> dict:
        """MocapPose를 MAVLink ATT_POS_MOCAP (#138) 메시지 딕셔너리로 변환한다.

        MAVLink ATT_POS_MOCAP 필드:
          time_usec: 타임스탬프 (마이크로초)
          q[4]: 자세 쿼터니언 [w, x, y, z]
          x, y, z: 위치 (m, NED)

        Args:
            pose: NED 기준 MocapPose.

        Returns:
            MAVLink #138 메시지 딕셔너리.
        """
        return {
            "mavlink_msg_id": 138,
            "msg_name": "ATT_POS_MOCAP",
            "time_usec": int(pose.timestamp * 1e6),
            "q": [pose.qw, pose.qx, pose.qy, pose.qz],
            "x": pose.x,
            "y": pose.y,
            "z": pose.z,
        }


class HITLBridge:
    """VRPNMocapBridge를 래핑하여 HITL 지연 시뮬레이션을 추가한다."""

    def __init__(
        self,
        latency_ms: float = 2.0,
        jitter_ms: float = 0.5,
        seed: int = 42,
    ) -> None:
        """
        Args:
            latency_ms: 평균 전송 지연 (ms).
            jitter_ms: 지연 지터 표준편차 (ms).
            seed: 난수 시드 (재현성).
        """
        self._bridge = VRPNMocapBridge()
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self._rng = np.random.default_rng(seed)
        self.relay_count = 0

    def relay(self, raw_data: dict) -> dict:
        """VRPN 데이터를 MAVLink #138 메시지로 변환한다 (지연 시뮬레이션 포함).

        Args:
            raw_data: VRPN 딕셔너리.

        Returns:
            MAVLink ATT_POS_MOCAP (#138) 딕셔너리 (시뮬 지연 메타데이터 포함).
        """
        pose = self._bridge.parse_vrpn(raw_data)
        msg = self._bridge.to_mavlink_138(pose)

        # 지연 시뮬레이션 (음수 방지)
        delay = max(0.0, float(self._rng.normal(self.latency_ms, self.jitter_ms)))
        msg["sim_latency_ms"] = round(delay, 3)
        self.relay_count += 1
        return msg
