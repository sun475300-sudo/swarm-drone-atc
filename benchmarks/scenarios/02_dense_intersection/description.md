# 02 — Dense Intersection (standard, medium)

**One sentence:** 16 drones in 4 orthogonal streams converge on a single
intersection at the same time.

## Setup

```
       N stream (4)
            │
W stream ── + ── E stream
   (4)      │      (4)
       S stream (4)
```

All 16 spawn within a 5-second window with intersecting routes through
a 100 m × 100 m central conflict zone.

## Why it's in the suite

Tests **layer interaction under saturation**. Pure reactive layers
either deadlock or thrash; pure global layers solve in pre-compute and
fail to react to wind. SDACS hybrid is supposed to dominate here.

## Expected behavior

- ORCA: occasional brief MSD < 5 m as more than 2 drones interact.
- CBS: precomputed schedule succeeds but cannot adapt to gusts.
- SDACS hybrid: CBS plans the order, APF handles wind disturbance,
  Voronoi prevents thrash.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | ~8e-5 | < 5e-4 |
| MSD (m) | ~6.5 | ≥ 5 |
| PE | ~0.88 | ≥ 0.80 |
| MS (s) | ~145 | ≤ 200 |

## Failure modes to watch

- If MSD drops to 4-5 m: Voronoi reassignment lag; tighten the
  redistribution period.
- If PE drops below 0.80: detour cost runaway; check APF repulsion gain.
