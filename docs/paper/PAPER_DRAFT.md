# SDACS Paper Draft (Phase 707)

> **Working draft** for AIAA SciTech 2027 submission (deadline 2026-06-04).
> Sections marked `[TBD]` need experimental data from P706.
> Sections marked `[ASK]` need a decision.

**Title (working):** A Hybrid Global–Reactive UTM Layer with Regulatory
Conformance: Benchmarking SDACS against ORCA, VO, and CBS in Dense
Sub-400 ft Airspace

**Authors:** Sunwoo Jang¹ [`ASK: 지도교수 second author?`]
**Affiliations:** ¹ Mokpo National University, Dept. of Drone Mechanical Engineering
**Corresponding:** sun475300@gmail.com
**Target page count:** 8 (AIAA SciTech standard)

---

## 0. Section budget (8 pages)

| § | Section | Pages | Status |
|---|---------|-------|--------|
| 1 | Abstract + Introduction | 1.0 | draft |
| 2 | Related Work | 1.0 | draft (P702 30 refs) |
| 3 | System Architecture | 1.5 | draft |
| 4 | Benchmark Suite | 1.0 | draft (P703) |
| 5 | Experiments + Results | 2.0 | [TBD: P706] |
| 6 | Discussion | 1.0 | skeleton |
| 7 | Conclusion + Future Work | 0.3 | skeleton |
| — | References | 0.2 | (not page-counted) |

---

## 1. Abstract + Introduction

### Abstract (≤ 250 words, AIAA limit)

> Unmanned aircraft system traffic management (UTM) systems must
> simultaneously satisfy three orthogonal requirements: collision-free
> coordination, regulatory conformance (Remote ID, geofence, LAANC), and
> real-time scalability to 200+ drones in 1 km³. Existing approaches
> attack one axis at a time — Conflict-Based Search (CBS) for global
> coordination, ORCA / Velocity Obstacle for reactive avoidance, NASA
> UTM CoO for regulation — and the literature lacks a benchmark on which
> these can be fairly compared.
>
> We present SDACS, an open-source UTM controller that composes a CBS
> global planner, an APF reactive layer, and an ASTM F3411 regulatory
> bus into a single 1 Hz tick. We release a 10-scenario benchmark suite
> (7 standard + 3 stress) with bit-deterministic Docker reproduction
> and 14 metrics spanning safety (Near-Miss Rate, Min Separation),
> efficiency (Path Efficiency, Makespan), regulatory conformance
> (Remote-ID compliance, geofence violations, LAANC latency), and
> computational throughput (Real-Time Factor).
>
> Across 1,200 simulated runs (10 scenarios × 4 systems × 30 seeds),
> SDACS hybrid achieves [TBD: NMR] near-misses per drone-pair-second
> versus [TBD] for ORCA-only — a [TBD: ~10×] reduction — at a
> [TBD: 5%] cost in path efficiency. We further show that the same
> compositional pattern transfers to non-physical multi-agent control:
> a sister project applying CBS-like resource reservation plus APF-like
> kiting in StarCraft II swarm-micro yields measurable wins.

### 1.1 Introduction structure

1. **Motivation paragraph (≈80 words):** sub-400 ft airspace is
   filling up — drone delivery, infrastructure inspection, urban air
   mobility. The 2023 FAA Part 89 Remote ID rule made *enforcement*
   real, but the academic UTM literature still treats it as future work.
2. **Gap paragraph (≈80 words):** existing work compares within a
   layer; nobody compares *layer compositions*. NASA UTM CoO is a
   document, not a runnable benchmark.
3. **Contribution bullets (3, mirror PAPER_TOPIC.md):**
   - C1: Hybrid 3-layer architecture with empirically-validated
     ablation.
   - C2: Open benchmark suite (10 scenarios + 3 baselines, bit-det
     Docker repro).
   - C3: Cross-domain pattern transfer (UAV ↔ SC2).
4. **Paper roadmap (≈40 words).**

---

## 2. Related Work

Map directly onto `docs/paper/PRIOR_WORK_SURVEY.md` buckets:

### 2.1 Multi-Agent Path Finding (Bucket A)
CBS [Sharon 2015], ICBS [Boyarski 2015], EECBS [Li 2021], lifelong
MAPF [Li 2021], M*/OD-ID [Standley 2011], CBSH [Felner 2018], PRIMAL
[Sartoretti 2019], Hönig 2024 quadrotor swarms.

> SDACS reuses CBS for the global planner with the EECBS bounded-suboptimal
> mode for the real-time path. The bypass heuristic from ICBS is adopted
> for dense intersection scenarios (sc 02).

### 2.2 Reactive Collision Avoidance (Bucket B)
VO [Fiorini 1998], ORCA [van den Berg 2011], HRVO [Snape 2011], APF
[Khatib 1986] + GNRON [Ge & Cui 2000], deadlock resolution
[Alonso-Mora 2018], KAPF [Park 2014].

> SDACS uses APF + GNRON in the reactive layer. We compare against
> ORCA and VO as baselines because they're the most-cited reciprocal
> velocity methods.

### 2.3 UTM / UAS Traffic Management (Bucket C)
NASA UTM CoO [Kopardekar 2016 → 2020], FAA LAANC, FAA Part 89 Remote
ID, ASTM F3411-22a, EUROCAE ED-269 (EU), Doole 2020 density model,
Causa 2022 mixed-GNSS.

> Most prior UTM work either provides regulatory frameworks (NASA, FAA,
> EUROCAE, ASTM) without runnable code, or implements a single
> compliance check without comparison. SDACS treats the regulatory
> layer as a first-class evaluation axis (RID-CR ≥ 99.9% as hard floor).

### 2.4 Swarm Behavior & Cross-Domain (Bucket D)
Boids [Reynolds 1986], Olfati-Saber 2006 algebraic flocking, Tanner
2003 stability, Vásárhelyi 2018 30-drone outdoor swarm, Wang & Schwager
2021 force allocation, SMAC [Samvelyan 2019], AlphaStar [Vinyals 2019].

> Vásárhelyi 2018 is our outdoor performance target for Track A.
> SMAC and AlphaStar are cross-domain anchors for our Contribution 3.

### 2.5 Positioning

We are uniquely placed at the **intersection of A + B + C** with C as
the differentiator. Hönig 2024 is the closest A+B competitor; we
differentiate via the regulatory layer and the open benchmark suite.

---

## 3. System Architecture

### 3.1 Three-layer overview (Fig. 1)

```
┌────────────────────────────────────────────────────────────┐
│ REGULATORY LAYER  (1 Hz)                                   │
│   • Remote ID broadcast (ASTM F3411 v2.0)                  │
│   • LAANC mock interface                                    │
│   • Geofence + dynamic NFZ injection                        │
│   • Priority bus (PAN_PAN, MAYDAY, manned aircraft)         │
└────────────────────────────────────────────────────────────┘
            ▼ constraints                  ▲ exceptions
┌────────────────────────────────────────────────────────────┐
│ GLOBAL PLANNING LAYER  (every 30 s, on-demand)             │
│   • CBS with EECBS bounded-suboptimal mode                  │
│   • Voronoi partitioning of airspace                        │
│   • Time-windowed conflict resolution                       │
└────────────────────────────────────────────────────────────┘
            ▼ trajectory plans            ▲ infeasibility
┌────────────────────────────────────────────────────────────┐
│ REACTIVE LAYER  (10 Hz)                                    │
│   • APF (Khatib + GNRON repulsive form)                     │
│   • Per-Voronoi-cell local interactions                     │
│   • CPA lookahead (90 s prediction window)                  │
└────────────────────────────────────────────────────────────┘
            ▼ velocity setpoint           ▲ telemetry
        ┌─────────────────────────────────────┐
        │ Drone agent (PX4 / Pixhawk SITL)    │
        └─────────────────────────────────────┘
```

`[Fig. 1]` Three-layer SDACS architecture. Counterclockwise data flow
top to bottom; clockwise exception flow bottom to top.

### 3.2 1 Hz airspace controller tick

Pseudocode for the main loop:

```python
async def tick():
    # P705 metrics start
    t0 = time.perf_counter()
    
    # 1) Refresh regulatory state
    geofences = await regulatory_bus.poll(timeout=0.05)
    priorities = await regulatory_bus.priorities()
    
    # 2) Detect deviation from planned trajectory
    deviations = []
    for agent in agents:
        if cpa_lookahead.predict_conflict(agent, horizon_s=90) is not None:
            deviations.append(agent)
    
    # 3) Re-plan only affected agents (incremental CBS)
    if deviations:
        replan = await cbs_planner.solve(
            agents=deviations,
            constraints=geofences + priorities,
            timeout_s=2.0,
        )
        for agent_id, traj in replan.items():
            agents[agent_id].trajectory = traj
    
    # 4) Reactive overlay (APF correction at 10 Hz, sampled here)
    for agent in agents:
        v_apf = apf_layer.compute(agent, neighbors_in_voronoi(agent))
        agent.velocity_setpoint = blend(agent.trajectory.v(t), v_apf)
    
    # 5) Emit telemetry + metrics
    metrics_recorder.tick(time.perf_counter() - t0)
```

### 3.3 Layer interaction table (key claim)

| Failure scenario | Single-layer behavior | Hybrid behavior |
|------------------|----------------------|-----------------|
| Storm cell appears | CBS replan from scratch (slow) | Regulatory inserts dynamic NFZ → planner replans only affected agents |
| Manned aircraft transit | ORCA panics, MSD violations | Regulatory creates corridor exclusion → CBS yields, APF holds spacing |
| 200-drone density | CBS combinatorial explosion | Voronoi shards; per-cell CBS + APF |
| Comms blackout 30 s | CBS can't replan, ORCA OK | Reg detects blackout → forces hold pattern → APF maintains MSD distributedly |

---

## 4. Benchmark Suite (P703)

Brief description (≤ 0.5 page) + table:

| # | Scenario | Tests |
|---|----------|-------|
| 01 | Corridor Crossing | sanity baseline |
| 02 | Dense Intersection | layer interaction under saturation |
| 03 | Emergency Landing | priority handoff |
| 04 | No-Fly Zone | regulatory hard constraint |
| 05 | Weather Diversion | dynamic obstacle replanning |
| 06 | Priority Aircraft | mixed-priority |
| 07 | Communication Loss | distributed-only fallback |
| 08 | Stress: 200 drones / 1 km³ | scaling |
| 09 | Stress: failure cascade | graceful degradation |
| 10 | Stress: adversarial swarm | non-cooperator robustness |

Refer to `benchmarks/README.md` and `benchmarks/DATASET_CARD.md` for
full manifest schema. Reproducibility one-liner:

```bash
docker run --rm -v "$(pwd)/results:/app/results" sdacs-repro:0.1.0 \
    bash scripts/reproduce/run_all.sh
```

---

## 5. Experiments and Results

### 5.1 Setup

- 4 systems: SDACS hybrid, ORCA, VO, CBS-only
- 10 scenarios from §4
- 30 seeds each → 1,200 runs total
- Reference HW: 16 cores / 32 GB / Ubuntu 22.04 host, Docker 24.0
- Wall time per full sweep: ~25 min (claim)

### 5.2 Headline result table `[TBD: fill from P706]`

| Metric | Direction | ORCA | VO | CBS | SDACS hybrid | Δ (SDACS vs best other) | p |
|--------|-----------|------|----|----|-------------|-----|---|
| NMR ×10⁻⁴ ev/(pair·s) | ↓ | TBD | TBD | TBD | TBD | TBD | TBD |
| MSD (m) | ↑ | TBD | TBD | TBD | TBD | TBD | TBD |
| PE | ↑ | TBD | TBD | TBD | TBD | TBD | TBD |
| MS (s) | ↓ | TBD | TBD | TBD | TBD | TBD | TBD |
| AU | ctx | TBD | TBD | TBD | TBD | TBD | TBD |
| RID-CR | ↑ | N/A | N/A | N/A | TBD | N/A | N/A |
| Geofence violations | ↓ (=0) | TBD | TBD | TBD | TBD | TBD | TBD |
| RTF (N=100) | ↑ | TBD | TBD | TBD | TBD | TBD | TBD |

Statistical test: Welch's t-test, Bonferroni-corrected at
α = 0.05/8 = 0.00625.

### 5.3 Per-scenario breakdown (Fig. 2)

`[Fig. 2]` Heat-map of NMR across 10 scenarios × 4 systems.
Expectation: SDACS hybrid is best or tied-best on every cell except
maybe sc 01 (where all systems pass).

### 5.4 Ablation (Fig. 3)

Drop one SDACS layer at a time:
- `no_global` — APF + Reg only
- `no_reactive` — CBS + Reg only
- `no_regulatory` — CBS + APF only

Hypothesis: each layer dominates on a distinct scenario subset. Plot
the per-scenario win count for each ablation.

### 5.5 Scaling (Fig. 4)

RTF as a function of N ∈ {10, 50, 100, 200, 500}. Claim: ≥ 5 at N=100;
target ≥ 1 at N=500.

### 5.6 Cross-domain validation (Fig. 5, Contribution 3)

Apply the same compositional pattern (CBS-like resource reservation +
APF-like kiting) in StarCraft II swarm-micro (`Swarm-control-in-sc2bot`):

- Win rate vs built-in Hard Zerg: TBD %
- APM curve: TBD
- Build-order timing: TBD

`[ASK: 이 contribution을 8쪽 안에 다 담을지, 또는 cut to "section" not "contribution"?]`

---

## 6. Discussion

### 6.1 What the layer interaction table predicts vs. what data shows

`[TBD: fill after experiments]`

### 6.2 Limitations

- Simulation-only — Track A (Vicon HITL) results not in this paper.
- Adversarial scenario (sc 10) is defensive-only by design.
- Reproducibility depends on Docker; non-Linux hosts may see 4th-decimal
  drift in BLAS reductions.
- 30-seed aggregation is below the 100-seed best practice for high-stakes
  safety claims; defensible because each scenario has a fixed
  deterministic structure, but flag this.

### 6.3 Threats to validity

- **Scenario selection bias:** all 10 scenarios are hand-designed.
  v2.0 will add scenarios derived from real flight logs.
- **Single SDACS implementation as ground truth for `expected_results.yaml`:**
  mitigated by requiring at least one external baseline (ORCA) per scenario.
- **OAuth/network for LAANC mock:** mock returns deterministic
  latencies; real LAANC has 200 ms p99.

### 6.4 Threats to deployment

- **OAuth refresh for Remote ID network mode:** not modeled (we use
  broadcast mode). Real network-mode operation needs refresh
  reliability ≥ 99.99%.

---

## 7. Conclusion + Future Work

(Short — ≤ 0.3 page.)

> SDACS is the first open-source UTM controller to combine global
> CBS planning, reactive APF avoidance, and ASTM F3411 regulatory
> conformance, benchmarked on a 10-scenario open suite with
> bit-deterministic reproduction. Across 1,200 simulated runs, the
> hybrid composition achieves [TBD] safety improvement at [TBD]
> efficiency cost over single-layer baselines, with regulatory
> conformance maintained at ≥ 99.9% Remote-ID compliance. The same
> compositional pattern transfers to a non-physical domain (StarCraft
> II swarm-micro), suggesting it is a portable design pattern for
> multi-agent control.
>
> Future work: hardware HITL validation (Vicon + Pixhawk + Jetson Orin),
> v2.0 benchmark scenarios derived from FAA ASIAS flight logs, and a
> SaaS dashboard for K-UTM pilot operations.

---

## 8. Open items / Open questions

1. `[ASK]` Decide single-author vs. co-author with 지도교수 by
   2026-05-14.
2. `[TBD]` All [TBD] cells in §5 — fill after P706 runs.
3. `[ASK]` Contribution 3 (cross-domain): full contribution or
   section-only? Risk: reviewers say "two papers in one."
4. `[TODO]` Generate Fig. 1 (architecture) — TikZ or Plotly?
5. `[TODO]` Run the full 1,200-run benchmark on reference hardware,
   check the 25-min wall-time claim.
6. `[TODO]` Get internal review (≥ 3 reviewers) by 2026-05-21
   per `PAPER_TOPIC.md` D-day plan.
7. `[CHECK]` AIAA SciTech 2027 conflict-of-interest policy vs. 동강대
   학술대회 발표 (not formally proceedings → likely OK).

---

## 9. Cross-references

- `docs/paper/PAPER_TOPIC.md` — topic confirmation, target venue, D-day
- `docs/paper/PRIOR_WORK_SURVEY.md` — 30 references (P702)
- `docs/paper/EVALUATION_METRICS.md` — metric spec (P705)
- `docs/REPRODUCIBILITY.md` — bit-deterministic guarantees (P704)
- `benchmarks/README.md` — scenario suite (P703)

---

*Last updated: 2026-04-27 (P707 skeleton). Body ≈ 2,500 words; will
expand to ~6,500 (8 pages × ~800 wpp) once P706 data lands.*
