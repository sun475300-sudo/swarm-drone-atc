"""Reference plugins for the SDACS Plugin SDK."""

from .custom_drone_profile import META as CUSTOM_DRONE_META
from .kpi_widget import META as KPI_WIDGET_META
from .weather_source import META as WEATHER_SOURCE_META

REFERENCE_PLUGIN_META = (
    WEATHER_SOURCE_META,
    CUSTOM_DRONE_META,
    KPI_WIDGET_META,
)

__all__ = [
    "CUSTOM_DRONE_META",
    "KPI_WIDGET_META",
    "REFERENCE_PLUGIN_META",
    "WEATHER_SOURCE_META",
]
