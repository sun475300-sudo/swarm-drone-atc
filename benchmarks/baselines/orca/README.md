# Baseline: ORCA — Reciprocal n-body Collision Avoidance

**Reference:** van den Berg, J., Guy, S. J., Lin, M., & Manocha, D.
(2011). *Reciprocal n-body Collision Avoidance.* ISRR 2011.

**License:** Apache 2.0 (RVO2 official implementation)

## What it is

ORCA represents each pairwise interaction as a half-plane velocity
constraint. Each agent solves a low-dimensional linear program every
tick to find the velocity closest to its preferred velocity that
satisfies all pairwise constraints.

Pure ORCA has **no concept of**:

- Global path planning (it's purely reactive).
- Geofences, no-fly zones, or any regulatory constraint.
- Priority handling (manned aircraft, emergencies).
- Communication failures (it assumes perfect velocity sharing).

These gaps drive the SDACS hybrid contribution claim — ORCA covers
*one* of the three SDACS layers.

## Adapter contract

Implement `benchmarks/baselines/orca/adapter.py` (Protocol shown below)
to plug ORCA into the SDACS scenario runner.

```python
from typing import Protocol
from src.analytics.types import SimulationTrace

class BaselineAdapter(Protocol):
    """Run a planner on a scenario and return a SimulationTrace."""

    name: str  # e.g. "orca"

    def __init__(self, scenario_manifest: dict, seed: int) -> None: ...

    def run(self) -> SimulationTrace:
        """Execute the scenario; return a fully-populated trace."""
        ...
```

## Recommended implementation

Use the `rvo2` Python bindings (PyPI: `rvo2`):

```bash
pip install rvo2==0.2.4
```

The adapter (~100 lines) maps:

- `manifest.agents.kinematics.max_speed_m_s` → `RVOSimulator.setMaxSpeed`
- `manifest.agents.count` × spawn pattern → `addAgent` calls
- `manifest.dt_seconds` → `RVOSimulator.setTimeStep`
- per-tick: `setAgentPrefVelocity` (toward goal), `doStep`, record positions

## Known limitations against this benchmark suite

| Scenario | Expected ORCA outcome |
|----------|----------------------|
| 01 corridor | ✅ pass |
| 02 dense | ⚠️ MSD likely < 5 m at peak |
| 03 emergency | ❌ no priority concept |
| 04 NFZ | ❌ no geofence concept |
| 05 weather | ⚠️ wind disturbance not modeled |
| 06 priority | ❌ helicopter ignored |
| 07 comms | ⚠️ assumes perfect velocity sharing |
| 08 stress density | ⚠️ O(N²) scaling concern |
| 09 failure cascade | ❌ bricked drones cause MSD violations |
| 10 adversarial | ⚠️ panics on intruders |

These gaps are the **point**. The SDACS paper's table 1 shows where
each layer pulls its weight.
