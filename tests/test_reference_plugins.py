"""Regression tests for the three Plugin SDK reference implementations."""

from __future__ import annotations

import pytest

from examples.plugins import REFERENCE_PLUGIN_META
from examples.plugins.custom_drone_profile import (
    DRONE_PROFILE,
    get_profile,
    validate_profile,
)
from examples.plugins.kpi_widget import summarize_kpis
from examples.plugins.weather_source import sample_weather
from simulation.plugin_sdk import PluginRegistry, PluginType


def test_reference_metadata_registers_without_warnings() -> None:
    registry = PluginRegistry()
    for metadata in REFERENCE_PLUGIN_META:
        result = registry.register(metadata)
        assert result.is_valid
        assert result.errors == ()
        assert result.warnings == ()
    assert {meta.plugin_type for meta in registry.list_plugins()} == {
        PluginType.SENSOR,
        PluginType.CONTROLLER,
        PluginType.ANALYTICS,
    }


def test_weather_source_is_deterministic_and_bounded() -> None:
    first = sample_weather(100.0, -25.0, 80.0, 12.5)
    second = sample_weather(100.0, -25.0, 80.0, 12.5)
    assert first == second
    assert first.precipitation_mmph >= 0
    assert first.visibility_m >= 2_000
    with pytest.raises(ValueError):
        sample_weather(float("nan"), 0.0, 0.0, 0.0)


def test_custom_profile_is_immutable_and_validated() -> None:
    assert get_profile() is DRONE_PROFILE
    assert validate_profile(DRONE_PROFILE) == ()
    with pytest.raises(TypeError):
        DRONE_PROFILE["mass_kg"] = 1.0  # type: ignore[index]
    errors = validate_profile(
        {
            "profile_id": "",
            "mass_kg": 2.0,
            "max_speed_mps": -1,
            "max_climb_rate_mps": 2.0,
            "battery_wh": 100.0,
            "payload_kg": 3.0,
            "priority": 10,
        }
    )
    assert "payload_kg must be lower than mass_kg" in errors
    assert "priority must be an integer from 1 to 9" in errors


def test_kpi_widget_returns_immutable_summary() -> None:
    summary = summarize_kpis(
        {
            "stats": {
                "conflicts": 10,
                "near_misses": 2,
                "collisions": 1,
            },
            "drones": [{"battery": 80}, {"battery": 60}],
        }
    )
    assert summary["resolution_rate_pct"] == 90.0
    assert summary["average_battery_pct"] == 70.0
    with pytest.raises(TypeError):
        summary["conflicts"] = 0  # type: ignore[index]


@pytest.mark.parametrize("key", ["conflicts", "near_misses", "collisions"])
def test_kpi_widget_rejects_invalid_counters(key: str) -> None:
    with pytest.raises(ValueError, match=key):
        summarize_kpis(
            {
                "stats": {
                    "conflicts": 0,
                    "near_misses": 0,
                    "collisions": 0,
                    key: -1,
                },
                "drones": [],
            }
        )
