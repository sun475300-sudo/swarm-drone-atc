# 04 — No-Fly Zone (standard, medium)

**One sentence:** 8 drones must reach goals on the opposite side of a
hard-no-entry geofence; the shortest path passes straight through it.

## Setup

A 300 × 300 m square geofence sits in the middle of the airspace. All
8 drones spawn on one side with goals on the opposite side. Their
straight-line shortest path crosses the geofence.

## Why it's in the suite

Tests **regulatory hard constraint**. Many planners "almost" respect
geofences — clip a corner, brush an edge — and that is exactly what is
banned in real LAANC operations. Zero tolerance.

## Expected behavior

- ORCA / VO: no concept of geofence. **Likely fail** the geofence
  violation criterion.
- CBS: handles as static obstacle if pre-fed. Pass.
- SDACS hybrid: regulatory layer pushes geofence to the planning
  layer's obstacle set. Pass with predictable detour cost.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | 0.0 | < 1e-4 |
| MSD (m) | ~11 | ≥ 5 |
| PE | ~0.82 | ≥ 0.75 |
| Geofence violations | 0 | 0 |
