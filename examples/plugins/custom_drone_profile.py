"""Custom drone-profile plugin example with explicit boundary validation."""

from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType

from simulation.plugin_sdk import PluginMeta, PluginType

META = PluginMeta(
    name="reference-medical-drone",
    version="1.0.0",
    author="SDACS Capstone Team",
    plugin_type=PluginType.CONTROLLER,
    description="Validated medical-delivery multirotor profile",
    entry_point="examples.plugins.custom_drone_profile:get_profile",
)

_PROFILE = {
    "profile_id": "medical-delivery-x8",
    "mass_kg": 18.5,
    "max_speed_mps": 22.0,
    "max_climb_rate_mps": 5.0,
    "battery_wh": 1_800.0,
    "payload_kg": 5.0,
    "priority": 2,
}
DRONE_PROFILE: Mapping[str, object] = MappingProxyType(_PROFILE)


def validate_profile(profile: Mapping[str, object]) -> tuple[str, ...]:
    """Return sorted validation errors; an empty tuple means valid."""

    errors: list[str] = []
    profile_id = profile.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id.strip():
        errors.append("profile_id must be a non-empty string")
    for field in (
        "mass_kg",
        "max_speed_mps",
        "max_climb_rate_mps",
        "battery_wh",
        "payload_kg",
    ):
        value = profile.get(field)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            errors.append(f"{field} must be a finite positive number")
    priority = profile.get("priority")
    if not isinstance(priority, int) or isinstance(priority, bool) or not 1 <= priority <= 9:
        errors.append("priority must be an integer from 1 to 9")
    mass = profile.get("mass_kg")
    payload = profile.get("payload_kg")
    if isinstance(mass, (int, float)) and isinstance(payload, (int, float)) and payload >= mass:
        errors.append("payload_kg must be lower than mass_kg")
    return tuple(sorted(errors))


def get_profile() -> Mapping[str, object]:
    """Return the immutable validated reference profile."""

    errors = validate_profile(DRONE_PROFILE)
    if errors:
        raise RuntimeError(f"invalid bundled profile: {errors}")
    return DRONE_PROFILE
