"""드론 프로파일 — 기체별 성능 스펙"""
from dataclasses import dataclass


@dataclass
class DroneProfile:
    name: str
    max_speed_ms: float
    cruise_speed_ms: float
    max_altitude_m: float
    battery_wh: float
    endurance_min: float
    comm_range_m: float
    priority: int               # 낮을수록 높은 우선순위


DRONE_PROFILES: dict[str, DroneProfile] = {
    "COMMERCIAL_DELIVERY": DroneProfile(
        name="상업 배송", max_speed_ms=15.0, cruise_speed_ms=10.0,
        max_altitude_m=120.0, battery_wh=80.0, endurance_min=30.0,
        comm_range_m=2000.0, priority=2,
    ),
    "SURVEILLANCE": DroneProfile(
        name="감시 정찰", max_speed_ms=20.0, cruise_speed_ms=12.0,
        max_altitude_m=120.0, battery_wh=100.0, endurance_min=45.0,
        comm_range_m=3000.0, priority=2,
    ),
    "EMERGENCY": DroneProfile(
        name="응급", max_speed_ms=25.0, cruise_speed_ms=20.0,
        max_altitude_m=120.0, battery_wh=60.0, endurance_min=20.0,
        comm_range_m=2000.0, priority=1,
    ),
    "RECREATIONAL": DroneProfile(
        name="레저", max_speed_ms=10.0, cruise_speed_ms=5.0,
        max_altitude_m=120.0, battery_wh=30.0, endurance_min=15.0,
        comm_range_m=500.0, priority=3,
    ),
}
