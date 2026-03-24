"""분산 드론 통신 메시지 타입 (MAVLink/DDS 추상화)"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class TelemetryMessage:
    """드론 → 시스템 텔레메트리 (50ms 주기)"""
    drone_id: str
    position: np.ndarray       # [x, y, z]
    velocity: np.ndarray       # [vx, vy, vz]
    battery_pct: float
    flight_phase: str
    timestamp_s: float
    is_registered: bool = True


@dataclass
class ClearanceRequest:
    """드론 → 컨트롤러: 비행 허가 요청"""
    drone_id: str
    origin: np.ndarray
    destination: np.ndarray
    priority: int
    timestamp_s: float
    profile_name: str = "COMMERCIAL_DELIVERY"


@dataclass
class ClearanceResponse:
    """컨트롤러 → 드론: 비행 허가 응답"""
    drone_id: str
    approved: bool
    assigned_waypoints: list[np.ndarray]
    altitude_band: tuple[float, float]
    timestamp_s: float
    reason: str = ""


@dataclass
class ResolutionAdvisory:
    """컨트롤러 → 드론: 충돌 회피 어드바이저리"""
    advisory_id: str
    target_drone_id: str
    advisory_type: str          # CLIMB, DESCEND, TURN_LEFT, TURN_RIGHT, HOLD, EVADE_APF
    magnitude: float            # 변경량 (m 또는 도)
    duration_s: float
    timestamp_s: float
    conflict_pair: Optional[str] = None  # 충돌 상대 드론 ID


@dataclass
class IntrusionAlert:
    """시스템 → 관제사: 침입 드론 경보"""
    alert_id: str
    intruder_id: str
    detection_position: np.ndarray
    detection_time_s: float
    threat_level: str           # LOW, MEDIUM, HIGH, CRITICAL
    nearest_registered_id: Optional[str] = None
