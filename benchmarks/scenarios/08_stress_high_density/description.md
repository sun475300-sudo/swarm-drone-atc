# 08 — Stress: High Density (stress, hard)

**One sentence:** 200 drones in 1 km³ — the operational ceiling claim.

## Setup

200 drones spawn uniformly inside a 1000 × 1000 × 100 m volume with
random goals inside the same volume. They must reach goals while
maintaining 5 m separation. No obstacles, no weather — the only
challenge is *density*.

## Why it's in the suite

Tests the **scaling claim** ("RTF ≥ 5 at N=100" from EVALUATION_METRICS
§5.1) at twice the headline N. Below 5 means real-time operation
breaks down at this density.

## Expected behavior

- ORCA / VO: reactive computation O(N²) per tick → degrades.
- CBS: combinatorial explosion — likely cannot solve in horizon.
- SDACS hybrid: Voronoi partitioning makes APF local. CBS runs only on
  per-cell sub-problems.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | ~4.5e-4 | < 1e-3 |
| MSD (m) | ~5.0 | ≥ 4.5 |
| PE | ~0.79 | ≥ 0.70 |
| RTF | ≥ 5.5 | ≥ 5.0 |
