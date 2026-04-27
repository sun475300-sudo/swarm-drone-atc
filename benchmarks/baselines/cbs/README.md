# Baseline: CBS — Conflict-Based Search (Sharon et al. 2015)

**Reference:** Sharon, G., Stern, R., Felner, A., & Sturtevant, N. R.
(2015). *Conflict-based search for optimal multi-agent pathfinding.*
Artificial Intelligence, 219, 40-66.
[doi:10.1016/j.artint.2014.11.006](https://doi.org/10.1016/j.artint.2014.11.006)

**License:** Re-implement from paper.

## What it is

CBS is a two-level search algorithm:

1. **High level:** A binary tree of conflict-resolution constraints.
   Each node is a set of (agent, location, time) prohibitions.
2. **Low level:** A single-agent A* on the time-expanded graph,
   respecting the high-level constraints.

CBS finds a sum-of-costs optimal solution for static-obstacle MAPF.

## What CBS is not

- **Not real-time.** Re-planning takes > 1 s on 10+ agents at our
  airspace resolution.
- **Not adaptive.** Cannot react to dynamic obstacles (storms, intruders)
  without restarting the whole search.
- **No regulatory layer.** Geofences are static obstacles, but
  emergencies, priority aircraft, and Remote ID are out of scope.

## Adapter contract

Same `BaselineAdapter` Protocol as `../orca/README.md`. Implement
`benchmarks/baselines/cbs/adapter.py`.

## Recommended implementation

Use the existing `src/airspace_control/planning/cbs.py` (already in
SDACS) but with `regulatory_constraints=None` and
`reactive_layer=None` to isolate the planning layer. Treat CBS as the
"global only" baseline.

For non-SDACS researchers wanting a clean reference, the
`libMultiRobotPlanning` C++ implementation from TU Berlin is a clean
external option.

## Known limitations against this benchmark suite

| Scenario | Expected CBS outcome |
|----------|---------------------|
| 01 corridor | ✅ optimal — 2 s offset |
| 02 dense | ✅ optimal but slow re-plan if perturbed |
| 03 emergency | ⚠️ requires re-plan trigger from outside |
| 04 NFZ | ✅ static obstacle, easy |
| 05 weather | ❌ moving obstacle not natively supported |
| 06 priority | ⚠️ requires re-plan trigger |
| 07 comms | ❌ centralized planner cannot operate without comms |
| 08 stress density | ❌ combinatorial explosion at N=200 |
| 09 failure cascade | ❌ each failure requires re-plan |
| 10 adversarial | ❌ random-walk intruders break CBS assumptions |

Use CBS to demonstrate that "global planning alone" is fragile in the
real-world scenarios that the hybrid architecture handles.
