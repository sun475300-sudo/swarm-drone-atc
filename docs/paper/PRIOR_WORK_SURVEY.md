# Prior Work Survey — SDACS

**Phase:** P702
**Target venues:** IROS 2026 · ICRA 2027 · AIAA SciTech 2027
**Target size:** ≥ 30 references
**Last updated:** 2026-04-19

---

## 1. Survey Scope

SDACS positions itself at the intersection of four research areas.
Any related work should be classified into one of these buckets:

| Bucket | Scope | Primary venues |
|--------|-------|----------------|
| **A. Multi-Agent Path Finding (MAPF)** | CBS, A*/PRM variants, conflict resolution | AAAI, IJCAI, ICAPS |
| **B. Reactive Collision Avoidance** | VO/ORCA, APF, BVC, RVO | ICRA, IROS, RA-L |
| **C. UTM / UAS Traffic Management** | Airspace partitioning, conformance monitoring, Remote ID | AIAA SciTech, DASC, JATM |
| **D. Swarm Behavior & Control** | Boids, consensus, formation, flocking | IROS, Swarm Intelligence, Nature MI |

Our contribution claim (see `P701_CONTRIBUTION_POINTS.md` — TODO) is the *hybrid* of (A) global planning + (B) reactive layer + (C) regulatory conformance, benchmarked on shared scenarios.

---

## 2. Reference Table Template

> Add one row per paper. Use `TODO` for fields you still need to extract.

| # | Year | Authors | Title | Venue | Bucket | Core idea (1 sentence) | Why it matters for SDACS | Citation key |
|---|------|---------|-------|-------|--------|------------------------|--------------------------|--------------|
| 1 | 2015 | Sharon et al. | Conflict-Based Search for Optimal Multi-Agent Path Finding | AIJ | A | Two-level CBS: high-level constraint tree + low-level A* | Baseline for our CBS implementation; we extend with time-windows | sharon2015cbs |
| 2 | 2011 | van den Berg et al. | Reciprocal n-body Collision Avoidance | ISRR | B | ORCA geometric velocity constraints | Baseline reactive layer we compare against APF | vandenberg2011orca |
| 3 | 1998 | Fiorini & Shiller | Motion Planning in Dynamic Environments Using Velocity Obstacles | IJRR | B | VO formulation | Theoretical foundation for ORCA and our APF hybrid | fiorini1998vo |
| 4 | 1986 | Reynolds | Flocks, Herds, and Schools: A Distributed Behavioral Model | SIGGRAPH | D | Boids three-rule model | Reference for our swarm cohesion layer | reynolds1986boids |
| 5 | 2020 | NASA | UTM Concept of Operations v2 | NASA-CoO | C | Regulatory framework for sub-400 ft UAS ops | Framework we claim conformance with | nasa2020utm |
| 6 | 2021 | FAA | LAANC System Architecture | FAA | C | Low-Altitude Authorization and Notification | Our `faa_laanc.py` implements this interface | faa2021laanc |
| 7 | 2021 | ASTM | F3411-22a Remote ID Standard | ASTM | C | Broadcast/Network Remote ID spec | Our `remote_id.py` implements this | astm2021f3411 |
| 8 | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| 9-30 | | | | | | | | |

---

## 3. Search Protocol

To hit 30+ references, run these queries and triage results:

### 3.1 Google Scholar / Semantic Scholar
```
"multi-agent path finding" drone UAV             → Bucket A
"conflict-based search" OR "CBS" UAV             → Bucket A
"velocity obstacle" OR "ORCA" UAV multi          → Bucket B
"artificial potential field" UAV swarm           → Bucket B
"UAS traffic management" OR UTM                  → Bucket C
"remote ID" F3411 detect-and-avoid               → Bucket C
"drone swarm" control formation                  → Bucket D
"consensus algorithm" multi-UAV                  → Bucket D
```

### 3.2 arXiv
- `cs.RO` + `cs.MA` cross-listed, 2022-2026 → recent MAPF advances
- `cs.SY` + keyword `UAV` → control-theoretic papers

### 3.3 IEEE Xplore
- Conferences: ICRA, IROS, RA-L, ACC, CDC, DASC, JATM
- Filter year ≥ 2020

### 3.4 Korean venues (for caption 4/23 학술대회 reference)
- 한국로봇학회 (KRoC), 한국항공우주학회 (KSAS)
- 동강대 학술대회 2026 proceedings (본인 발표 포함)

---

## 4. Triage Criteria (keep / drop)

Keep a paper if ANY of:
- Published ≥ 2020 AND cited ≥ 20 times, OR
- Foundational (pre-2020 but defines a core method we build on — CBS, ORCA, VO, APF, Boids), OR
- Directly compares UTM compliance (C bucket — always keep).

Drop if:
- Survey paper of a survey (2nd-order aggregator)
- Pure simulation with no real-world validation AND no mathematical contribution
- Preprint > 3 years without any citation

---

## 5. Citation File (BibTeX seed)

```bibtex
@article{sharon2015cbs,
  author  = {Sharon, Guni and Stern, Roni and Felner, Ariel and Sturtevant, Nathan R.},
  title   = {Conflict-based search for optimal multi-agent pathfinding},
  journal = {Artificial Intelligence},
  volume  = {219},
  pages   = {40--66},
  year    = {2015},
  doi     = {10.1016/j.artint.2014.11.006}
}

@inproceedings{vandenberg2011orca,
  author    = {van den Berg, Jur and Guy, Stephen J. and Lin, Ming and Manocha, Dinesh},
  title     = {Reciprocal n-body Collision Avoidance},
  booktitle = {Robotics Research: The 14th International Symposium {ISRR}},
  year      = {2011},
  pages     = {3--19}
}

@article{fiorini1998vo,
  author  = {Fiorini, Paolo and Shiller, Zvi},
  title   = {Motion Planning in Dynamic Environments Using Velocity Obstacles},
  journal = {International Journal of Robotics Research},
  volume  = {17},
  number  = {7},
  pages   = {760--772},
  year    = {1998}
}

@inproceedings{reynolds1986boids,
  author    = {Reynolds, Craig W.},
  title     = {Flocks, Herds and Schools: A Distributed Behavioral Model},
  booktitle = {SIGGRAPH},
  year      = {1987},
  pages     = {25--34}
}
```

---

## 6. Open Items

- [ ] Fill rows 8-30 via the Section 3 queries.
- [ ] For each paper, note *exactly* which of SDACS's 10 Phase 601-610 modules it overlaps with (use `grep -l` on `src/`).
- [ ] Decide positioning: "hybrid" paper vs. "novel regulatory conformance layer" paper.
- [ ] Keep a running diff of which references sc2bot swarm-control project shares (if paper becomes joint).

---

## 7. Joint-Work Angle (sc2bot bridge)

If the 동강대 학술대회 발표를 두 프로젝트 융합으로 가져간다면, survey에 한 bucket을 추가:

| Bucket E | Scope | Venues |
|----------|-------|--------|
| **E. Game-based Swarm RL** | StarCraft II swarm micro, Hierarchical RL, emergent coordination | AAAI, NeurIPS, AIIDE |

Starter references:
- Vinyals et al., AlphaStar (Nature 2019) — large-scale RL in SC2
- Samvelyan et al., StarCraft Multi-Agent Challenge (SMAC) — MARL benchmark
- Ecoffet et al., First Return Then Explore (Nature 2021) — exploration in RL

→ Bridge claim: *"swarm coordination principles transfer across simulated (SC2) and physical (UAV) domains when expressed as constraint-satisfaction + potential-field composition."*
