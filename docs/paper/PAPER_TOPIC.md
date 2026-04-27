# SDACS Paper Topic — Phase 701

**Decision date:** 2026-04-26
**Author:** 장선우 (sun475300@gmail.com), Mokpo National University, Dept. of Drone Mechanical Engineering
**Status:** ✅ TOPIC CONFIRMED — proceeding to P702 (survey) and P705 (metrics) under this frame.

---

## 1. 확정 주제 (Confirmed Title)

> **A Hybrid Global–Reactive UTM Layer with Regulatory Conformance: Benchmarking SDACS against ORCA, VO, and CBS in Dense Sub-400 ft Airspace**

**One-line pitch.**
SDACS는 *전역 계획 (CBS)* + *반응적 회피 (APF)* + *규제 준수 (Remote ID / LAANC / Geofence)* 세 층을 하나의 1 Hz airspace controller에 결합한 UTM 시스템이고, 동일 시나리오에서 ORCA·VO·CBS 단일 베이스라인 대비 **near-miss를 한 자릿수 줄이면서 path efficiency 손실은 5% 이내**로 유지함을 증명한다.

이 주제가 주는 frame:
- **연구 질문(RQ):** "Reactive layer 단독이 막지 못하는 conflict를 global layer가 얼마만큼 흡수하고, regulatory layer는 그 trade-off를 어떻게 바꾸는가?"
- **무엇을 비교하나:** 4 시스템 × 7+3 시나리오 × 30 seed = **1,200 runs** (P705 §7 Statistical Protocol 기반).
- **핵심 dependent variable:** Near-Miss Rate (NMR), Path Efficiency (PE), Real-Time Factor (RTF), Remote-ID Compliance Rate (RID-CR).

---

## 2. Three Contributions

### Contribution 1 — Hybrid 3-layer architecture with empirically-validated layer interaction

**Claim (1 sentence):** SDACS is the first open-source UTM stack that composes CBS (global), APF/Voronoi (reactive), and ASTM F3411 conformance into a single 1 Hz controller, and we quantify how each layer's removal degrades safety vs. efficiency.

**Evidence in repo:**
- Architecture: `src/airspace_control/controller/` (1 Hz tick), `src/airspace_control/planning/` (CBS), `src/airspace_control/avoidance/` (APF + Voronoi).
- Ablation study: `scripts/run_benchmark.py --ablation no_global | no_reactive | no_regulatory` (to add).
- Conformance interface: `src/airspace_control/comms/` (Remote ID, LAANC mock).

**Why novel:** Existing literature compares within a layer (CBS vs PBS, ORCA vs VO, RVO vs HRVO). We compare *layer compositions* on the same scenario set, with the regulatory layer as a first-class evaluation axis (RID-CR ≥ 99.9% as a hard target).

**Differentiator vs prior work:**
- vs. NASA UTM CoO v2 (`nasa2020utm`): we provide a *runnable* benchmark, they provide a concept document.
- vs. Sharon et al. CBS (`sharon2015cbs`): we add reactive + regulatory layers and re-validate the claimed sum-of-costs optimality empirically.

---

### Contribution 2 — Open benchmark suite (7 standard + 3 stress scenarios) with bit-deterministic reproduction

**Claim (1 sentence):** We release a 10-scenario benchmark suite with `manifest.yaml` + ORCA/VO/CBS baseline implementations + `Dockerfile.reproducible` such that any reviewer can reproduce every paper number to the last decimal in ≤ 25 minutes wall-clock.

**Evidence in repo:**
- Benchmark structure: `benchmarks/scenarios/{01..10}/manifest.yaml` (P703).
- Baseline adapters: `benchmarks/baselines/{orca,vo,cbs}/`.
- Reproducibility: `Dockerfile.reproducible`, `docs/REPRODUCIBILITY.md`, `scripts/reproduce/run_all.sh` (P704).
- Determinism: `PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`, single `numpy.random.default_rng(seed)` (`src/utils/rng.py`).
- Metrics: `src/analytics/metrics.py` implements all 14 metrics from `docs/paper/EVALUATION_METRICS.md` (P705).

**Why novel:** MAPF benchmarks (movingai) and SC2 benchmarks (SMAC) exist, but **no open UTM benchmark** combines (a) regulatory metrics (RID-CR, LAANC latency) with (b) scenario manifests sufficient for cross-paper comparison. We aim to be the "MovingAI of UTM."

**Differentiator vs prior work:**
- vs. MovingAI MAPF benchmarks: ours is 3D + temporal + regulatory.
- vs. SMAC (`samvelyan2019smac`): physical (not game) and has regulatory targets.

---

### Contribution 3 — Cross-domain principle transfer: same constraint+potential composition wins in two domains

**Claim (1 sentence):** The same compositional pattern — global constraint satisfaction (CBS / build-order reservation) + local potential field (APF / SC2 unit kiting) — yields measurable wins both in physical UAV swarms and in StarCraft II swarm-micro, suggesting it is a portable design pattern for multi-agent control.

**Evidence in repo (joint with sister project `Swarm-control-in-sc2bot`):**
- UAV side: §1 above.
- SC2 side: `wicked_zerg_challenger/economy/queen_inject_optimizer.py` (resource reservation = constraint), `wicked_zerg_challenger/combat_manager.py` (kiting = potential field).
- Shared metric framework: see `EVALUATION_METRICS.md §8 Joint metrics`.

**Why novel:** Sim2Real transfer is well studied; *cross-domain* transfer of *coordination patterns* (not weights) is rarely formalized.

**Differentiator vs prior work:**
- vs. AlphaStar (`vinyals2019alphastar`): they show RL transfers across SC2 races. We claim *non-RL coordination patterns* transfer across physical and simulated domains.

**Risk note:** Contribution 3 is the most ambitious and the most likely to be cut if reviewers push back on "two-papers-in-one." The fallback is to make it a section, not a contribution, and submit the SC2 bridge separately to AAAI 2027.

---

## 3. Target Venue Matrix

| Venue | Deadline (estimated) | Page limit | Review model | Fit (★/5) | Rationale |
|-------|---------------------|------------|--------------|-----------|-----------|
| **IROS 2026** | 2026-03-01 (passed) | 6+1 | Double-blind, 3 reviewers | ★★★★☆ | Strong fit for layer ablation + benchmark; **deadline missed for 2026, target 2027 cycle.** |
| **AIAA SciTech 2027** | **2026-06-04** (open) | 8 | Single-blind | ★★★★★ | **PRIMARY TARGET.** UTM/UAS Traffic Management is a SciTech track. Regulatory contribution lands well here. |
| **ICRA 2027** | 2026-09-15 (estimated) | 6+1 | Double-blind | ★★★★☆ | Good fit for hybrid controller, but UTM angle is weaker. **SECONDARY TARGET** if AIAA rejects. |
| **JATM (Journal of Air Transportation Management)** | Rolling | 12+ | Single-blind | ★★★★★ | Long-form journal — best for full benchmark + regulatory analysis. **THIRD TARGET as journal extension.** |
| **arXiv only** | N/A | N/A | None | ★★☆☆☆ | Not enough for capstone credit; use as preprint after AIAA submission. |

**Decision: AIAA SciTech 2027 → AIAA preprint on arXiv → ICRA 2027 (if rejected) → JATM extension.**

---

## 4. 3-Month D-day Plan (working backwards from 2026-06-04)

| Date | Milestone | Owner | Verify by |
|------|-----------|-------|-----------|
| **2026-06-04** | AIAA SciTech 2027 submission deadline | 장선우 | ConfTool receipt |
| 2026-05-28 | Paper v1.0 finalized; arXiv tar-ball uploaded | 장선우 | Co-author sign-off |
| 2026-05-21 | 지도교수 1차 리뷰 피드백 반영 완료 | 장선우 + 지도교수 | Pull request merged |
| 2026-05-14 | Paper v0.9 draft (8 pages, all figures, all tables) | 장선우 | Self-checklist |
| 2026-05-07 | All experiments run on reference hardware; `summary.parquet` frozen | benchmark runner | `make repro && diff` |
| 2026-04-30 | All metrics implemented + tested (P705 done) | this session + next | `pytest tests/analytics/` green |
| 2026-04-26 | Paper topic confirmed (this doc) | this session | ✅ |
| 2026-04-26 | Benchmark scenario manifests written (P703) | this session | `benchmarks/scenarios/*/manifest.yaml` exist |
| 2026-04-26 | Reproducibility scaffolding (P704) | this session | `Dockerfile.reproducible` + `docs/REPRODUCIBILITY.md` exist |

**Slack of 1 week (2026-05-28 → 2026-06-04) is intentional — IROS-style anonymization fixes always take longer than expected.**

---

## 5. Open Questions / Risks

1. **Single-author vs co-author.** AIAA SciTech allows single-author. Decide by 2026-05-14 whether to invite 지도교수 as second author. If yes, get sign-off on contribution split before paper v1.0.
2. **Hardware claim scope.** Track A (P691-P700) hardware integration may not be ready by 2026-05-07. Fallback: paper claims "validated in Vicon HITL with N=3 drones" instead of "validated in outdoor flight."
3. **Cross-domain Contribution 3.** May get cut. Plan B: spin off as AAAI 2027 short paper or workshop submission.
4. **Reproducibility 25-minute claim.** Currently extrapolated from P704 estimate. Re-measure on actual reference hardware after first full run — adjust `docs/REPRODUCIBILITY.md` `TL;DR` if it drifts.
5. **Ethics & dual-use.** Drone swarms touch dual-use territory. Add an ethics paragraph to the paper (NeurIPS-style); review against AIAA conduct policy.
6. **Korean venue cross-submission.** The 4/23 동강대 학술대회 발표는 그 자체로 출판된 것이 아니므로 SciTech submission에 conflict 없음. Confirm in writing if 동강대 proceedings appear formally.

---

## 6. Cross-references

- Methodology: see `docs/paper/EVALUATION_METRICS.md` (P705 spec)
- Related work: see `docs/paper/PRIOR_WORK_SURVEY.md` (P702 in progress)
- Reproducibility: see `docs/REPRODUCIBILITY.md` (P704)
- Benchmark suite: see `benchmarks/README.md` (P703)
- Roadmap: see `docs/TASK_LIST_2026-04-25.md` (Phase 691-720 master)

---

*Last updated: 2026-04-26*
