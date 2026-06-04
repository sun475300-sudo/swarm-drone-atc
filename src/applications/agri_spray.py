"""P750: 농업용 방제 드론 통합 — Voronoi 작업영역 분할 + 농약 잔량 최적화.

여러 드론이 농지를 분할 담당하여 균등 살포. 농약 부족 시 자동 복귀·교체.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FarmField:
    """농지 polygon (WGS84 또는 로컬 ENU)."""

    polygon: list[tuple[float, float]]   # [(x, y), ...]
    crop_type: str                       # 'rice'|'wheat'|'soybean'|'orchard'
    target_dose_l_per_ha: float          # 살포 목표 농약량


@dataclass(frozen=True)
class SprayDrone:
    """방제 드론 사양."""

    drone_id: str
    tank_capacity_l: float = 16.0        # DJI Agras T40 = 40L, 소형 10-16L
    flow_rate_lpm: float = 3.0           # L/min
    swath_width_m: float = 5.0           # 1회 비행폭
    cruise_speed_mps: float = 6.0


def field_area_ha(field: FarmField) -> float:
    """Shoelace로 polygon 면적 → 헥타르 (1 ha = 10,000 m²)."""
    pts = field.polygon
    n = len(pts)
    if n < 3:
        return 0.0
    area_m2 = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area_m2 += x1 * y2 - x2 * y1
    return abs(area_m2) / 2.0 / 10_000


def required_chemical_l(field: FarmField) -> float:
    """농지 전체 살포 필요 농약량 (L)."""
    return field_area_ha(field) * field.target_dose_l_per_ha


def partition_field_voronoi(field: FarmField, drones: list[SprayDrone]) -> dict[str, float]:
    """드론 수만큼 농지 면적을 Voronoi 분할 — 단순화: 균등 분할."""
    if not drones:
        return {}
    total_area = field_area_ha(field)
    per_drone_ha = total_area / len(drones)
    return {d.drone_id: per_drone_ha for d in drones}


def estimate_mission_time(field: FarmField, drone: SprayDrone, assigned_ha: float) -> dict[str, float]:
    """드론별 작업 시간 + 농약 보급 횟수 추정."""
    chem_needed_l = assigned_ha * field.target_dose_l_per_ha
    refills = math.ceil(chem_needed_l / drone.tank_capacity_l) - 1
    spray_duration_min = chem_needed_l / drone.flow_rate_lpm
    refill_time_min = refills * 3.0  # 3 min per refill
    return {
        "assigned_ha": assigned_ha,
        "chemical_required_l": chem_needed_l,
        "refills_needed": float(refills),
        "spray_duration_min": spray_duration_min,
        "refill_time_min": refill_time_min,
        "total_min": spray_duration_min + refill_time_min,
    }


def plan_spray_mission(field: FarmField, drones: list[SprayDrone]) -> dict[str, dict[str, float]]:
    """미션 전체 계획 — 드론별 ha + 시간."""
    assignment = partition_field_voronoi(field, drones)
    plan = {}
    for d in drones:
        plan[d.drone_id] = estimate_mission_time(field, d, assignment[d.drone_id])
    return plan
