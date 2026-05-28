# weather_disturbance Smoke Run — 2026-05-18

**Phase reference:** ADDITIONAL_WORK_PLAN_2026-05-15 → P1-3
**Scope:** Re-record `weather_disturbance` smoke run after the 2026-05-15 environment
fixes. Earlier `data/pipeline/sdacs_report_*` artifacts from 2026-04-08 contained
`"error": "No module named 'simpy'"` for every scenario — those are not
representative of current behavior and should be treated as stale.

---

## Run configuration

| Field | Value |
| ----- | ----- |
| Command | `python main.py scenario weather_disturbance --runs 1 --seed 42` |
| Scenario id | `s06_weather_disturbance` |
| Drone count | 100 |
| Simulated duration | 600.0 s |
| Wind models | constant (5 m/s @ 270°), variable (mean 10 m/s gust 15 m/s), shear (5→20 m/s @ 60 m) |
| simpy version | 4.1.1 |
| Host | Windows 11, CPU-default path (`SDACS_ENABLE_TORCH` unset) |

The `variable` wind model exceeds 10 m/s on gusts, which exercises the APF
windy-parameter switch documented in `CLAUDE.md` (`>10 m/s → APF_PARAMS_WINDY`).

---

## Headline numbers

| Metric | Value |
| ------ | ----- |
| Wall clock | 67.6 s |
| Real-time factor | ~8.88x (600.0 / 67.6) |
| Conflicts total | 1,932 |
| Advisories issued | 479 |
| Collisions | 12 |
| Near-misses | 54 |
| Conflict resolution rate | **99.38 %** |
| Route efficiency (mean) | 1.059 |
| Route efficiency (max) | 4.520 |
| Total flight time | 58,728.1 drone-s |
| Total distance | 551.5 km |
| Energy efficiency | 375.65 Wh/km |
| Clearances approved / denied | 65 / 63 |
| CBS attempts / successes | 14 / 14 (100 %) |
| A* fallbacks | 47 |
| Comm messages delivered | 120,636 / 120,636 (0 drops) |
| Advisory latency p50 / p99 | 0.0 / 0.0 |
| Effective seed (after derivation) | 191664964 |

The conflict-resolution-rate formula used here is
`1 − collisions / (conflicts + collisions)` per CLAUDE.md — for this run that
gives `1 − 12 / (1932 + 12) = 0.9938`.

---

## Interpretation

- **Engine and CPU-default path are healthy.** A 600 s, 100-drone wind-stressed
  run finishes in ~68 s wall clock with no crash, no comms drops, and 100 % CBS
  success rate.
- **Wind regime triggers the expected stress.** 12 collisions and 54 near-misses
  under combined constant + gust + shear winds is consistent with prior
  qualitative observations — the gust model (15 m/s) reliably crosses the windy
  APF threshold.
- **The route-efficiency max of 4.52 is high** and indicates at least one drone
  took a path more than 4× the straight-line distance to its goal. Worth a
  follow-up to see whether this is concentrated in shear-zone transitions.

---

## What this run does *not* establish

- This is a single seed (42). For paper-grade claims use the 30-seed protocol in
  `config/seeds.yaml` and report mean ± 95 % CI.
- The benchmark suite scenario for weather is
  `benchmarks/scenarios/05_weather_diversion/`, which is a **different**
  scenario from `config/scenario_params/weather_disturbance.yaml`. Do not
  conflate the two when citing numbers. This memo is about the latter.
- Memory/peak-RSS not measured here.

---

## Follow-ups

- [ ] Run 30-seed weather_disturbance sweep and append summary to this memo
- [ ] Investigate the route_efficiency_max = 4.52 outlier (which drone, where in
      the wind field, which timestep)
- [ ] Cross-check that the 12 collisions cluster in the shear-transition zone
      (60 m altitude band) — if so, link to a known limitation in
      `docs/AUDIT_2026-04-20.md`
- [ ] Delete or annotate the stale 2026-04-08
      `data/pipeline/sdacs_report_*.json` records that show every scenario as
      `simpy missing` — they are misleading if a future reader trusts them

---

*Authored after the 2026-05-15 ADDITIONAL_WORK_PLAN tracked P1-3 as open.
This memo discharges the "weather_disturbance 포함 smoke run 재기록" item.*
