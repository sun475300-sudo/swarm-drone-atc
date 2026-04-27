# Dataset Card — SDACS Benchmark Suite v1.0

> Following the Hugging Face / Papers With Code dataset card template.

---

## Dataset summary

The SDACS Benchmark Suite is a small, hand-designed set of 10 scenarios
for evaluating multi-drone airspace control systems. Unlike datasets in
the supervised-learning sense, this is a **scenario specification** —
each scenario tells a simulator what to set up, and the "data" produced
is a tuple of metric values from running a planner on that scenario.

- **10 scenarios:** 7 standard + 3 stress
- **Each scenario:** spec'd by a `manifest.yaml` (~30-60 lines) +
  human-readable `description.md`
- **Reproduction model:** simulator runs the scenario; reviewer reports
  14 metrics from `EVALUATION_METRICS.md`
- **License:** CC-BY-4.0 (you may modify, fork, redistribute with
  attribution)

---

## Composition

| Split | # scenarios | Purpose |
|-------|-------------|---------|
| standard | 7 | Cover orthogonal axes literature conflates |
| stress | 3 | Push past standard envelope (density / failures / adversaries) |

Each scenario specifies:

- **Agents:** number, kinematic limits, start/goal positions, mission types
- **Airspace:** 3D bounds, geofences, no-fly zones
- **Obstacles:** static (terrain, towers) and dynamic (storm cells, birds)
- **Weather:** wind profile, visibility, precipitation
- **Communications:** quality, packet-loss model, blackout windows
- **Regulatory context:** Remote-ID requirement, LAANC volume class
- **Success criteria:** thresholds on metrics that define "passed"
- **Expected baseline performance:** SDACS hybrid current numbers
  (refreshed by CI; lets you spot regressions instantly)

---

## Curation rationale

Scenarios were chosen to cover the four axes literature typically
collapses into a single "complexity" knob:

1. **Conflict topology:** crossings, intersections, head-ons (sc 01-02)
2. **Priority and exception handling:** emergencies, manned aircraft (sc 03, 06)
3. **Environmental disturbance:** weather, no-fly geofences (sc 04-05)
4. **Degraded operations:** comms loss, failure cascades (sc 07, 09)

Stress scenarios (08-10) hold the topology fixed and crank one variable
to the operational ceiling.

**Selection bias:** All scenarios are hand-designed by the SDACS team.
We have not crawled real-world flight logs (e.g. ASIAS) for empirical
distributions; that is a v2.0 goal. As a result, frequency and
co-occurrence of conflict types may not match real airspace.

---

## Manifest schema (v1.0)

Each `scenarios/NN_*/manifest.yaml` MUST contain these top-level keys:

```yaml
id: "01_corridor_crossing"           # str, ^[0-9]{2}_[a-z_]+$
name: "Corridor Crossing"            # str, human-readable
version: "1.0.0"                     # semver
category: "standard"                 # "standard" | "stress"
difficulty: "easy"                   # "easy" | "medium" | "hard"

duration_seconds: 300                # int, simulation horizon
dt_seconds: 1.0                      # float, step size

airspace:
  bounds_m:                          # bounding box of the operation
    x: [0, 1000]
    y: [0, 1000]
    z: [50, 400]                     # 50-400 ft AGL approximation
  volume_m3: 350_000_000             # convenience (computed from bounds)
  capacity_max_agents: 10            # ops cap for utilization metric

agents:
  count: 4                           # int
  kinematics:                        # one block applied to all agents
    max_speed_m_s: 15.0
    max_accel_m_s2: 5.0
    turn_rate_deg_s: 30.0
  spawn_pattern: "two_streams"       # see description.md
  goal_pattern: "swap_endpoints"

obstacles:
  static: []                         # list of {shape, params}
  dynamic: []                        # list of {shape, motion, params}

weather:
  wind:
    mean_m_s: 0.0
    gust_m_s: 0.0
    direction_deg: 0.0
  visibility_m: 10000
  precipitation_mm_per_h: 0.0

communications:
  quality: "perfect"                 # "perfect" | "noisy" | "degraded"
  packet_loss: 0.0
  blackout_windows_s: []             # list of [start, end]

regulatory:
  remote_id_required: true
  laanc_volume_class: "G"            # "B" | "C" | "D" | "E" | "G"
  geofences: []                      # list of polygons

success_criteria:                    # for the *suite*; SDACS targets
  NMR_max: 1.0e-4
  MSD_min_m: 5.0
  geofence_violations_max: 0
  RID_CR_min: 0.999

expected_baseline_performance:        # SDACS hybrid current numbers
  NMR: 0.0
  MSD_m: 10.0
  PE: 0.95
  MS_s: 78.0
  RTF: 12.5
```

Field validation lives in `benchmarks/_schema/manifest.schema.json`
(TODO: generate from this spec).

---

## Intended uses

- **Primary:** evaluating new UTM controllers against ORCA/VO/CBS/SDACS
  on shared scenarios.
- **Secondary:** ablation studies (turn off SDACS layers to see which
  scenario each layer protects against).
- **Tertiary:** sim-to-real validation when paired with a Vicon HITL
  setup (Phase 697-700).

**Out of scope:**

- Training data for ML models. Scenario count (10) is far too small.
  Use SMAC, MovingAI, or PettingZoo for ML training.
- Real-world flight clearance. The scenarios are simulation-only.

---

## Limitations & known caveats

1. **No real-world flight log calibration.** v1.0 is hand-designed.
2. **Single SDACS system as ground truth for `expected_results.yaml`.**
   If SDACS itself has a bug, expected ranges drift with it. Mitigated
   by requiring at least one external baseline (ORCA) per scenario.
3. **Determinism only inside Docker.** Running outside the
   `Dockerfile.reproducible` image may produce metric differences in
   the 4th decimal due to BLAS thread non-determinism.
4. **Unit ambiguity for "drone."** All scenarios assume a multirotor
   in the 1-25 kg class (FAA Group 1-2). Heavier or fixed-wing UAVs
   not validated.

---

## Ethical considerations

Drone swarms are dual-use. The benchmark intentionally does NOT include
scenarios involving:

- Adversarial interception of crewed aircraft
- Targeting persons or property
- Weaponized payload delivery

Stress scenario 10 ("Adversarial Swarm") models a *non-cooperative
intruder* — drones that ignore Remote ID and conflict resolution — to
test robustness, not to enable counter-swarm hostilities.

We follow the spirit of the AIAA Code of Ethics: "Knowledge derived
from this work shall not be used to harm others or the environment."

---

## How to cite

```bibtex
@misc{sdacs2026benchmark,
  author       = {Jang, Sunwoo},
  title        = {SDACS Benchmark Suite v1.0:
                  7+3 scenarios for UTM controller evaluation},
  year         = {2026},
  howpublished = {\url{https://github.com/sun475300-sudo/swarm-drone-atc/tree/main/benchmarks}},
  note         = {CC-BY-4.0; commit hash in CITATION.bib}
}
```

---

## Changelog

- **v1.0.0 (2026-04-26):** Initial release. 10 scenarios, 3 baselines,
  manifest schema locked.

---

*Last updated: 2026-04-26*
