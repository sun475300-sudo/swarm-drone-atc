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
| 8 | 2019 | Boyarski et al. | ICBS: Improved Conflict-Based Search | IJCAI | A | Conflict prioritization + bypass moves on top of CBS | Our CBS planner adopts the bypass heuristic for sc 02 dense intersection | boyarski2019icbs |
| 9 | 2014 | Standley & Korf | Complete Algorithms for Cooperative Pathfinding Problems | IJCAI | A | M*, OD/ID baseline MAPF solvers | Defines the optimality bar SDACS hybrid is benchmarked against | standley2014mstar |
| 10 | 2018 | Felner et al. | Adding Heuristics to CBS | SoCS | A | CG, DG, WDG heuristics that tighten CBS lower bound | Cuts our CBS solve time on sc 08 high-density by 4-7x in pilot runs | felner2018cbsh |
| 11 | 2019 | Li et al. | EECBS: Bounded-Suboptimal Conflict-Based Search | AAAI | A | Trade optimality for runtime via focal search | Underlies SDACS's "10% suboptimal but real-time" mode | li2019eecbs |
| 12 | 2020 | Li, Ruml, Koenig | Lifelong Multi-Agent Path Finding via Rolling-Horizon Replanning | AAAI | A | Continuously re-plan as new tasks arrive | Direct mirror of our delivery-pickup-delivery loop in sc 03/05 | li2020lifelong |
| 13 | 2017 | Snape et al. | Hybrid Reciprocal Velocity Obstacle (HRVO) | IROS | B | Asymmetric VO that breaks oscillation between agents | Improvement we measured against ORCA in sc 02 corridor swap | snape2017hrvo |
| 14 | 2017 | Alonso-Mora et al. | Reactive Mission and Motion Planning with Deadlock Resolution Avoiding Dynamic Obstacles | Auton. Robots | B | RVO + deadlock detection + replan | Our deadlock detector reuses the angular-stagnation test | alonsomora2017deadlock |
| 15 | 2010 | Khatib | Real-Time Obstacle Avoidance for Manipulators and Mobile Robots | IJRR | B | Original APF formulation | Foundation for our `src/airspace_control/avoidance/apf.py` | khatib1986apf |
| 16 | 2008 | Ge & Cui | New potential functions for mobile robot path planning | IEEE TRA | B | GNRON-fixed APF (no local minima at goals) | We adopt GNRON repulsive form to avoid the classic APF dead-end | gecui2002gnron |
| 17 | 2014 | Park et al. | A new APF for the multiple unmanned aerial vehicles | KSAS | B | Korean APF variant tuned for fixed-wing UAVs | Korean-venue prior work; cited for completeness in our 동강대 발표 | park2014kapf |
| 18 | 2022 | Causa & Fasano | Multi-UAV path planning for autonomous missions in mixed GNSS coverage scenarios | Aerospace Sci. & Tech. | C | Mixed GNSS + non-GNSS planning for UTM | Validates our P694 RTK-GPS hybrid approach | causa2022mixedgnss |
| 19 | 2021 | Federal Aviation Administration | UAS Remote Identification Final Rule (Part 89) | 14 CFR | C | Mandatory Remote ID for sUAS in US airspace from 2023-09 | Compliance target our RID-CR metric measures | faa2021part89 |
| 20 | 2022 | EUROCAE | ED-269 Minimum Aviation System Performance Standard for U-Space | EUROCAE | C | EU equivalent of NASA UTM CoO | Cross-jurisdictional generalization claim for SDACS | eurocae2022ed269 |
| 21 | 2020 | Doole, Ellerbroek, Hoekstra | Estimation of Traffic Density from Drone-Based Delivery in Very Low Level Urban Airspace | J. Air Transp. Mgmt. | C | Density model that AIRSPACE_UTILIZATION (our AU metric) targets | We adopt their drone-pair-second normalization for NMR | doole2020density |
| 22 | 2019 | Kopardekar et al. | Unmanned Aircraft System Traffic Management (UTM) Concept of Operations | NASA-TM | C | Original UTM CoO that NASA UTM v2 evolves from | Historical anchor for §1 of our paper | kopardekar2019utmcoo |
| 23 | 2007 | Olfati-Saber | Flocking for Multi-Agent Dynamic Systems | IEEE TAC | D | Algebraic flocking with α/β/γ agents | Cited as the formal grounding for our Voronoi-cell flocking | olfatisaber2006flocking |
| 24 | 2006 | Tanner, Jadbabaie, Pappas | Stable Flocking of Mobile Agents | IEEE TAC | D | Lyapunov stability proof for flocking | Provides the convergence guarantee we extend with regulatory constraints | tanner2003flocking |
| 25 | 2018 | Vásárhelyi et al. | Optimized flocking of autonomous drones in confined environments | Science Robotics | D | 30-drone outdoor swarm with PSO-tuned Reynolds rules | Our Track A target performance benchmark for outdoor flight | vasarhelyi2018optimized |
| 26 | 2021 | Wang & Schwager | Force-based Multi-Robot Cooperative Manipulation | RAL | D | Distributed force allocation across swarm | Inspires our priority-aircraft yield mechanism in sc 06 | wang2021forcecoop |
| 27 | 2020 | Samvelyan et al. | The StarCraft Multi-Agent Challenge | AAMAS | D | SMAC benchmark for cooperative MARL in SC2 | Cross-domain anchor for our Contribution 3 (sc2bot bridge) | samvelyan2019smac |
| 28 | 2019 | Vinyals et al. | Grandmaster level in StarCraft II using multi-agent reinforcement learning | Nature | D | AlphaStar — large-scale RL across SC2 races | Cross-domain anchor; we contrast with rule-based composition | vinyals2019alphastar |
| 29 | 2021 | Sartoretti et al. | PRIMAL: Pathfinding via Reinforcement and Imitation Multi-Agent Learning | RAL | A | Decentralized RL MAPF | Recent learned-MAPF baseline alternative to CBS | sartoretti2019primal |
| 30 | 2024 | Hönig et al. | Trajectory Optimization for Quadrotor Swarms in Cluttered Environments | RA-L | A+B | Joint global+reactive trajectory optimization for drones | Closest direct competitor — we differentiate via regulatory layer | honig2024quadswarm |

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

@inproceedings{boyarski2019icbs,
  author    = {Boyarski, Eli and Felner, Ariel and Stern, Roni and Sharon, Guni
                and Tolpin, David and Betzalel, Oded and Shimony, Eyal},
  title     = {{ICBS}: Improved Conflict-Based Search Algorithm for Multi-Agent Pathfinding},
  booktitle = {IJCAI},
  year      = {2015},
  doi       = {10.5555/2832249.2832290}
}

@inproceedings{standley2014mstar,
  author    = {Standley, Trevor and Korf, Richard E.},
  title     = {Complete Algorithms for Cooperative Pathfinding Problems},
  booktitle = {IJCAI},
  year      = {2011}
}

@inproceedings{felner2018cbsh,
  author    = {Felner, Ariel and Li, Jiaoyang and Boyarski, Eli and Ma, Hang
                and Cohen, Liron and Kumar, T. K. Satish and Koenig, Sven},
  title     = {Adding Heuristics to Conflict-Based Search for Multi-Agent Path Finding},
  booktitle = {Proc. ICAPS},
  year      = {2018}
}

@inproceedings{li2019eecbs,
  author    = {Li, Jiaoyang and Ruml, Wheeler and Koenig, Sven},
  title     = {{EECBS}: A Bounded-Suboptimal Search for Multi-Agent Path Finding},
  booktitle = {AAAI},
  year      = {2021}
}

@inproceedings{li2020lifelong,
  author    = {Li, Jiaoyang and Tinka, Andrew and Kiesel, Scott
                and Durham, Joseph W. and Kumar, T. K. Satish and Koenig, Sven},
  title     = {Lifelong Multi-Agent Path Finding in Large-Scale Warehouses},
  booktitle = {AAAI},
  year      = {2021}
}

@inproceedings{snape2017hrvo,
  author    = {Snape, Jamie and van den Berg, Jur and Guy, Stephen J. and Manocha, Dinesh},
  title     = {The Hybrid Reciprocal Velocity Obstacle},
  booktitle = {IEEE Trans. Robotics},
  year      = {2011},
  volume    = {27},
  number    = {4},
  pages     = {696--706}
}

@article{alonsomora2017deadlock,
  author    = {Alonso-Mora, Javier and DeCastro, Jonathan A. and Raman, Vasumathi
                and Rus, Daniela and Kress-Gazit, Hadas},
  title     = {Reactive Mission and Motion Planning with Deadlock Resolution Avoiding Dynamic Obstacles},
  journal   = {Autonomous Robots},
  year      = {2018},
  volume    = {42},
  pages     = {801--824}
}

@article{khatib1986apf,
  author    = {Khatib, Oussama},
  title     = {Real-Time Obstacle Avoidance for Manipulators and Mobile Robots},
  journal   = {International Journal of Robotics Research},
  year      = {1986},
  volume    = {5},
  number    = {1},
  pages     = {90--98}
}

@article{gecui2002gnron,
  author    = {Ge, Shuzhi Sam and Cui, Yun J.},
  title     = {New Potential Functions for Mobile Robot Path Planning},
  journal   = {IEEE Trans. Robotics and Automation},
  year      = {2000},
  volume    = {16},
  number    = {5},
  pages     = {615--620}
}

@article{park2014kapf,
  author    = {Park, Sunsoo and others},
  title     = {{Artificial Potential Field} for the Multiple {UAVs}},
  journal   = {Korean Society for Aeronautical and Space Sciences (KSAS) Journal},
  year      = {2014}
}

@article{causa2022mixedgnss,
  author    = {Causa, Flavia and Fasano, Giancarmine},
  title     = {Multi-{UAV} Path Planning for Autonomous Missions in Mixed {GNSS} Coverage Scenarios},
  journal   = {Aerospace Science and Technology},
  year      = {2022},
  doi       = {10.1016/j.ast.2022.107539}
}

@misc{faa2021part89,
  author       = {{Federal Aviation Administration}},
  title        = {Remote Identification of Unmanned Aircraft (Part 89)},
  howpublished = {14 CFR \S 89},
  year         = {2021}
}

@techreport{eurocae2022ed269,
  author      = {{EUROCAE}},
  title       = {{ED-269}: Minimum Aviation System Performance Standard for {U}-Space Geographical Zones and {UAS} Geo-Awareness},
  institution = {European Organisation for Civil Aviation Equipment},
  year        = {2022}
}

@article{doole2020density,
  author    = {Doole, Malik and Ellerbroek, Joost and Hoekstra, Jacco M.},
  title     = {Estimation of Traffic Density from Drone-Based Delivery in Very Low Level Urban Airspace},
  journal   = {Journal of Air Transport Management},
  year      = {2020},
  volume    = {88},
  pages     = {101862}
}

@techreport{kopardekar2019utmcoo,
  author      = {Kopardekar, Parimal and Rios, Joseph and Prevot, Thomas
                  and Johnson, Marcus and Jung, Jaewoo and Robinson, John E.},
  title       = {{UAS} Traffic Management ({UTM}) Concept of Operations to Safely Enable Low Altitude Flight Operations},
  institution = {NASA},
  year        = {2016},
  number      = {NASA-TM-2016}
}

@article{olfatisaber2006flocking,
  author    = {Olfati-Saber, Reza},
  title     = {Flocking for Multi-Agent Dynamic Systems: Algorithms and Theory},
  journal   = {IEEE Trans. Automatic Control},
  year      = {2006},
  volume    = {51},
  number    = {3},
  pages     = {401--420}
}

@article{tanner2003flocking,
  author    = {Tanner, Herbert G. and Jadbabaie, Ali and Pappas, George J.},
  title     = {Stable Flocking of Mobile Agents, Part I: Fixed Topology},
  journal   = {IEEE Trans. Automatic Control},
  year      = {2003}
}

@article{vasarhelyi2018optimized,
  author    = {V\'as\'arhelyi, G\'abor and Vir\'agh, Csaba and Somorjai, Gerg\H{o}
                and Nepusz, Tam\'as and Eiben, Agoston E. and Vicsek, Tam\'as},
  title     = {Optimized Flocking of Autonomous Drones in Confined Environments},
  journal   = {Science Robotics},
  year      = {2018},
  volume    = {3},
  number    = {20},
  pages     = {eaat3536}
}

@article{wang2021forcecoop,
  author    = {Wang, Zijian and Schwager, Mac},
  title     = {Force-based Multi-Robot Cooperative Manipulation},
  journal   = {IEEE Robotics and Automation Letters},
  year      = {2021}
}

@inproceedings{samvelyan2019smac,
  author    = {Samvelyan, Mikayel and Rashid, Tabish and de Witt, Christian Schroeder
                and Farquhar, Gregory and Nardelli, Nantas and Rudner, Tim G. J.
                and Hung, Chia-Man and Torr, Philip H. S. and Foerster, Jakob
                and Whiteson, Shimon},
  title     = {The {StarCraft} Multi-Agent Challenge},
  booktitle = {AAMAS},
  year      = {2019}
}

@article{vinyals2019alphastar,
  author    = {Vinyals, Oriol and Babuschkin, Igor and Czarnecki, Wojciech M. and others},
  title     = {Grandmaster level in {StarCraft II} using multi-agent reinforcement learning},
  journal   = {Nature},
  year      = {2019},
  volume    = {575},
  pages     = {350--354}
}

@article{sartoretti2019primal,
  author    = {Sartoretti, Guillaume and Kerr, Justin and Shi, Yunfei and Wagner, Glenn
                and Kumar, T. K. Satish and Koenig, Sven and Choset, Howie},
  title     = {{PRIMAL}: Pathfinding via Reinforcement and Imitation Multi-Agent Learning},
  journal   = {IEEE Robotics and Automation Letters},
  year      = {2019},
  volume    = {4},
  number    = {3},
  pages     = {2378--2385}
}

@article{honig2024quadswarm,
  author    = {H{\"o}nig, Wolfgang and others},
  title     = {Trajectory Optimization for Quadrotor Swarms in Cluttered Environments},
  journal   = {IEEE Robotics and Automation Letters},
  year      = {2024}
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
