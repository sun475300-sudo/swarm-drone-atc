# 09 — Stress: Failure Cascade (stress, hard)

**One sentence:** 40 drones operating; at t=50, 10 % lose control;
at t=120, an additional 5 % brick mid-flight.

## Setup

40 drones doing routine deliveries. Two failure injections:

- **t=50 s:** 10 % lose control authority. They keep broadcasting
  Remote ID but drift with the wind (5 m/s × t).
- **t=120 s:** Additional 5 % "brick" — they freeze in their current
  position and stop broadcasting. Other drones must treat them as
  silent obstacles.

Wind is 5 m/s ± 2 m/s gust crosswind, so drifting drones move
unpredictably across the airspace.

## Why it's in the suite

Tests **graceful degradation**. Real-world swarms lose 1-3 % of
drones per mission to battery / GPS / motor failures. The system must
not let a failure trigger a cascade.

## Expected behavior

- ORCA / VO: handles drifting drones as moving obstacles. Bricked
  drones (no broadcast) cause MSD violations.
- CBS: re-plan trigger required for each failure. Slow.
- SDACS hybrid: regulatory layer detects loss-of-broadcast within 5 s,
  inserts a static obstacle at the last known position; planner
  re-routes affected agents.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | ~6e-4 | < 1e-3 |
| MSD (m) | ~5.0 | ≥ 4.5 |
| PE | ~0.73 | ≥ 0.65 |
| Cascading failures | 0 | 0 |
