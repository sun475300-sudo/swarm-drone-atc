"""P737: 비협조 침입자(UAS-T) 대응 결정 트리.

DnI 정확도(P735) + 위협 분류 → 회피 결정 트리. 적대적 시나리오 100건 평가.

Decision Tree:
    1. 침입자 분류 (조류/협조/비협조/적대적) — DnI
    2. 위협 등급 산정 — TCPA + 거리 + 의도
    3. 대응 선택:
        - Bird/협조: 무시 (기존 ATC)
        - 비협조: 우선 회피 + RID 송신 강화
        - 적대적: 즉시 LAND + 운영자 알람
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ThreatLevel(Enum):
    """위협 등급."""

    SAFE = 0       # 조류·먼 거리
    LOW = 1        # 협조 트래픽
    MEDIUM = 2     # 비협조, 거리 충분
    HIGH = 3       # 비협조, 임박
    CRITICAL = 4   # 적대적·근접


class Response(Enum):
    """대응 액션."""

    IGNORE = "ignore"
    MONITOR = "monitor"
    EVADE = "evade"
    EMERGENCY_LAND = "emergency_land"
    RTL_AND_ALARM = "rtl_and_alarm"


@dataclass(frozen=True)
class IntruderObservation:
    """침입자 관측 데이터."""

    distance_m: float
    bearing_deg: float
    closing_speed_mps: float
    tcpa_s: float                  # CPA 도달 시간
    cpa_distance_m: float          # CPA 시점 이격거리
    classification: str            # 'bird' | 'cooperative' | 'unknown' | 'hostile'
    classification_confidence: float  # 0.0 - 1.0
    has_remote_id: bool
    altitude_diff_m: float


def assess_threat(obs: IntruderObservation) -> ThreatLevel:
    """관측치로부터 위협 등급 산정."""
    if obs.classification == "hostile" and obs.classification_confidence > 0.7:
        return ThreatLevel.CRITICAL

    if obs.classification == "bird" and obs.classification_confidence > 0.8:
        return ThreatLevel.SAFE

    if obs.tcpa_s < 0 or obs.tcpa_s > 90:
        return ThreatLevel.LOW

    if obs.cpa_distance_m > 100:
        return ThreatLevel.LOW

    if obs.has_remote_id and obs.classification == "cooperative":
        return ThreatLevel.LOW

    if obs.cpa_distance_m < 30 and obs.tcpa_s < 20:
        return ThreatLevel.HIGH

    return ThreatLevel.MEDIUM


def select_response(threat: ThreatLevel, obs: IntruderObservation) -> Response:
    """위협 등급 → 대응 액션 결정 트리."""
    if threat == ThreatLevel.SAFE:
        return Response.IGNORE
    if threat == ThreatLevel.LOW:
        return Response.MONITOR
    if threat == ThreatLevel.MEDIUM:
        return Response.EVADE
    if threat == ThreatLevel.HIGH:
        return Response.EVADE if obs.altitude_diff_m > 30 else Response.EMERGENCY_LAND
    return Response.RTL_AND_ALARM  # CRITICAL


def handle_intruder(obs: IntruderObservation) -> tuple[ThreatLevel, Response]:
    """통합 진입점 — 위협 등급 + 대응 동시 반환."""
    threat = assess_threat(obs)
    response = select_response(threat, obs)
    return threat, response
