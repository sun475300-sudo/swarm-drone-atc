"""Deterministic synthetic weather-source plugin example."""

from __future__ import annotations

import math
from dataclasses import dataclass

from simulation.plugin_sdk import PluginMeta, PluginType

META = PluginMeta(
    name="reference-weather-source",
    version="1.0.0",
    author="SDACS Capstone Team",
    plugin_type=PluginType.SENSOR,
    description="Deterministic local wind and precipitation sample provider",
    entry_point="examples.plugins.weather_source:sample_weather",
)


@dataclass(frozen=True)
class WeatherSample:
    """One immutable weather observation in local ENU coordinates."""

    wind_east_mps: float
    wind_north_mps: float
    precipitation_mmph: float
    visibility_m: float


def sample_weather(
    east_m: float,
    north_m: float,
    altitude_m: float,
    time_s: float,
) -> WeatherSample:
    """Return a deterministic bounded sample without external network access."""

    values = (east_m, north_m, altitude_m, time_s)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("weather coordinates and time must be finite")
    phase = east_m * 0.0007 + north_m * 0.0003 + time_s * 0.01
    altitude_factor = min(max(altitude_m, 0.0), 300.0) / 300.0
    wind_east = 3.0 + math.sin(phase) * 1.5 + altitude_factor
    wind_north = 1.0 + math.cos(phase * 0.8) * 1.2
    precipitation = max(0.0, math.sin(phase * 0.25) * 2.0)
    visibility = max(2_000.0, 12_000.0 - precipitation * 1_500.0)
    return WeatherSample(
        wind_east_mps=round(wind_east, 3),
        wind_north_mps=round(wind_north, 3),
        precipitation_mmph=round(precipitation, 3),
        visibility_m=round(visibility, 1),
    )
