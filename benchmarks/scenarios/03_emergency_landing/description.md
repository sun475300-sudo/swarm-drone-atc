# 03 — Emergency Landing (standard, medium)

**One sentence:** 8 delivery drones operate normally; at t=60 s, one
declares an emergency and must land immediately while the rest yield.

## Setup

8 drones doing routine point-to-point deliveries. At t=60 s, drone 03
sends a `PAN_PAN` priority message and dives toward the nearest safe
landing site at (500, 500, 0).

The system must:

1. Within 15 s, push all other drones out of a 50 m horizontal radius
   around the landing site.
2. Hold them clear until the emergency drone touches down.
3. Resume normal traffic flow after.

## Why it's in the suite

Tests **priority handoff** — the regulatory layer (which carries
priority codes) must override the planning layer's optimization.
Realistic: this is exactly the FAA Part 107 emergency procedure.

## Expected behavior

- ORCA / VO: no concept of priority; drones treat the emergency drone
  as just another agent. Likely fails the clearance criterion.
- CBS: requires re-planning trigger; without one, fails.
- SDACS hybrid: regulatory priority bus broadcasts PAN_PAN; planner
  re-runs CBS with the landing site as a hard exclusion zone.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | ~2e-5 | < 1e-4 |
| MSD (m) | ~9 | ≥ 5 |
| PE | ~0.91 | ≥ 0.85 |
| Emergency clearance time | ~10 s | ≤ 15 s |

## Failure modes to watch

- If clearance time > 15 s: priority bus latency too high.
- If MSD < 5 m during the panic re-route: APF gain doesn't scale with
  the urgency of the avoidance.
