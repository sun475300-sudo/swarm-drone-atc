<div align="center">

# SDACS
## Swarm Drone Airspace Control System

Automated Airspace Control System for Swarm Drones · Capstone Design, Dept. of Drone and Mechanical Engineering, Mokpo National University

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-1.5.0-8b5cf6?style=for-the-badge)](VERSION.md)
[![CI](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/ci.yml/badge.svg)](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/ci.yml)
[![Desktop Build](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/desktop-build.yml/badge.svg)](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/desktop-build.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-live-22c55e?style=for-the-badge&logo=github)](https://sun475300-sudo.github.io/swarm-drone-atc/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[**Launch Web 3D Simulator**](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) · [Download Linux AppImage](https://github.com/sun475300-sudo/swarm-drone-atc/releases/download/v1.5.0/SDACS-Simulator-1.5.0-x86_64.AppImage) · [Build Windows App](#electron-desktop-app-build) · [All Releases](https://github.com/sun475300-sudo/swarm-drone-atc/releases) · [Documentation Index](docs/INDEX.md) · [한국어](README.md)

</div>

![SDACS Swarm Drone Airspace Control 3D Simulator](docs/images/auto/sim_swarm_3d.png)

> **Scope & Nature**: SDACS is a research and educational project centered around a SimPy-based discrete-event simulator and a browser-based 3D visualization tool. The performance metrics, scenarios, and regulatory/standard modules provided here are for simulation or prototype validation purposes only and do not serve as a basis for actual flight safety certification, operational approval, regulatory compliance, or commercial ATC services.

## Run or Download Now

| Path | Public & Validation Status | Start |
|---|---|---|
| Web 3D simulator | Publicly hosted on GitHub Pages | [Launch in browser](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) |
| Linux x64 desktop app | Public v1.5.0 AppImage release | [Direct AppImage download](https://github.com/sun475300-sudo/swarm-drone-atc/releases/download/v1.5.0/SDACS-Simulator-1.5.0-x86_64.AppImage) |
| Windows x64 desktop app | NSIS installer and portable build passed local install/UI/WebGL and CI smoke tests; public release and code signing remain pending | [`scripts/build_desktop.ps1`](#electron-desktop-app-build) |
| macOS desktop app | Intel and Apple Silicon DMGs build in CI; physical-device install, notarization, and public release remain pending | [Desktop Build CI](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/desktop-build.yml) |

> Windows and macOS binaries are not currently permanent public downloads. GitHub Actions artifacts are validation outputs with limited retention, and local Windows outputs are unsigned development builds that may trigger SmartScreen.

## Table of Contents

- [Run or Download Now](#run-or-download-now)
- [Project at a Glance](#project-at-a-glance)
- [Current Status](#current-status)
- [Which Interface Should I Choose?](#which-interface-should-i-choose)
- [Architecture & Data Flow](#architecture--data-flow)
- [Requirements & Installation](#requirements--installation)
- [Quick Start](#quick-start)
- [Full CLI Commands](#full-cli-commands)
- [Scenarios & Configuration](#scenarios--configuration)
- [Build & Deployment](#build--deployment)
- [Outputs & Generated Files](#outputs--generated-files)
- [Validation & CI](#validation--ci)
- [Repository Map](#repository-map)
- [Maturity & Known Limitations](#maturity--known-limitations)
- [Troubleshooting](#troubleshooting)
- [Documentation & Research Assets](#documentation--research-assets)
- [Remaining Tasks](#remaining-tasks)
- [Contributing, Security & Citation](#contributing-security--citation)

## Project at a Glance

SDACS is not a single application, but a suite of tools exploring the same domain at different depths.

| Feature | Implementation | Current Use Case |
|---|---|---|
| Discrete-Event Swarm Simulation | SimPy, NumPy, APF, CBS/A*, CPA-based Collision Prediction/Avoidance | Repeatable research experiments and regression validation |
| Airspace & Drone Models | Drone state machine, priority, comms bus, weather/failure injection, flight clearance | Algorithm unit & integration testing |
| Scenario Execution | 10 runtime YAML scenarios, quick/full Monte Carlo | Normal, high-density, comms loss, weather, intrusion experiments |
| Public Benchmarks | 7 standard + 3 stress suites, ORCA/VO/CBS/SDACS adapters | Reproducible comparison between methods |
| Browser Visualization | Three.js Swarm Drone & Maritime Small Vessel Detection Simulator | Demos, education, UI/interaction experiments |
| Python Visualization | Dash/Plotly 3D Dashboard | Python analysis & demos |
| Service Prototyping | FastAPI, WebSocket, JWT/RBAC, React/Vite | Service architecture prototype for airspace managers |
| Desktop Packaging | Electron Builder for Windows/macOS/Linux | Offline executable creation |
| Reproducibility Assets | Docker, Helm, monitoring configs, CI, canonical hash | Reproducibility & deployment architecture review |

## Current Status

The last repository and desktop-distribution visibility review was completed on **2026-11-01 (KST)**. Verify the latest source and automated validation results against [`main`](https://github.com/sun475300-sudo/swarm-drone-atc/commits/main) and [GitHub Actions](https://github.com/sun475300-sudo/swarm-drone-atc/actions).

| Status | Item | Result |
|:---:|---|---|
| ✅ | Project Version | `1.5.0` in `pyproject.toml` and `package.json` |
| ✅ | Default Branch | `main` — All valid feature and maintenance PRs consolidated |
| ✅ | GitHub Actions | Python 3.10/3.11/3.12 CI, security audit, simulator smoke, Pages deployment, and [3-OS desktop build](https://github.com/sun475300-sudo/swarm-drone-atc/actions/runs/41038538075) gates active |
| ✅ | Design System | v2.0 applied (CSS variable-based Glassmorphism HUD) |
| ✅ | Web Release | [v1.5.0 static Web ZIP](https://github.com/sun475300-sudo/swarm-drone-atc/releases/download/v1.5.0/SDACS-Simulator-Web-v1.5.0.zip) (`SHA-256 b035348e…0e3a8d2`) |
| ✅ | Desktop App | [Linux AppImage is public](https://github.com/sun475300-sudo/swarm-drone-atc/releases/tag/v1.5.0). Windows x64 NSIS and portable outputs passed local install/run/uninstall and WebGL smoke tests on 2026-10-30. macOS is CI-build-only (Windows/macOS public release, signing, and notarization remain pending) |
| ✅ | Python Regression | Python 3.10/3.11/3.12, strict lint, mypy, 80% coverage gates passed |
| ✅ | Federated Browser E2E | Mutual LIVE ghost rendering successful across 2 `ws_bridge` instances and 2 Chromium pages |
| ⏳ | Real-world Validation | Pixhawk, Jetson, RTK, HITL, real-flight, and regulatory approval evidence are future tasks (Phase 261-280) |

## Which Interface Should I Choose?

| Purpose | Recommended Entry Point | Default Port | Required Tools |
|---|---|---:|---|
| Run algorithms fastest | `python main.py simulate` | - | Python |
| Repeat YAML scenarios | `python main.py scenario ...` | - | Python |
| Single benchmark between methods | `python main.py benchmark ...` | - | Python |
| Most complete visual demo | `python scripts/serve.py` | 8123 | Python + Browser |
| Python 3D Dashboard | `python main.py visualize` | 8050 | Python |
| API & WebSocket Integration | `python main.py api` | 8000 | Python API dependencies |
| React Airspace Manager UI | `cd frontend && npm run dev` | 3000 | Node.js |
| Standalone Desktop App | Public Linux AppImage or locally built Windows installer/portable EXE | - | Prebuilt files require no separate runtime |
| Full-stack Container Demo | `docker compose up` | 8050 | Docker |

## Architecture & Data Flow

```mermaid
flowchart LR
    CFG["YAML Config/Scenarios<br/>config/"] --> CLI["CLI<br/>main.py"]
    CLI --> SIM["SwarmSimulator<br/>simulation/simulator.py"]
    SIM --> AGENT["DroneAgent<br/>10 Hz State Machine"]
    SIM --> CTRL["AirspaceController<br/>1 Hz Airspace Control"]
    SIM --> APF["APF·CPA·CBS/A*<br/>Collision Prediction/Avoidance"]
    SIM --> COMMS["CommunicationBus<br/>Latency/Loss Model"]
    AGENT --> ANALYTICS["SimulationAnalytics<br/>KPIs & Events"]
    CTRL --> ANALYTICS
    APF --> ANALYTICS
    COMMS --> ANALYTICS
    ANALYTICS --> OUT["Terminal/JSON/Reports<br/>data/results, results/"]
    SIM --> DASH["Dash/Plotly"]
    SIM --> API["FastAPI·WebSocket"]
    API --> REACT["React/Vite Admin UI"]
    WEB["Three.js Static Simulator"] --> PAGES["GitHub Pages·Electron"]
```

## Requirements & Installation

### Supported Environments

- Python **3.10 or higher**; CI validation covers 3.10, 3.11, 3.12
- Node.js **22 recommended**; Electron & browser E2E CI uses Node 22
- Latest Chromium-based browser; E2E uses Playwright Chromium

### Python Development Environment

```bash
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc

python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Quick Start

### 1. Python Simulation

```bash
# 60 seconds, 20 drones, seed 42
python main.py simulate --duration 60 --drones 20 --seed 42

# List and run named scenarios
python main.py scenario --list
python main.py scenario weather_disturbance --runs 3 --seed 42 --duration 120
```

### 2. Browser Simulator (Web Version)

```bash
# Serve the repository root via HTTP and open the swarm simulator
python scripts/serve.py
```

The browser simulator uses built-in demo data by default. To receive live snapshots from the Python `SwarmSimulator`, run the WebSocket bridge separately and specify `?live=1` in the URL.

```bash
# Terminal 1: Default ws://127.0.0.1:8765
python -m pip install websockets
python simulation/ws_bridge.py --drones 50

# Terminal 2: Static Simulator
python scripts/serve.py --no-browser --port 8123
# Open http://127.0.0.1:8123/swarm_3d_simulator.html?live=1 in your browser
```

### 3. Desktop App

Linux x64 users can download the public [v1.5.0 AppImage](https://github.com/sun475300-sudo/swarm-drone-atc/releases/download/v1.5.0/SDACS-Simulator-1.5.0-x86_64.AppImage) and run it.

```bash
chmod +x SDACS-Simulator-1.5.0-x86_64.AppImage
./SDACS-Simulator-1.5.0-x86_64.AppImage
```

Windows builds produce `SDACS-Simulator-1.5.0-portable.exe` for no-install use and `SDACS-Simulator-1.5.0-x64.exe` for normal installation. There is no permanent public Windows download yet; create them with the [Electron desktop build](#electron-desktop-app-build) instructions below. These unsigned development builds may trigger SmartScreen.

## Full CLI Commands

Run `python main.py <command> --help` to check the latest options for all commands.

| Command | Purpose | Example |
|---|---|---|
| `simulate` | Single SimPy run & KPI summary | `python main.py simulate --duration 60 --drones 20 --seed 42` |
| `scenario` | List & repeat runtime YAML scenarios | `python main.py scenario high_density --runs 5` |
| `monte-carlo` | Quick/full sweep of config combinations | `python main.py monte-carlo --mode quick` |
| `benchmark` | Fixed scenario/method/seed comparison | `python main.py benchmark --scenario 01_corridor_crossing --method sdacs_hybrid --seed 0` |
| `visualize` | Dash/Plotly 3D Dashboard | `python main.py visualize --port 8050 --drones 30` |
| `visualize-3d` | Open local Three.js simulator | `python main.py visualize-3d` |
| `api` | FastAPI·WebSocket backend | `python main.py api --host 127.0.0.1 --port 8000` |
| `ops-report` | Delivery/traffic/weather/compliance ops report bundle | `python main.py ops-report --scenario demo --seed 42` |

## Scenarios & Configuration

Scenarios are defined in the `config/` directory. Key scenarios include:
- `default`: Default settings (50 drones)
- `high_density`: High-density traffic (150 drones)
- `emergency_failure`: Emergency failure injection (80 drones)
- `weather_disturbance`: Severe weather conditions (100 drones)
- `route_conflict`: Focus on route crossing and collision avoidance (100 drones)

## Build & Deployment

### Static Web Build
```bash
python scripts/build_simulator.py
# Static assets are generated in the build/simulator/ folder
```

### Electron Desktop App Build

On Windows, one command builds both the NSIS installer and portable EXE. The default package uses the built-in JavaScript simulation engine and runs offline without Python.

```powershell
npm ci
powershell -ExecutionPolicy Bypass -File scripts/build_desktop.ps1 -Clean

# Optional: bundle the Dash/Python backend (Python 3.11+ and substantial disk space required)
powershell -ExecutionPolicy Bypass -File scripts/build_desktop.ps1 -Clean -IncludePython
```

Direct commands for other operating systems:

```bash
npm ci
npm run dist:linux   # Linux AppImage
npm run dist:win     # Windows NSIS + portable EXE
npm run dist:mac     # macOS DMG
```

## Outputs & Generated Files

| Action | Recommended Location | Content |
|---|---|---|
| `simulate --output` | User-specified JSON | Single run KPIs |
| Monte Carlo | `data/results/` | Sweep results |
| `benchmark --output` | `results/` | JSON by method/scenario/seed |
| `ops-report` | `data/e2e_reports/` | JSON, Markdown, manifest JSON |
| Web Build | `build/simulator/` | Static deployment package |
| Electron Windows Build | `dist-desktop/` | `*-x64.exe` installer, `*-portable.exe`, and `win-unpacked/` validation tree |

## Validation & CI

### Python Quality Gates
```bash
ruff check src/ simulation/
mypy src/
python -m pytest tests/ -q
```

### Web & Frontend E2E
```bash
npm run pw:install
npm run test-server &
$env:SIM_URL='http://localhost:8123/swarm_3d_simulator.html'
npm run smoke
```

### Desktop App Smoke

[![Desktop Build](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/desktop-build.yml/badge.svg)](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/desktop-build.yml)

```powershell
npm run pack
npm run smoke:desktop:app

# After npm run dist:win, verify that the portable wrapper launches the real Electron process
node tests/e2e/smoke_desktop_app.mjs --portable
```

The packaged-app check validates Electron preload availability, the canonical simulator entry point, WebGL draw calls, a 50-drone initial scenario, a nonblank capture, advancing simulation time, and page errors. The portable check verifies that the extraction wrapper launches the real Electron process and cleans up the process tree.

## Repository Map

| Path | Responsibility | See Also |
|---|---|---|
| [`main.py`](main.py) | CLI entry point | CLI examples, tests, README |
| [`simulation`](simulation) | SimPy execution engine & research modules | `config/`, `tests/`, Maturity |
| [`src/airspace_control`](src/airspace_control) | Core airspace control domain | controller, planning, avoidance, comms |
| [`benchmarks`](benchmarks) | Public comparison suite | manifest schema, adapters, results |
| [`api`](api) | FastAPI, JWT/RBAC, WebSocket | `frontend/`, API tests |
| [`frontend`](frontend) | React Admin UI | Vite proxy, API contracts |
| [`desktop`](desktop) | Electron shell | Root package, static assets |
| [`tests`](tests) | Python & E2E regression | pytest markers, Playwright |
| [`docs`](docs) | Design, research, operations documentation | Doc dates vs code consistency |

## Maturity & Known Limitations

- The SimPy Python engine, Three.js web engine, and maritime simulator are separate runtimes; their state and physical models do not synchronize automatically.
- The presence of hardware, SITL, HITL, regulatory, and standard modules does not imply actual equipment connection, institutional approval, or completed certification.
- While `benchmarks/` contains manifests and descriptions, the scenario-specific `expected_results.yaml` mentioned in some older documents is not present in the current tree.
- Windows and macOS desktop packages are not currently code-signed or notarized. Keep locally validated research builds distinct from public, signed distribution releases.

## Troubleshooting

- **HTML opened but Three.js is not displaying**: Serve via HTTP instead of `file://` (`python scripts/serve.py`).
- **Korean logs are garbled**: Set `$env:PYTHONIOENCODING='utf-8'` in Windows Terminal or PowerShell before running.
- **Web build integrity check fails**: Do not manually edit copies after modifying the root master HTML; re-run `python scripts/build_simulator.py`.

## Documentation & Research Assets

| Purpose | Document |
|---|---|
| Full Documentation Index | [docs/INDEX.md](docs/INDEX.md) |
| System Architecture | [docs/architecture.md](docs/architecture.md) |
| Reproducibility Guide | [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) |
| Paper Contribution & Submission Prep | [docs/paper/contribution_outline.md](docs/paper/contribution_outline.md) |
| Commercialization & Industry Track | [docs/track_f/README.md](docs/track_f/README.md) |
| Long-term Roadmap | [ROADMAP.md](ROADMAP.md) |
| External Execution & Evidence Checklist | [docs/EXTERNAL_EXECUTION_CHECKLIST.md](docs/EXTERNAL_EXECUTION_CHECKLIST.md) |

## Remaining Tasks

The following **external execution and operations tasks** remain after the code, local Windows packaging, and public GitHub-state review on 2026-11-01. The presence of implementation files in the repository does not prove field validation, submission, or certification.

- [ ] **Repository Operations & Distribution Channels**
  - Add a repository description, Pages homepage, and `drone`, `simulation`, `utm`, `electron`, and `airspace` topics in GitHub About
  - Enable `main` branch protection (require CI and reviews)
  - Sign and publish the Windows EXE; validate, sign/notarize, and publish the macOS DMG on physical hardware
  - Publish `@sdacs/core` and the Python wheel to their package registries
  - Automatically publish the representative-scenario screenshot and video gallery
- [ ] **Research Papers & DOI**
  - Create the Zenodo archive and DOI, then update `CITATION.cff` and the paper
  - Re-run fixed-seed baselines and ablations and cross-check every paper figure
  - Submit to IROS or the selected venue and file through the K-UTM standards channel
- [ ] **Real-world Environment & Hardware (Phase 261-380)**
  - Integrate Pixhawk, Jetson, RTK hardware-in-the-loop (SITL/HITL)
  - Build bi-directional digital twin (link real flight data with simulator)
- [ ] **Commercialization & External Cooperation (Phase 410-499)**
  - Contribute to GUTMA and collaborate with overseas pilot organizations
  - Secure budget and execute 90-day proof-of-concept pilot in Jeonnam islands
  - Prepare for handover to the next generation capstone team

## Contributing, Security & Citation

- Contribution Guidelines: [CONTRIBUTING.md](CONTRIBUTING.md)
- Report Security Vulnerabilities: [SECURITY.md](SECURITY.md)
- License: [MIT License](LICENSE)
- Project Citation Metadata: [CITATION.cff](CITATION.cff)

The automation and simulators in this repository are intended for research, education, and prototyping. Actual operations that may affect people, aircraft, or property require independent safety validation, regulatory approval, security assessment, and operational accountability frameworks.
