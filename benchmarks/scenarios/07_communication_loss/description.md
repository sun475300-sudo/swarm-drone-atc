# 07 — Communication Loss (standard, hard)

**One sentence:** 12 drones operate under 30 % packet loss with two
total blackouts (30 s and 15 s) during the run.

## Setup

Comms have 30 % baseline packet loss. Two complete blackouts:

- t=60 → t=90 (30 s)
- t=180 → t=195 (15 s)

All drones must:

1. Detect the blackout within 2 s.
2. Enter a deterministic hold pattern.
3. Resume their mission within 5 s of comms restoration.

## Why it's in the suite

Tests **distributed-only fallback**. Centralized planners fail. APF +
local Voronoi must keep separation without the regulatory bus.

## Expected behavior

- ORCA / VO: keep operating reactively (no centralized layer to lose).
  But Network Remote ID fails during blackout → RID-CR drops.
- CBS: hard fail (cannot replan without comms).
- SDACS hybrid: regulatory layer detects blackout via heartbeat loss,
  switches to "comms-out hold," resumes after restoration.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | ~3e-4 | < 5e-4 |
| MSD (m) | ~5.5 | ≥ 5 |
| PE | ~0.71 | ≥ 0.65 |
| RID-CR | ≥ 0.85 | ≥ 0.85 (45 s of forced blackout pulls this down) |
| Hold-pattern failures | 0 | 0 |
