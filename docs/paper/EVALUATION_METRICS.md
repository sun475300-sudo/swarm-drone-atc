# Evaluation Metrics — SDACS

**Phase:** P705
**Purpose:** Formalize every metric used to justify SDACS claims. Every number reported in the paper MUST trace back to one definition here.
**Last updated:** 2026-04-19

---

## 0. Design Principles

1. **One metric, one formula.** Ambiguity kills reproducibility.
2. **All metrics are sign-consistent:** higher = better, unless marked `(lower better)`.
3. **All metrics have units.** Dimensionless ratios use `[1]`.
4. **All metrics come with a computation function** (src/analytics/metrics.py — TODO).
5. **Report mean ± 95% CI over ≥ 30 Monte Carlo seeds.**

---

## 1. Safety Metrics (Primary)

### 1.1 Near-Miss Rate (NMR) — (lower better)

**Definition:**
A near-miss between drones *i* and *j* at time *t* occurs when their Euclidean distance drops below the safety buffer `d_safe`.

```
NMR = (# distinct near-miss events) / (# drone-pairs × simulation_horizon_in_seconds)
```

**Parameters:**
- `d_safe = 5 m` (default; configurable via `config/safety.yaml`)
- Event de-duplication: a near-miss is counted once until the pair separates beyond `2 * d_safe` for ≥ 2 s.

**Units:** events / (pair · second)
**Typical range:** 0 (ideal) to 1e-3 (unacceptable)

**Code reference:** `src/analytics/metrics.py::near_miss_rate()` (to implement)

---

### 1.2 Minimum Separation Distance (MSD) — (higher better)

**Definition:** Over the entire run, the minimum pairwise distance observed.
```
MSD = min_{i ≠ j, t} ‖x_i(t) − x_j(t)‖₂
```

**Units:** meters
**Reporting:** Report both MSD (single run worst case) and `mean(min-per-pair)` (mean of each pair's worst case).

---

### 1.3 Time-to-Conflict (TTC) distribution

**Definition:** For every CPA-predicted conflict, the lead time before the predicted closest approach.

**Useful summary statistics:** mean, median, 5th percentile (tail risk).
**Claim:** CPA lookahead ≥ 90 s should give median TTC ≥ 60 s in typical scenarios. (Verify!)

---

## 2. Efficiency Metrics

### 2.1 Path Efficiency (PE) — (higher better)

**Definition:**
Ratio of straight-line Euclidean distance to actual path length.
```
PE_i = ‖x_i(T_end) − x_i(T_start)‖₂ / ∫₀^T ‖ẋ_i(t)‖₂ dt
```

Report mean over all drones.

**Units:** dimensionless `[1]`, in `(0, 1]`. 1.0 means perfect straight-line.
**Interpretation:** Detour cost due to avoidance. Lower = more detour.

---

### 2.2 Makespan (MS) — (lower better)

**Definition:** Time at which the last drone reaches its goal.
```
MS = max_i T_goal_i − T_start
```

**Units:** seconds.
**Reporting:** Used as the cost function in CBS. Report absolute and normalized by ideal (straight-line, free-flight).

---

### 2.3 Flowtime (FT) — (lower better)

**Definition:** Sum of goal-arrival times.
```
FT = Σ_i (T_goal_i − T_start)
```

**Units:** drone-seconds.
**Why both MS and FT?** MS penalizes the slowest, FT penalizes average. CBS optimal for sum-of-costs, so FT is the natural primal metric.

---

## 3. Airspace Utilization

### 3.1 Airspace Utilization (AU) — (context-dependent)

**Definition:** Fraction of time the airspace contains ≥ k active drones, or:
```
AU = ∫₀^T (# active drones(t) / capacity) dt / T
```

**Units:** dimensionless in `[0, 1]`.
**Two reports needed:**
- High AU with low NMR = **good** (dense and safe)
- High AU with high NMR = **bad** (overloaded)

---

### 3.2 Voronoi Cell Utilization (VCU)

**Definition:** For each Voronoi cell assigned by the dynamic partitioner, report:
- `cell_occupancy(t)` — # drones assigned to cell
- `cell_handoff_rate` — # cell-boundary crossings / sec

**Purpose:** Shows whether the dynamic partitioning is stable (low handoff rate) or thrashing.

---

## 4. Regulatory Conformance (SDACS-specific)

### 4.1 Remote ID Compliance Rate (RID-CR) — (higher better)

**Definition:** Fraction of simulated drones for which the Remote ID broadcast (ASTM F3411 v2.0) passes schema validation every second.

```
RID-CR = (# seconds with valid broadcast) / (# drones × total seconds)
```

**Target:** ≥ 99.9 %. Any failure is a regulatory violation.

---

### 4.2 LAANC Authorization Latency — (lower better)

**Definition:** Mean time between a flight plan filing request and its accept/reject decision from the mocked LAANC interface.

**Units:** milliseconds.
**Target:** ≤ 200 ms (industry SLA).

---

### 4.3 Geofence Violation Count — (lower better; hard target = 0)

**Definition:** Number of timestamps at which any drone's position lies outside its authorized volume.

**Units:** count.
**Target:** 0. Any non-zero value is a blocker for the paper.

---

## 5. Computational Efficiency

### 5.1 Real-Time Factor (RTF) — (higher better)

**Definition:**
```
RTF = simulated_seconds / wall_clock_seconds
```
RTF > 1 means the simulator runs faster than real time.

**Report per N** (# drones): RTF(N=10), RTF(N=50), RTF(N=100), RTF(N=200).
**Target:** RTF(N=100) ≥ 5.

---

### 5.2 Per-Tick Latency — (lower better)

**Definition:** Wall-clock time to compute one AirspaceController 1 Hz tick.
**Report:** p50, p95, p99.

---

### 5.3 Memory Peak (RSS)

**Units:** MB.
**Purpose:** Scaling claim.

---

## 6. Reporting Table (paper-ready)

| Metric | Unit | Direction | Baseline (ORCA only) | SDACS hybrid | Δ | p-value |
|--------|------|-----------|----------------------|--------------|---|---------|
| NMR (×10⁻⁴) | ev/(pair·s) | ↓ | TODO | TODO | TODO | TODO |
| MSD | m | ↑ | TODO | TODO | TODO | TODO |
| PE | [1] | ↑ | TODO | TODO | TODO | TODO |
| MS | s | ↓ | TODO | TODO | TODO | TODO |
| AU | [1] | context | TODO | TODO | TODO | TODO |
| RID-CR | [1] | ↑ | N/A | TODO | N/A | N/A |
| RTF(N=100) | [1] | ↑ | TODO | TODO | TODO | TODO |

Use Welch's t-test (unequal variance) for significance. Report `p < 0.05` claim only with Bonferroni-corrected threshold `p < 0.05 / #metrics`.

---

## 7. Statistical Protocol

- **Seeds:** 30 fixed seeds (0..29) committed in `config/seeds.yaml`.
- **Scenarios:** 7 Monte Carlo scenarios (existing Phase 1-470 set).
- **Per (scenario, baseline) cell:** 30 runs.
- **Total runs per experiment:** 7 × 30 × 2 baselines = 420.
- **Expected wall time:** 420 × ~10 s / RTF ≈ 20 min on reference hardware.

All raw results stored in `results/<timestamp>/runs.parquet` with schema:
`seed, scenario, method, metric, value, wall_time_s`.

---

## 8. Joint metrics (if paper spans sc2bot)

When reporting the SC2 swarm-control bridge in the same paper, add:

| Metric | Domain | Unit |
|--------|--------|------|
| Win rate vs Easy/Medium/Hard | SC2 | [0,1] |
| APM (actions per minute) | SC2 | [1/min] |
| Worker kill count (per minute) | SC2 | [1/min] |
| Expansion time (min → N-th base) | SC2 | s |

Cross-domain claim table:
| Principle | UAV manifestation | SC2 manifestation |
|-----------|-------------------|-------------------|
| Potential field | APF collision avoidance | Unit micro kiting (stutter-step) |
| Constraint satisfaction | CBS path planning | Build-order resource reservation |
| Formation | Voronoi partition | Army concave / position |

---

## 9. Open Items

- [ ] Implement `src/analytics/metrics.py` with one function per metric.
- [ ] Add unit tests in `tests/analytics/test_metrics.py` — fixed input, known output.
- [ ] Add `scripts/run_benchmark.py` that sweeps (seed × scenario × method) and writes `results/*.parquet`.
- [ ] Decide `d_safe` value (currently 5 m placeholder).
- [ ] Confirm whether the paper targets IROS 2026 (deadline Feb?) or AIAA SciTech 2027.
