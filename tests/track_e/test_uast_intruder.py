"""P737 UAS-T intruder response decision tree 검증."""
from __future__ import annotations

import pytest

from src.uast.intruder_response import (
    IntruderObservation,
    Response,
    ThreatLevel,
    assess_threat,
    handle_intruder,
    select_response,
)


def _obs(**kwargs) -> IntruderObservation:
    base = {
        "distance_m": 100.0,
        "bearing_deg": 90.0,
        "closing_speed_mps": 5.0,
        "tcpa_s": 30.0,
        "cpa_distance_m": 50.0,
        "classification": "unknown",
        "classification_confidence": 0.5,
        "has_remote_id": False,
        "altitude_diff_m": 20.0,
    }
    base.update(kwargs)
    return IntruderObservation(**base)


def test_bird_is_safe() -> None:
    """조류 + 높은 신뢰도 → SAFE."""
    obs = _obs(classification="bird", classification_confidence=0.9)
    assert assess_threat(obs) == ThreatLevel.SAFE
    assert select_response(ThreatLevel.SAFE, obs) == Response.IGNORE


def test_hostile_is_critical() -> None:
    """적대적 + 높은 신뢰도 → CRITICAL → RTL_AND_ALARM."""
    obs = _obs(classification="hostile", classification_confidence=0.8)
    assert assess_threat(obs) == ThreatLevel.CRITICAL
    assert select_response(ThreatLevel.CRITICAL, obs) == Response.RTL_AND_ALARM


def test_cooperative_with_rid_is_low() -> None:
    """협조 + RID 보유 → LOW → MONITOR."""
    obs = _obs(classification="cooperative", has_remote_id=True)
    assert assess_threat(obs) == ThreatLevel.LOW
    assert select_response(ThreatLevel.LOW, obs) == Response.MONITOR


def test_close_imminent_is_high_evade() -> None:
    """근접 + 임박 + 고도차 충분 → HIGH → EVADE."""
    obs = _obs(cpa_distance_m=25.0, tcpa_s=15.0, altitude_diff_m=40.0)
    assert assess_threat(obs) == ThreatLevel.HIGH
    assert select_response(ThreatLevel.HIGH, obs) == Response.EVADE


def test_close_imminent_low_alt_is_emergency_land() -> None:
    """근접 + 임박 + 고도차 부족 → HIGH → EMERGENCY_LAND."""
    obs = _obs(cpa_distance_m=25.0, tcpa_s=15.0, altitude_diff_m=10.0)
    threat, response = handle_intruder(obs)
    assert threat == ThreatLevel.HIGH
    assert response == Response.EMERGENCY_LAND


def test_far_distance_is_low() -> None:
    """CPA 거리 충분 → LOW."""
    obs = _obs(cpa_distance_m=200.0)
    assert assess_threat(obs) == ThreatLevel.LOW


def test_tcpa_negative_is_low() -> None:
    """이미 발산 (tcpa<0) → LOW."""
    obs = _obs(tcpa_s=-5.0)
    assert assess_threat(obs) == ThreatLevel.LOW


def test_handle_intruder_returns_tuple() -> None:
    """통합 핸들러는 (ThreatLevel, Response) tuple."""
    obs = _obs(classification="bird", classification_confidence=0.9)
    threat, response = handle_intruder(obs)
    assert isinstance(threat, ThreatLevel)
    assert isinstance(response, Response)


@pytest.mark.parametrize("classification,confidence,expected_safe", [
    ("bird", 0.9, True),
    ("bird", 0.5, False),  # 낮은 신뢰도는 unknown 처리
    ("hostile", 0.5, False),  # 낮은 신뢰도는 즉시 critical 안 함
])
def test_classification_confidence_matters(
    classification: str,
    confidence: float,
    expected_safe: bool,
) -> None:
    """분류 신뢰도가 위협 등급에 영향."""
    obs = _obs(classification=classification, classification_confidence=confidence)
    threat = assess_threat(obs)
    if expected_safe:
        assert threat == ThreatLevel.SAFE
    else:
        assert threat != ThreatLevel.SAFE
