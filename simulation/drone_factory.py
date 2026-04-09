"""
다중 드론 타입 팩토리
====================
22종 드론 타입별 스펙 생성 + 성능 프리셋.

사용법:
    df = DroneFactory()
    drone = df.create("DELIVERY", drone_id="d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DroneSpec:
    """드론 사양"""
    drone_id: str
    drone_type: str
    max_speed_ms: float
    max_altitude_m: float
    battery_wh: float
    weight_kg: float
    payload_kg: float
    endurance_min: float
    sensors: list[str] = field(default_factory=list)


PRESETS: dict[str, dict[str, Any]] = {
    "DELIVERY": {"max_speed": 15, "max_alt": 120, "battery": 80, "weight": 2.5, "payload": 3.0, "endurance": 30, "sensors": ["GPS", "BARO"]},
    "AGRICULTURE": {"max_speed": 10, "max_alt": 50, "battery": 120, "weight": 8.0, "payload": 10.0, "endurance": 20, "sensors": ["GPS", "BARO", "NDVI"]},
    "FILMING": {"max_speed": 20, "max_alt": 150, "battery": 60, "weight": 1.5, "payload": 0.5, "endurance": 25, "sensors": ["GPS", "CAMERA", "GIMBAL"]},
    "SURVEILLANCE": {"max_speed": 18, "max_alt": 200, "battery": 100, "weight": 3.0, "payload": 1.0, "endurance": 45, "sensors": ["GPS", "CAMERA", "IR"]},
    "MEDICAL": {"max_speed": 25, "max_alt": 120, "battery": 90, "weight": 2.0, "payload": 2.0, "endurance": 20, "sensors": ["GPS", "BARO", "TEMP"]},
    "UAM_TAXI": {"max_speed": 40, "max_alt": 300, "battery": 500, "weight": 200, "payload": 300, "endurance": 30, "sensors": ["GPS", "LIDAR", "RADAR"]},
    "INSPECTION": {"max_speed": 8, "max_alt": 100, "battery": 50, "weight": 1.2, "payload": 0.3, "endurance": 35, "sensors": ["GPS", "CAMERA", "THERMAL"]},
    "MAPPING": {"max_speed": 12, "max_alt": 180, "battery": 70, "weight": 2.0, "payload": 0.5, "endurance": 40, "sensors": ["GPS", "LIDAR", "CAMERA"]},
    "CARGO": {"max_speed": 12, "max_alt": 100, "battery": 200, "weight": 15, "payload": 25, "endurance": 25, "sensors": ["GPS", "BARO"]},
    "RACING": {"max_speed": 50, "max_alt": 80, "battery": 30, "weight": 0.8, "payload": 0, "endurance": 8, "sensors": ["GPS"]},
    "SEARCH_RESCUE": {"max_speed": 20, "max_alt": 150, "battery": 110, "weight": 4.0, "payload": 2.0, "endurance": 35, "sensors": ["GPS", "IR", "SPEAKER"]},
    "RELAY": {"max_speed": 15, "max_alt": 200, "battery": 80, "weight": 1.5, "payload": 0.2, "endurance": 50, "sensors": ["GPS", "COMM"]},
}


class DroneFactory:
    """드론 팩토리."""

    def __init__(self) -> None:
        self._created: list[DroneSpec] = []
        self._custom_presets: dict[str, dict[str, Any]] = {}

    def create(self, drone_type: str, drone_id: str = "") -> DroneSpec:
        preset = self._custom_presets.get(drone_type) or PRESETS.get(drone_type)
        if not preset:
            preset = PRESETS["DELIVERY"]

        spec = DroneSpec(
            drone_id=drone_id or f"{drone_type}_{len(self._created)}",
            drone_type=drone_type,
            max_speed_ms=preset["max_speed"],
            max_altitude_m=preset["max_alt"],
            battery_wh=preset["battery"],
            weight_kg=preset["weight"],
            payload_kg=preset.get("payload", 0),
            endurance_min=preset.get("endurance", 30),
            sensors=list(preset.get("sensors", ["GPS"])),
        )
        self._created.append(spec)
        return spec

    def create_fleet(self, drone_type: str, count: int, prefix: str = "d") -> list[DroneSpec]:
        return [self.create(drone_type, f"{prefix}{i}") for i in range(count)]

    def add_preset(self, name: str, spec: dict[str, Any]) -> None:
        self._custom_presets[name] = spec

    def available_types(self) -> list[str]:
        return sorted(set(list(PRESETS.keys()) + list(self._custom_presets.keys())))

    def type_comparison(self, type_a: str, type_b: str) -> dict[str, Any]:
        a = PRESETS.get(type_a, {})
        b = PRESETS.get(type_b, {})
        if not a or not b:
            return {}
        return {
            "speed_ratio": a["max_speed"] / max(b["max_speed"], 1),
            "endurance_ratio": a.get("endurance", 30) / max(b.get("endurance", 30), 1),
            "payload_ratio": a.get("payload", 0) / max(b.get("payload", 0.1), 0.1),
        }

    def summary(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for s in self._created:
            type_counts[s.drone_type] = type_counts.get(s.drone_type, 0) + 1
        return {
            "total_created": len(self._created),
            "available_types": len(self.available_types()),
            "type_distribution": type_counts,
        }
