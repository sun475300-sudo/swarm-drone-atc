"""
DroneState 데이터클래스 — 드론 1기의 완전한 상태 표현
분산 제어 시스템: 각 드론이 자신의 상태를 자율적으로 관리
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import numpy as np


class FlightPhase(Enum):
    GROUNDED = auto()
    TAKEOFF = auto()
    ENROUTE = auto()
    HOLDING = auto()
    LANDING = auto()
    FAILED = auto()
    RTL = auto()          # Return To Launch (Lost-link 자율 복귀)
    EVADING = auto()      # APF 회피 기동 중


class CommsStatus(Enum):
    NOMINAL = auto()      # 정상
    DEGRADED = auto()     # 지연/패킷 손실
    LOST = auto()         # 두절 → Lost-link 프로토콜 활성화


class FailureType(Enum):
    NONE = auto()
    MOTOR_FAILURE = auto()       # 즉각 하강
    BATTERY_CRITICAL = auto()    # 비상 착륙
    GPS_LOSS = auto()            # 위치 유지
    COMMS_LOSS = auto()          # 자율 복귀
    SENSOR_FAILURE = auto()      # 감지 불능


@dataclass
class DroneState:
    """드론 1기의 완전한 상태"""
    drone_id: str
    position: np.ndarray             # [x, y, z] NED 좌표 (m)
    velocity: np.ndarray             # [vx, vy, vz] (m/s)
    heading: float = 0.0             # 방위각 (도)
    battery_pct: float = 100.0       # 배터리 잔량 (%)
    flight_phase: FlightPhase = FlightPhase.GROUNDED
    comms_status: CommsStatus = CommsStatus.NOMINAL
    failure_type: FailureType = FailureType.NONE

    # 비행 계획
    goal: Optional[np.ndarray] = None            # 현재 목표 위치
    waypoints: list[np.ndarray] = field(default_factory=list)
    current_waypoint_idx: int = 0

    # 성능 추적
    distance_flown_m: float = 0.0
    planned_distance_m: float = 0.0
    flight_time_s: float = 0.0

    # 드론 프로파일 참조
    profile_name: str = "COMMERCIAL_DELIVERY"

    # HOLDING 진입 시각 (HOLDING → ENROUTE 복귀 타이머)
    _hold_start_s: Optional[float] = None

    # 타임스탬프
    last_update_s: float = 0.0

    def __post_init__(self):
        if isinstance(self.position, list):
            self.position = np.array(self.position, dtype=float)
        if isinstance(self.velocity, list):
            self.velocity = np.array(self.velocity, dtype=float)

    @property
    def is_active(self) -> bool:
        return self.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED)

    @property
    def is_failed(self) -> bool:
        return self.failure_type != FailureType.NONE

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.velocity))

    def to_dict(self) -> dict:
        return {
            "drone_id": self.drone_id,
            "position": self.position.tolist(),
            "velocity": self.velocity.tolist(),
            "heading": self.heading,
            "battery_pct": self.battery_pct,
            "flight_phase": self.flight_phase.name,
            "comms_status": self.comms_status.name,
            "failure_type": self.failure_type.name,
            "speed_ms": self.speed,
        }
