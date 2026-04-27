# 10 — Stress: Adversarial Swarm (stress, hard)

**One sentence:** 30 cooperative SDACS drones operating; 8
non-cooperative intruders (ignoring Remote ID and conflict resolution)
appear at t=60 s and random-walk through the volume.

## Setup

- **Cooperative side:** 30 SDACS-controlled drones doing routine
  deliveries.
- **Intruder side:** 8 non-cooperative drones appear at t=60 s, ignore
  Remote ID broadcasts, ignore reciprocal conflict resolution, and
  random-walk through the volume at 12 m/s.

The cooperative side must avoid intruders defensively (intruders can
be detected via radar / vision but not via cooperative comms).

## Why it's in the suite

Tests **robustness against non-cooperators**. This is realistic: lost
hobbyist drones, unauthorized incursions, even bird strikes appear as
non-cooperative obstacles in real operations.

## Ethics note

The intruder model is intentionally **defensive only** — we do not
include scenarios involving counter-swarm hostilities or interception
of crewed aircraft. See `DATASET_CARD.md` ethical considerations.

## Expected behavior

- ORCA / VO: treat intruders as fast-moving obstacles. Reactive layer
  may panic.
- CBS: cannot precompute against random-walk intruders.
- SDACS hybrid: detection layer (radar / vision proxy) feeds intruder
  trajectories to APF; CBS does not re-plan (intruders are too fast),
  reactive layer does the work.

## Expected ranges (SDACS hybrid)

| Metric | Expected | Hard floor |
|--------|----------|-----------|
| NMR | ~1.2e-3 | < 2e-3 |
| MSD (m) | ~4.5 | ≥ 4.0 |
| PE | ~0.68 | ≥ 0.60 |
| Cooperative-cooperative collisions | 0 | 0 |
