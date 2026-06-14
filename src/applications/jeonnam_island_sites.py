"""GENESIS Phase 342: 전남 도서지역(신안·완도) 의료 배송 거점 DB.

P751 `medical_delivery.py` 의 일반 모델에 **실 지역 거점 좌표**를 입혀
신안·완도 도서 의료 배송 경로를 산출한다.

좌표 정확도 안내(maturity honesty):
    아래 좌표는 공개 지도 기준 **도서 중심 근사값**이며 실측(RTK/측량) 값이 아니다.
    실증 배치 시 해도·정밀 측량으로 갱신해야 한다(GENESIS Phase 341 연계).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.applications.medical_delivery import (
    DeliveryRequest,
    Urgency,
    can_meet_sla,
    estimate_eta_min,
    haversine_km,
)


@dataclass(frozen=True)
class IslandSite:
    """도서 배송 거점 (근사 좌표)."""

    name: str
    county: str          # 신안군 / 완도군
    lat: float
    lon: float


@dataclass(frozen=True)
class BaseHospital:
    """배송 출발 거점 병원 (근사 좌표)."""

    name: str
    lat: float
    lon: float


# 출발 거점 — 목포(신안권)·완도(완도권) 거점 병원 (근사 좌표)
BASE_HOSPITALS: tuple[BaseHospital, ...] = (
    BaseHospital("목포한국병원", 34.7936, 126.3886),
    BaseHospital("완도대성병원", 34.3110, 126.7550),
)

# 신안·완도 도서 거점 (공개 지도 기준 도서 중심 근사 좌표)
ISLAND_SITES: tuple[IslandSite, ...] = (
    # 신안군
    IslandSite("안좌도", "신안군", 34.7320, 126.1290),
    IslandSite("비금도", "신안군", 34.7570, 125.9560),
    IslandSite("도초도", "신안군", 34.6940, 125.9530),
    IslandSite("흑산도", "신안군", 34.6840, 125.4360),
    IslandSite("홍도", "신안군", 34.6860, 125.1960),
    # 완도군
    IslandSite("노화도", "완도군", 34.1730, 126.5170),
    IslandSite("보길도", "완도군", 34.1490, 126.5320),
    IslandSite("청산도", "완도군", 34.1730, 126.8650),
    IslandSite("소안도", "완도군", 34.1290, 126.5990),
)


def nearest_base(site: IslandSite) -> tuple[BaseHospital, float]:
    """도서 거점에서 가장 가까운 출발 병원과 거리(km)."""
    best: BaseHospital | None = None
    best_km = float("inf")
    for base in BASE_HOSPITALS:
        km = haversine_km(base.lat, base.lon, site.lat, site.lon)
        if km < best_km:
            best, best_km = base, km
    assert best is not None  # BASE_HOSPITALS 비어있지 않음
    return best, best_km


def delivery_request_for(
    site: IslandSite,
    medication: str,
    urgency: Urgency,
    requested_ts: float,
    payload_kg: float = 0.5,
) -> DeliveryRequest:
    """도서 거점을 목적지로 하는 배송 요청 생성."""
    return DeliveryRequest(
        request_id=f"{site.county}-{site.name}-{int(requested_ts)}",
        medication=medication,
        urgency=urgency,
        destination_lat=site.lat,
        destination_lon=site.lon,
        requested_ts=requested_ts,
        payload_kg=payload_kg,
    )


def route_eta_table(
    urgency: Urgency = Urgency.CRITICAL,
    cruise_speed_kmh: float = 60.0,
) -> dict[str, dict[str, float | str | bool]]:
    """전 도서 거점에 대한 최근접 병원·거리·ETA·SLA 충족 표.

    키는 거점명, 값은 base/distance_km/eta_min/meets_sla.
    """
    table: dict[str, dict[str, float | str | bool]] = {}
    for site in ISLAND_SITES:
        base, dist_km = nearest_base(site)
        req = delivery_request_for(site, "emergency_kit", urgency, 0.0)
        eta = estimate_eta_min(req, base.lat, base.lon, cruise_speed_kmh)
        table[site.name] = {
            "base": base.name,
            "distance_km": round(dist_km, 2),
            "eta_min": round(eta, 2),
            "meets_sla": can_meet_sla(req, eta),
        }
    return table
