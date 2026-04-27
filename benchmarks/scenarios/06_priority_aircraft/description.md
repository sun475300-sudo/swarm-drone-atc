# 06 — Priority Aircraft Transit (standard, medium)

**One sentence:** 12 delivery drones operate normally; a manned
rotorcraft transits east-to-west across the entire airspace at t=90 s.

## Setup

A manned helicopter at 200 m altitude, 30 m/s ground speed, transits
the airspace from x=0 to x=2000 along y=1000. The regulatory feed
broadcasts the transit at t=60 s (30 s advance notice). All UAS must
maintain ≥ 150 m lateral separation from the corridor.

## Why it's in the suite

Tests **mixed-priority operations** — the bread-and-butter of urban
UTM. Manned aircraft always have right of way; the planner must
proactively clear a corridor without halting all UAS traffic.

## Expected behavior

- ORCA / VO: treat the helicopter as just a fast obstacle. Reactive
  layer fights rather than yielding.
- CBS: works if the manned aircraft is fed in advance as a moving
  high-priority obstacle.
- SDACS hybrid: regulatory layer creates a time-varying corridor
  exclusion; planner re-routes UAS in their current task without
  resetting their goals.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | 0.0 | < 1e-4 |
| MSD (m) | ~8.5 | ≥ 5 |
| PE | ~0.86 | ≥ 0.80 |
| Manned-aircraft clear violations | 0 | 0 |
