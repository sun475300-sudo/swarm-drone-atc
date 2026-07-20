<div align="center">

# SDACS — Swarm Drone Airspace Control System

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1-4CAF50?style=for-the-badge)](https://simpy.readthedocs.io/)
[![Dash](https://img.shields.io/badge/Dash-4.1-00A0DC?style=for-the-badge&logo=plotly)](https://dash.plotly.com/)
[![NumPy](https://img.shields.io/badge/NumPy-2.0-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Mokpo National University, Dept. of Drone Mechanical Engineering — Capstone Design (2026)**

🌐 **Language:** **English** · [한국어 (Korean)](README.md)

[**⚡ Quick Start**](#quick-start) · [**🛰 Live 3D Simulator**](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) · [**🚢 Maritime Simulator**](https://sun475300-sudo.github.io/swarm-drone-atc/maritime_detection_simulator.html) · [**🗺 Roadmap**](ROADMAP.md)

</div>

> **Scope & honesty note.** SDACS is a **research-grade discrete-event simulator** with a browser-based 3D visualizer. The results reported below are simulation measurements obtained under fixed seeds; they constitute an improvement baseline for research, **not** a safety certification. A live API-maturity classifier (`window._sdacs.maturityReport()`) discloses which capabilities are production-grade versus deterministic mocks. See [`docs/TECH_DEBT_LEDGER.md`](docs/TECH_DEBT_LEDGER.md) for the full technical-debt disclosure.

---

## What is SDACS?

> *"Instead of installing radar on the ground, what if the drones themselves became the radar?"*

SDACS starts from this premise. A team of roughly 20 control drones takes off and self-organizes into a mesh-connected surveillance fabric — a **mobile virtual radar dome** — that autonomously monitors low-altitude urban airspace and prevents collisions before they happen. In short, it is a **"traffic-light system for the sky":** just as road traffic lights prevent vehicle collisions, SDACS automatically deconflicts drone traffic in the air.

### The Problem

Hundreds of thousands of drones already share the low-altitude airspace below 120 m AGL for delivery, agriculture, and inspection, with Urban Air Mobility (UAM) arriving by 2030. Existing approaches each have a structural limitation that SDACS addresses:

| System | Core limitation | SDACS approach |
|---|---|---|
| **K-UTM** (centralized control) | Single server failure halts all control | Distributed architecture — 90% remains operational even if 10% of drones fail |
| **Fixed radar** | Hundreds of thousands of USD + 6 months; ~67% urban low-altitude blind spots | 10 drones deployable in 30 minutes, ~90% cost reduction |
| **Drone-show choreography** | Executes pre-planned paths only; cannot react to contingencies | AI real-time autonomous decisions; emergent collective intelligence |

> **Drone show vs. SDACS.** A drone show is *top-down* — a central plan is executed by each drone. SDACS is *bottom-up* — drones follow simple local rules, communicate, and let collective intelligence emerge.

### Our Approach

1. **Replace radar with drones** — emergency deployment within 30 minutes, no fixed infrastructure (6 months → 30 minutes).
2. **End-to-end automation from detection to avoidance** — preemptive conflict prediction 90 s ahead, response within ~1 s.
3. **Scale coverage by adding drones** — distributed architecture, fewer operators required.

---

## Key Results

All figures are simulation measurements under fixed seeds (research baseline, not certification).

| Metric | Value | Description |
|---|---|---|
| **Collision resolution** | **100% (20 drones)** | 20 drones / 600 s: 0 collisions; 50 drones: 97.9%; 100 drones: 98.9% |
| **Route efficiency** | **≤ 1.12** | Passes the ≤ 1.15 SLA across all swarm sizes (600 s runs) |
| **Prediction lookahead** | **90 s** | CPA-based preemptive conflict detection at 1 Hz |
| **Advisory latency** | **< 1 s** (measured: 0.8 s) | 6 advisory types: CLIMB / DESCEND / TURN_LEFT / TURN_RIGHT / EVADE_APF / HOLD |
| **Multi-language coverage** | **50+ languages** | Phase 521–660: Zig, Rust, Go, C++, Kotlin, Nim, OCaml, Swift, TS, Haskell, Julia, Ada, Fortran, Prolog, and more |
| **Monte Carlo validation** | **38,400 runs** | 384 configurations × 100 seeds |
| **Scenario coverage** | **63 scenarios** | 7 metropolitan urban environments + extreme weather + intrusion + GPS jamming + large-scale delivery |
| **Concurrent drones** | **100+** | See swarm-scale table below |
| **Deployment time** | **30 min** | No fixed infrastructure required |

> Representative run (`100 drones / 60 s / seed 42`, local re-verification 2026-06-18): **45 collisions · 87 near misses · 95.9% conflict resolution**. Automated test collection: **9,591 collected / 0 collection errors** (2026-07-21) across 1,118 Python files and 306 test files.

---

## System Architecture

SDACS is organized into four independent layers, each with a clear responsibility and interface, independently testable.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Layer 4: User Interface                      │
│                CLI (main.py) + Dash 3D Visualizer                │
├─────────────────────────────────────────────────────────────────┤
│                   Layer 3: Simulation Engine                     │
│          SwarmSimulator + WindModel + Monte Carlo Engine         │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 2: Control System                       │
│     AirspaceController (1 Hz) + Priority Queue + Advisory Gen     │
├─────────────────────────────────────────────────────────────────┤
│                     Layer 1: Drone Agents                        │
│             DroneAgent (10 Hz SimPy process per drone)           │
└─────────────────────────────────────────────────────────────────┘
```

- **Layer 1 — Drone Agent.** Each drone is a SimPy discrete-event process updating position / velocity / battery at 10 Hz, driven by a flight state machine (`GROUNDED → TAKEOFF → ENROUTE → EVADING/HOLDING → LANDING → GROUNDED`, with an `EMERGENCY` branch off `EVADING` for RTL / forced landing). File: `simulation/drone_agent.py` (`DroneAgent`), spawned per drone by `simulation/simulator.py`.
- **Layer 2 — Airspace Controller.** Collects all active drone positions at 1 Hz, evaluates collision risk, and issues advisories. CPA pairwise scan (O(N²), 90 s lookahead), Voronoi airspace partitioning (10 s refresh), geometric 6-type resolution advisories, and wind-coupled dynamic separation (1.0×–1.6× across 5/10/15 m/s bands). File: `src/airspace_control/controller/airspace_controller.py`.
- **Layer 3 — Simulation Engine.** SimPy-based engine supporting environmental conditions and fault injection. `SwarmSimulator` (canonical engine), `WindModel` (constant / variable-gust / shear), Monte Carlo (384 configs × 100 seeds = 38,400 runs), and fault injection (motor / battery / GPS failure, comms loss, rogue intrusion). Files: `simulation/simulator.py`, `simulation/wind_model.py`, `simulation/monte_carlo.py`.
- **Layer 4 — User Interface.** CLI (`main.py`: `simulate`, `scenario`, `monte-carlo`, `benchmark`, `visualize`, `visualize-3d`, `api`, `ops-report`, `chatbot`), a Dash + Plotly real-time 3D dashboard, and a standalone Three.js [browser simulator](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) (63 scenarios, WebGPU/Web Worker APF acceleration, replay/timeline, an ATC command console, and a `window._sdacs` automation API).

### Five-Layer Safety Net

Five defenses protect in depth — **if one fails, the next still guarantees safety**:

| Layer | Analogy | Description |
|---|---|---|
| **1. Pre-flight path planning** | Navigation | Compute conflict-free optimal routes before departure (CBS) |
| **2. 90 s conflict prediction** | Forward radar | Predict whether the current trajectory meets another drone 90 s ahead (CPA) |
| **3. Magnetic auto-avoidance** | Like-pole magnets | A repulsive force automatically engages as drones approach (APF) |
| **4. Emergency brake** | Hard stop | A last-resort emergency stop even if all avoidance fails |
| **5. Controller / UTM oversight** | Air traffic control | Centralized advisories and airspace-level oversight |

---

## Core Algorithms

The collision-avoidance pipeline has three stages — **detect → decide → act**.

**1. Collision detection.** CPA (closest point of approach, O(N²) per tick), Voronoi tessellation (O(N log N) cell-intrusion detection), geofence monitor (auto-RTL on 90% boundary breach), and intrusion detection (unregistered/ROGUE profiles).

**2. Conflict resolution.** APF (artificial potential field — attractive goal + repulsive obstacle fields, auto-switching to `APF_PARAMS_WINDY` above 10 m/s), CBS (conflict-based search for optimal multi-agent paths), a resolution-advisory generator (geometric classification into 6 advisory types), and A\* energy-aware path replanning.

**3. Formation control.** Graph-Laplacian consensus (leader–follower, V / line / circle / grid), Reynolds boids (separation / alignment / cohesion), and ORCA (optimal reciprocal collision avoidance in velocity space).

### Swarm-scale performance

| Drones | Resolution | Bottleneck | Mitigation |
|---|---|---|---|
| 10 (baseline) | 100% | none | default operation |
| **50** | **97.9%** | none | **recommended swarm size** |
| 100 | 98.9% | comm bandwidth | edge-computing distribution |
| 200 | 70% | decision compute | leader–follower hierarchy |
| 200+ | ≤ 50% | state sync failure | partition into local swarms of 10–20 |

### Conflict-resolution rate

The project-canonical formula is `resolution_rate = 1 − collisions / (conflicts + collisions)`.

---

## Project Structure

```
swarm-drone-atc/
├── simulation/            # Layers 1 & 3: core runtime + experiments (586 modules)
│   ├── simulator.py       # SwarmSimulator orchestrator
│   ├── drone_agent.py     # DroneAgent 10 Hz SimPy process
│   ├── wind_model.py      # constant / variable-gust / shear
│   ├── monte_carlo.py     # 384 configs × 100 seeds
│   └── ws_bridge.py       # Python → browser WebSocket bridge
├── src/airspace_control/  # Layer 2: AirspaceController, avoidance, planning
├── visualization/         # Dash / Plotly 3D visualizer
├── docs/                  # GitHub Pages + plans + certification docs
├── tests/                 # 306 test files + e2e smoke
├── config/                # default_simulation.yaml, monte_carlo.yaml, scenario_params/
├── main.py                # CLI entry point
└── swarm_3d_simulator.html# standalone Three.js web simulator
```

Configuration precedence: `config/default_simulation.yaml` → `config/scenario_params/{name}.yaml` → CLI arguments, merged by `SwarmSimulator._deep_merge()`. The drone-count key read by the engine is `drones.default_count`.

---

## Quick Start

### Prerequisites
- Python 3.10+ (3.10 / 3.11 / 3.12 are tested in CI)
- `pip install -r requirements.txt`

### Run

```bash
pytest tests/ -v                          # full test suite
python main.py simulate --duration 60     # basic simulation
python main.py scenario high_density      # run a scenario
python main.py monte-carlo --mode quick   # Monte Carlo sweep
python main.py visualize                  # Dash 3D dashboard (localhost:8050)
```

### Run with Docker

```bash
docker build -t sdacs .
docker run --rm -p 8050:8050 sdacs        # dashboard on http://localhost:8050
```

### Browser simulator

> ⚠️ **Do not open the HTML file by double-clicking it (`file://`).** The simulator loads three.js as an ES module, so opening the file directly is blocked by the browser's CORS policy and **nothing will render.** Use one of the methods below.

| Method | Command | Notes |
|---|---|---|
| **① Double-click (Windows)** | `RUN_SIMULATOR.bat` in the repo root | Starts a local server and opens the browser automatically |
| **② CLI (any OS)** | `python scripts/serve.py` (swarm) · `python scripts/serve.py --page maritime` (maritime) | Opens `http://localhost:8123` |
| **③ Desktop app** | Install the [v1.5.0 build](docs/V1_5_0_RELEASE_INSTRUCTIONS.md) | No server needed, bundled with Electron |
| **④ Online** | [Hosted live version](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) | Runs instantly, no install |

No build step required.

---

## Testing

CI (`.github/workflows/ci.yml`) runs a Python 3.10 / 3.11 / 3.12 matrix: syntax lint (`flake8 --select=E9,F63,F7,F82`), `pytest tests/ -v --tb=short --timeout=60`, core-module import checks, and PR smoke/perf reports. Headless browser smoke tests for the simulators live under `tests/e2e/` and run via `.github/workflows/sim-smoke.yml`.

---

## Research Framework — Why StarCraft II?

> *"Can swarm-intelligence algorithms learned in StarCraft II be effectively transferred to real drone airspace control?"*

SDACS's core algorithms were first validated in a [StarCraft II bot project](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot). Zerg unit swarming maps to UAV formation flight; simultaneous threat response maps to multi-target tracking and anti-swarm; decision-making under imperfect information maps to Bayesian situational awareness.

---

## Roadmap

Completed on `main`: the SimPy `SwarmSimulator` + `DroneAgent` + `AirspaceController` + `CommunicationBus` stack, the Dash/Plotly 3D dashboard, the Three.js web simulator (63 scenarios, 7 metropolitan environments, extreme weather, intrusion, GPS spoofing), WebGPU/Web Worker APF acceleration, replay/timeline, PNG/CSV/KPI export, large-scale InstancedMesh scenarios (1K/5K/10K), the `ws_bridge.py` LIVE hook, the `_sdacs` automation API, and KO/EN/JA/ZH internationalization.

Known gaps include hardware-in-the-loop flight validation (pending physical Pixhawk/Jetson/RTK hardware), real-experiment paper figures, and LIVE-source UI hardening. The detailed phase plan is tracked in [`ROADMAP.md`](ROADMAP.md) and [`STATUS_REPORT.md`](STATUS_REPORT.md).

---

## How to Cite

```bibtex
@misc{jang2026sdacs,
  title        = {SDACS: A Distributed Swarm Drone Airspace Control System},
  author       = {Jang, Sunwoo},
  year         = {2026},
  howpublished = {Capstone Design, Dept. of Drone Mechanical Engineering,
                  Mokpo National University},
  note         = {Research-grade discrete-event simulator},
  url          = {https://github.com/sun475300-sudo/swarm-drone-atc}
}
```

---

## References

1. **SimPy** — Discrete-event simulation for Python. <https://simpy.readthedocs.io>
2. **Artificial Potential Field** — Khatib, O. (1986). Real-time obstacle avoidance for manipulators and mobile robots. *IJRR*.
3. **Conflict-Based Search** — Sharon, G. et al. (2015). Conflict-based search for optimal multi-agent pathfinding. *AIJ*.
4. **CPA** — Kuchar, J. K. & Yang, L. C. (2000). A review of conflict detection and resolution modeling methods. *IEEE T-ITS*.
5. **Voronoi Tessellation** — Aurenhammer, F. (1991). Voronoi diagrams — a survey of a fundamental geometric data structure. *ACM Computing Surveys*.
6. **Reynolds Boids** — Reynolds, C. W. (1987). Flocks, herds and schools: a distributed behavioral model. *SIGGRAPH*.
7. **ORCA** — van den Berg, J. et al. (2011). Reciprocal n-body collision avoidance. *Robotics Research*.

---

## License

MIT License — developed for academic and educational purposes.

> **Note.** A standalone MIT `LICENSE` file is present at the repository root (added 2026-06-25); the MIT badge link above resolves to it. `pyproject.toml` and `package.json` also declare **MIT**.

---

<div align="center">

**Developed by Sunwoo Jang · Mokpo National University, Dept. of Drone Mechanical Engineering**

</div>
