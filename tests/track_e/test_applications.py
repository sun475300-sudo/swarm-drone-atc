"""P750 농업 + P751 의료 배송 단위 검증."""
from __future__ import annotations

import pytest

from src.applications.agri_spray import (
    FarmField,
    SprayDrone,
    estimate_mission_time,
    field_area_ha,
    partition_field_voronoi,
    plan_spray_mission,
    required_chemical_l,
)
from src.applications.medical_delivery import (
    DeliveryQueue,
    DeliveryRequest,
    Urgency,
    can_meet_sla,
    estimate_eta_min,
    haversine_km,
)


# ─── Agri ────────────────────────────────────────────

def test_square_field_area_1ha() -> None:
    """100m × 100m square = 1 ha."""
    f = FarmField(
        polygon=[(0, 0), (100, 0), (100, 100), (0, 100)],
        crop_type="rice",
        target_dose_l_per_ha=3.0,
    )
    assert field_area_ha(f) == pytest.approx(1.0, rel=0.01)


def test_required_chemical_proportional() -> None:
    """면적 × dose."""
    f = FarmField(
        polygon=[(0, 0), (200, 0), (200, 100), (0, 100)],   # 2 ha
        crop_type="wheat",
        target_dose_l_per_ha=2.5,
    )
    assert required_chemical_l(f) == pytest.approx(5.0, rel=0.01)


def test_partition_even() -> None:
    """3 드론 균등 분할."""
    f = FarmField(polygon=[(0, 0), (300, 0), (300, 100), (0, 100)], crop_type="rice", target_dose_l_per_ha=3.0)
    drones = [SprayDrone(drone_id=f"DR-{i}") for i in range(3)]
    p = partition_field_voronoi(f, drones)
    assert len(p) == 3
    assert all(abs(v - 1.0) < 0.01 for v in p.values())


def test_mission_time_includes_refills() -> None:
    """16L 탱크로 60L 살포 → 3-4 보급."""
    f = FarmField(polygon=[(0, 0), (1000, 0), (1000, 200), (0, 200)],  # 20 ha
                  crop_type="soybean", target_dose_l_per_ha=3.0)
    drone = SprayDrone(drone_id="DR-1", tank_capacity_l=16.0)
    t = estimate_mission_time(f, drone, assigned_ha=20.0)
    assert t["refills_needed"] >= 2
    assert t["total_min"] > t["spray_duration_min"]


def test_plan_mission_returns_per_drone() -> None:
    f = FarmField(polygon=[(0, 0), (200, 0), (200, 100), (0, 100)], crop_type="rice", target_dose_l_per_ha=3.0)
    drones = [SprayDrone(drone_id=f"DR-{i}") for i in range(2)]
    plan = plan_spray_mission(f, drones)
    assert set(plan.keys()) == {"DR-0", "DR-1"}
    assert all("total_min" in v for v in plan.values())


# ─── Medical ────────────────────────────────────────

def test_haversine_known_distance() -> None:
    """서울 ↔ 인천 ≈ 30km."""
    d = haversine_km(37.5665, 126.9780, 37.4563, 126.7052)
    assert 25 < d < 35


def test_priority_queue_orders_by_urgency() -> None:
    q = DeliveryQueue()
    normal = DeliveryRequest("R1", "aspirin", Urgency.NORMAL, 37.5, 127.0, 100.0)
    crit = DeliveryRequest("R2", "epi_pen", Urgency.LIFE_THREATENING, 37.5, 127.0, 101.0)
    q.enqueue(normal)
    q.enqueue(crit)
    first = q.dequeue()
    assert first is not None
    assert first.request_id == "R2"


def test_queue_len_and_peek() -> None:
    q = DeliveryQueue()
    q.enqueue(DeliveryRequest("R1", "x", Urgency.URGENT, 37.5, 127.0, 100.0))
    assert len(q) == 1
    p = q.peek()
    assert p is not None and p.request_id == "R1"
    assert len(q) == 1   # peek doesn't remove


def test_eta_estimation() -> None:
    req = DeliveryRequest("R1", "x", Urgency.CRITICAL, 37.6, 127.1, 0.0)
    eta = estimate_eta_min(req, base_lat=37.5, base_lon=127.0, cruise_speed_kmh=60.0)
    assert eta > 5.0   # base 5 min margin


def test_sla_critical_within_20min() -> None:
    """CRITICAL은 ETA 20분 이내 만족."""
    req = DeliveryRequest("R1", "x", Urgency.CRITICAL, 37.5, 127.0, 0.0)
    assert can_meet_sla(req, eta_min=15.0)
    assert not can_meet_sla(req, eta_min=25.0)


def test_sla_life_threatening_strict() -> None:
    """LIFE_THREATENING은 10분 SLA."""
    req = DeliveryRequest("R1", "epi_pen", Urgency.LIFE_THREATENING, 37.5, 127.0, 0.0)
    assert can_meet_sla(req, eta_min=8.0)
    assert not can_meet_sla(req, eta_min=12.0)
