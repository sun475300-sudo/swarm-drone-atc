# 05 — Weather Diversion (standard, hard)

**One sentence:** 12 drones must deliver under wind and rain while a
storm cell crosses the airspace diagonally over 5 minutes.

## Setup

12 drones doing point-to-point deliveries. A 200 m radius storm cell
moves linearly from (200, 200) to (1300, 1300) over the 300 s horizon
— effectively a moving no-fly zone. Wind 8 m/s ± 4 m/s gusts. Rain
6 mm/h. Visibility 5 km. Comms have 5% packet loss.

## Why it's in the suite

Tests **dynamic re-planning under environmental disturbance**. This is
the most common cause of UTM diversions in real operations.

## Expected behavior

- ORCA / VO: no concept of moving NFZ. Likely violate.
- CBS: precompute fails — storm cell trajectory must be input as
  time-varying constraint, which classical CBS doesn't handle.
- SDACS hybrid: weather feed → regulatory layer → planner replans
  every 30 s. APF handles wind disturbance.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | ~1.5e-4 | < 5e-4 |
| MSD (m) | ~6 | ≥ 5 |
| PE | ~0.74 | ≥ 0.65 |
| Storm-cell violations | 0 | 0 |
| RID-CR | ≥ 0.99 | ≥ 0.99 (degraded comms) |
