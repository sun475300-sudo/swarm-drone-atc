# 01 — Corridor Crossing (standard, easy)

**One sentence:** Two streams of 2 drones each fly toward each other along
parallel corridors that cross once at 90°.

## Setup

```
       N
       │
   ◀── + ──▶
       │
       S
```

- 2 drones spawn at the **west** edge with goals on the east edge.
- 2 drones spawn at the **east** edge with goals on the west edge.
- Their cruise altitudes differ by 0 m (same level) — pure horizontal
  conflict.

## Why it's in the suite

This is the canonical sanity check. A planner that fails this fails
everything. It's the first scenario CI runs and the one debug logs
default to.

## Expected behavior

- ORCA / VO: solve via reciprocal velocity adjustment, slight detour.
- CBS: assigns a 2-second time offset, no spatial detour.
- SDACS hybrid: APF resolves locally without invoking the global layer.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | 0.0 | < 1e-4 |
| MSD (m) | ~12 | ≥ 5 |
| PE | ~0.96 | ≥ 0.85 |
| MS (s) | ~78 | ≤ 120 |

## Failure modes to watch

- If MSD drops below 5 m: APF gain too low or CPA lookahead too short.
- If MS spikes above 100 s: layer dispatching overhead — profile.
