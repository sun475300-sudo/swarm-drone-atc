# Reference Plugins

Three dependency-free examples exercise the public metadata contract in
`simulation/plugin_sdk.py`:

| Plugin | Type | Entry point |
|---|---|---|
| Deterministic weather source | `SENSOR` | `weather_source:sample_weather` |
| Medical-delivery drone profile | `CONTROLLER` | `custom_drone_profile:get_profile` |
| Safety KPI adapter | `ANALYTICS` | `kpi_widget:summarize_kpis` |

```python
from examples.plugins import REFERENCE_PLUGIN_META
from simulation.plugin_sdk import PluginRegistry

registry = PluginRegistry()
for metadata in REFERENCE_PLUGIN_META:
    assert registry.register(metadata).is_valid
```

These are contract examples, not dynamically loaded third-party code. A
production plugin host must add isolation, capability permissions, signatures,
and resource limits before executing untrusted plugins.
