# SDACS Benchmark Suite

> Open benchmark suite for evaluating multi-drone airspace control systems
> against the SDACS reference, across 7 standard scenarios + 3 stress
> scenarios, with bit-deterministic reproduction.

**Phase:** P703
**Maintainer:** 장선우 (sun475300@gmail.com)
**License:** [CC-BY-4.0](LICENSE) — share, adapt, attribute.

---

## Why this benchmark exists

There is no openly-published UTM (UAS Traffic Management) benchmark that
combines (a) regulatory metrics like Remote-ID Compliance Rate and LAANC
latency with (b) scenario manifests sufficient for cross-paper comparison.
MovingAI's MAPF benchmarks are 2D-only and lack regulatory targets;
SMAC is game-only.

This suite aims to be the **"MovingAI of UTM"** — a small, fully
specified set of scenarios that anyone can drop into their planner and
report a comparable number on.

---

## What's included

```
benchmarks/
├── README.md            # this file
├── LICENSE              # CC-BY-4.0
├── DATASET_CARD.md      # ML-style dataset card
├── CITATION.bib         # BibTeX for citing the suite
├── scenarios/
│   ├── 01_corridor_crossing/        # Standard
│   ├── 02_dense_intersection/       # Standard
│   ├── 03_emergency_landing/        # Standard
│   ├── 04_no_fly_zone/              # Standard
│   ├── 05_weather_diversion/        # Standard
│   ├── 06_priority_aircraft/        # Standard
│   ├── 07_communication_loss/       # Standard
│   ├── 08_stress_high_density/      # Stress
│   ├── 09_stress_failure_cascade/   # Stress
│   └── 10_stress_adversarial_swarm/ # Stress
├── baselines/
│   ├── orca/                        # Reciprocal Velocity Obstacle (van den Berg 2011)
│   ├── vo/                          # Velocity Obstacle (Fiorini & Shiller 1998)
│   └── cbs/                         # Conflict-Based Search (Sharon 2015)
└── metrics/
    └── README.md                    # Pointer to ../docs/paper/EVALUATION_METRICS.md
```

Each scenario folder contains:

| File | Purpose |
|------|---------|
| `manifest.yaml` | Machine-readable scenario specification (agents, obstacles, weather, success criteria) |
| `description.md` | Human-readable narrative of the scenario, design rationale, expected behavior |
| `expected_results.yaml` | SDACS-internal expected ranges per metric (used by CI to detect regressions) |

---

## Quick start

### 1. Run all baselines on all scenarios (one command)

```bash
docker run --rm -v "$(pwd)/results:/app/results" sdacs-repro:0.1.0 \
    bash scripts/reproduce/run_all.sh
```

Wall time on reference hardware (16 cores / 32 GB): **~25 minutes**.

### 2. Run a single scenario with a single method

```bash
docker run --rm -v "$(pwd)/results:/app/results" sdacs-repro:0.1.0 \
    bash scripts/reproduce/run_one.sh 01_corridor_crossing sdacs_hybrid 42
```

### 3. Adapt your own planner

Implement the adapter interface defined in `baselines/orca/adapter.py`
(it's a 30-line Protocol). Your planner becomes a 4th column in the
result table.

---

## Metrics

All scenarios are scored on the 14 metrics defined in
[`../docs/paper/EVALUATION_METRICS.md`](../docs/paper/EVALUATION_METRICS.md).
The headline metrics are:

| Metric | Direction | Target | Why it matters |
|--------|-----------|--------|----------------|
| **NMR** Near-Miss Rate | ↓ | < 1e-4 | Safety primary; below this is ATC-acceptable |
| **MSD** Min Separation | ↑ | ≥ 5 m | Hard floor; below = unsafe |
| **PE** Path Efficiency | ↑ | ≥ 0.85 | Avoidance shouldn't waste flight |
| **MS** Makespan | ↓ | scenario-dependent | Throughput proxy |
| **RID-CR** Remote-ID Compliance | ↑ | ≥ 0.999 | Hard regulatory floor |
| **RTF** Real-Time Factor | ↑ | ≥ 5 at N=100 | Operational viability |

Reference numbers on SDACS hybrid are stored in each scenario's
`expected_results.yaml` and refreshed by CI on every `main` push.

---

## Scenario design

The 7 standard scenarios are picked to cover the orthogonal axes that
literature routinely conflates:

| # | Name | Tests |
|---|------|-------|
| 01 | Corridor Crossing | Simple 2-stream conflict, baseline sanity |
| 02 | Dense Intersection | 4-way conflict, high local density |
| 03 | Emergency Landing | Priority handling under disturbance |
| 04 | No-Fly Zone | Geofence respect under shortest-path pressure |
| 05 | Weather Diversion | Dynamic obstacle (storm cell), replanning |
| 06 | Priority Aircraft | Mixed-priority traffic (manned aircraft transit) |
| 07 | Communication Loss | Degraded comms — distributed-only fallback |

The 3 stress scenarios push the system past the standard envelope:

| # | Name | Tests |
|---|------|-------|
| 08 | Stress: High Density | 200 agents in 1 km³ — capacity claim |
| 09 | Stress: Failure Cascade | 10 % drones lose control, 5 % brick mid-flight |
| 10 | Stress: Adversarial Swarm | Non-cooperative intruder swarm injects randomly |

---

## How to cite

```bibtex
@misc{sdacs2026benchmark,
  author = {Jang, Sunwoo},
  title  = {SDACS Benchmark Suite v1.0:
            7+3 scenarios for UTM controller evaluation},
  year   = {2026},
  howpublished = {\url{https://github.com/sun475300-sudo/swarm-drone-atc/tree/main/benchmarks}},
  note   = {CC-BY-4.0}
}
```

---

## Versioning

The suite uses semver-style versioning. v1.0 is locked at the
2026-04-26 commit hash recorded in `CITATION.bib`. Bumping a scenario
manifest (changing num_agents, obstacles, weather) is a *minor* bump.
Adding a scenario is a *minor* bump. Breaking the manifest schema is a
*major* bump.

---

## Contributing a new scenario

1. Pick the next free `NN_short_name` slot.
2. Copy `scenarios/_template/` (TODO).
3. Fill in `manifest.yaml` per the schema in [`DATASET_CARD.md`](DATASET_CARD.md).
4. Run all baselines and commit `expected_results.yaml`.
5. Open a PR; CI will diff the new scenario against the existing 10.

---

## See also

- [`DATASET_CARD.md`](DATASET_CARD.md) — full dataset card (Hugging Face / Papers With Code style)
- [`../docs/paper/EVALUATION_METRICS.md`](../docs/paper/EVALUATION_METRICS.md) — metric definitions
- [`../docs/paper/PAPER_TOPIC.md`](../docs/paper/PAPER_TOPIC.md) — paper this benchmark backs
- [`../docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md) — bit-determinism guarantees

---

*Last updated: 2026-04-26*
