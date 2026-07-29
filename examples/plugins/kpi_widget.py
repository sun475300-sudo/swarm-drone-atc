"""KPI widget data adapter plugin example."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from simulation.plugin_sdk import PluginMeta, PluginType

META = PluginMeta(
    name="reference-safety-kpi",
    version="1.0.0",
    author="SDACS Capstone Team",
    plugin_type=PluginType.ANALYTICS,
    description="Collision-resolution and fleet-health KPI adapter",
    entry_point="examples.plugins.kpi_widget:summarize_kpis",
)


def _non_negative_int(stats: Mapping[str, object], key: str) -> int:
    value = stats.get(key, 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value


def summarize_kpis(snapshot: Mapping[str, object]) -> Mapping[str, float | int]:
    """Convert a telemetry snapshot into immutable reader-facing KPI values."""

    stats = snapshot.get("stats", {})
    drones = snapshot.get("drones", ())
    if not isinstance(stats, Mapping):
        raise ValueError("snapshot.stats must be a mapping")
    if not isinstance(drones, (list, tuple)):
        raise ValueError("snapshot.drones must be a list or tuple")

    conflicts = _non_negative_int(stats, "conflicts")
    collisions = _non_negative_int(stats, "collisions")
    near_misses = _non_negative_int(stats, "near_misses")
    resolved = max(0, conflicts - collisions)
    resolution_rate = 100.0 if conflicts == 0 else resolved / conflicts * 100.0
    batteries = [
        float(drone["battery"])
        for drone in drones
        if isinstance(drone, Mapping)
        and isinstance(drone.get("battery"), (int, float))
    ]
    average_battery = sum(batteries) / len(batteries) if batteries else 0.0
    return MappingProxyType(
        {
            "fleet_size": len(drones),
            "conflicts": conflicts,
            "near_misses": near_misses,
            "collisions": collisions,
            "resolution_rate_pct": round(resolution_rate, 2),
            "average_battery_pct": round(average_battery, 2),
        }
    )
