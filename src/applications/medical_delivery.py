"""P751: 도서·산간 의료 배송 — 응급 의약품 우선순위 운영."""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import Enum


class Urgency(Enum):
    """배송 우선순위."""

    LIFE_THREATENING = 0   # 심정지·과민성 쇼크 (5분 이내)
    CRITICAL = 1           # 출혈·뇌졸중 (15분)
    URGENT = 2             # 외상·고열 (30분)
    NORMAL = 3             # 정기 처방 (수 시간 가능)


@dataclass(frozen=True)
class DeliveryRequest:
    """배송 요청."""

    request_id: str
    medication: str
    urgency: Urgency
    destination_lat: float
    destination_lon: float
    requested_ts: float
    payload_kg: float = 0.5


@dataclass
class DeliveryQueue:
    """우선순위 큐 — heap (urgency, ts)."""

    _heap: list[tuple[int, float, str]] = field(default_factory=list)
    _registry: dict[str, DeliveryRequest] = field(default_factory=dict)

    def enqueue(self, req: DeliveryRequest) -> None:
        """요청 등록."""
        heapq.heappush(self._heap, (req.urgency.value, req.requested_ts, req.request_id))
        self._registry[req.request_id] = req

    def dequeue(self) -> DeliveryRequest | None:
        """가장 긴급한 요청 반환."""
        while self._heap:
            _, _, rid = heapq.heappop(self._heap)
            if rid in self._registry:
                return self._registry.pop(rid)
        return None

    def __len__(self) -> int:
        return len(self._registry)

    def peek(self) -> DeliveryRequest | None:
        """다음 요청 (제거하지 않음)."""
        while self._heap:
            _, _, rid = self._heap[0]
            if rid in self._registry:
                return self._registry[rid]
            heapq.heappop(self._heap)
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 지점 거리 (km, 구면 근사)."""
    import math
    r_earth = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * r_earth * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_eta_min(
    req: DeliveryRequest,
    base_lat: float,
    base_lon: float,
    cruise_speed_kmh: float = 60.0,
) -> float:
    """ETA 추정 — 직선 거리 / 순항 속도 + 5분 (이착륙 마진)."""
    distance = haversine_km(base_lat, base_lon, req.destination_lat, req.destination_lon)
    flight_min = distance / cruise_speed_kmh * 60
    return flight_min + 5.0


def can_meet_sla(req: DeliveryRequest, eta_min: float) -> bool:
    """긴급도 SLA 충족 여부."""
    sla_min = {
        Urgency.LIFE_THREATENING: 10.0,  # ETA 5min 비현실, 10min 최선
        Urgency.CRITICAL: 20.0,
        Urgency.URGENT: 40.0,
        Urgency.NORMAL: 240.0,
    }
    return eta_min <= sla_min[req.urgency]
