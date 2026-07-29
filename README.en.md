<div align="center">

# SDACS
## Swarm Drone Airspace Control System

A research and education platform for swarm-drone airspace-control simulation.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/ci.yml/badge.svg)](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/ci.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-live-22c55e?style=for-the-badge&logo=github)](https://sun475300-sudo.github.io/swarm-drone-atc/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[Live site](https://sun475300-sudo.github.io/swarm-drone-atc/) · [3D simulator](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) · [Maritime simulator](https://sun475300-sudo.github.io/swarm-drone-atc/maritime_detection_simulator.html) · [Documentation index](docs/INDEX.md) · [한국어](README.md)

</div>

> **Scope and honesty note.** SDACS is a SimPy-based discrete-event simulator with browser 3D visualization tools. Its metrics and scenarios are simulation evidence for research and education; they are not flight-safety certification, operational approval, or a production air-traffic-control service.

## Current status

The repository was audited on **2026-07-30 (KST)**. Use `git log -1 --oneline origin/main` for the current SHA.

| Area | Verified state |
|---|---|
| Default branch | `main`, synchronized with local `main` at audit time |
| GitHub Actions | The latest `main` push completed CI, Security Audit, Canonical Hash Verification, and Pages deployment successfully |
| GitHub Pages | Root, 3D simulator, and maritime simulator returned HTTP 200 |
| Static simulator artifact | `python scripts/build_simulator.py` and `--check` completed successfully; `build/simulator/` was generated |
| Python regression | Latest CI passed on Python 3.10, 3.11, and 3.12 with lint, mypy, and an 80% coverage gate |
| Desktop app | Electron packaging and a three-OS workflow exist, but no SDACS desktop installer is currently published in GitHub Releases |

## System map

| Area | Purpose | Primary paths |
|---|---|---|
| Simulation engine | SimPy environment, drone agents, conflict avoidance, airspace control, weather/comms/fault injection | [simulation/simulator.py](simulation/simulator.py), [simulation/drone_agent.py](simulation/drone_agent.py), [src/airspace_control](src/airspace_control) |
| CLI and experiments | Single runs, named scenarios, Monte Carlo, benchmarks, operations reports | [main.py](main.py), [config/scenario_params](config/scenario_params) |
| Browser simulators | Canonical Three.js swarm simulator and maritime small-vessel detection simulator | [swarm_3d_simulator.html](swarm_3d_simulator.html), [maritime_detection_simulator.html](maritime_detection_simulator.html) |
| Dash visualization | Python dashboard | [visualization/simulator_3d.py](visualization/simulator_3d.py) |
| API experiment | FastAPI snapshots, scenarios, run records, and WebSocket telemetry | [api/fastapi_server.py](api/fastapi_server.py) |
| Desktop wrapper | Electron application wrapper | [desktop/main.js](desktop/main.js), [package.json](package.json) |
| Validation and delivery | Tests, benchmarks, static build, and GitHub Actions | [tests](tests), [benchmarks](benchmarks), [scripts/build_simulator.py](scripts/build_simulator.py), [.github/workflows](.github/workflows) |

The root [`swarm_3d_simulator.html`](swarm_3d_simulator.html) is the canonical 3D simulator. `scripts/build_simulator.py` synchronizes it to `visualization/`, `docs/`, and `build/simulator/`; do not manually maintain these copies.

## Quick start

### Python simulation

```bash
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc
python -m pip install -e ".[dev]"

python main.py simulate --duration 60 --drones 20
python main.py --help
```

The CLI exposes `simulate`, `scenario`, `monte-carlo`, `benchmark`, `visualize`, `visualize-3d`, `api`, and `ops-report`.

### Browser simulators

```bash
python scripts/serve.py
python scripts/serve.py --page maritime
```

Do not open the HTML files directly with `file://`: browser module and CORS rules can prevent Three.js from loading. Use the local server, GitHub Pages, or Electron instead.

### Dash and FastAPI

```bash
python main.py visualize
python main.py api
```

The FastAPI service is an integration/research surface. It currently uses in-memory state, so a multi-instance production deployment needs persistent storage, key management, observability, and an operational design.

## Build and deploy the simulator only

```bash
python scripts/build_simulator.py
python scripts/build_simulator.py --check
python -m http.server 8123 --directory build/simulator
```

`build/simulator/` contains the simulator, manifest, service worker, and local Three.js vendor files, so it can be copied to a static host. GitHub Pages deploys `docs/`; `.github/workflows/deploy-pages.yml` synchronizes the canonical simulator and vendor files before publishing.

## Desktop packaging

```bash
npm ci
npm run build:simulator
npm run pack       # validate an unpacked Electron app
npm run dist:win   # create Windows installer and portable app
```

Build macOS and Linux packages on their native platforms with `npm run dist:mac` and `npm run dist:linux`. Output is written to `dist-desktop/` and is intentionally untracked.

Pushing a `v*` tag runs the [Desktop Build workflow](.github/workflows/desktop-build.yml), which builds Windows, macOS, and Linux artifacts and publishes a GitHub Release. Validate each platform and any signing policy before tagging.

## Verification

```bash
ruff check src/ simulation/
mypy src/
python -m pytest tests/ -q
npm run build:simulator:check
```

CI runs tests on Python 3.10, 3.11, and 3.12, then enforces `ruff`, `mypy src/`, coverage >=80%, and main-branch benchmarks. Browser simulator changes also run Node/Playwright smoke tests.

## Documentation

| Topic | Document |
|---|---|
| Documentation index | [docs/INDEX.md](docs/INDEX.md) |
| Browser API and maturity | [docs/SDACS_API.md](docs/SDACS_API.md) |
| Repository health record | [docs/HEALTH_CHECK.md](docs/HEALTH_CHECK.md) |
| Hardware plan | [docs/hardware/README.md](docs/hardware/README.md) |
| Research-paper preparation | [docs/paper/contribution_outline.md](docs/paper/contribution_outline.md) |
| Industry and commercialization track | [docs/track_f/README.md](docs/track_f/README.md) |
| Roadmap | [ROADMAP.md](ROADMAP.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

The `window._sdacs` reference distinguishes production, beta, mock, and speculative APIs. Do not infer deployment readiness from an API or phase name alone; inspect its maturity and test evidence.

## Open work as of 2026-07-30

| Priority | Work item | Reason |
|---|---|---|
| High | Review and merge dependency PRs | Dependabot PRs [#512](https://github.com/sun475300-sudo/swarm-drone-atc/pull/512) through [#518](https://github.com/sun475300-sudo/swarm-drone-atc/pulls?q=is%3Aopen%20is%3Apr) remain open; NumPy, Playwright, and GitHub Actions need CI/E2E review |
| High | Publish a desktop release | Packaging is configured, but no SDACS desktop installer is currently downloadable from GitHub Releases |
| High | Protect `main` | GitHub reports no branch-protection rule; required checks, reviews, and administrator-bypass policy need a decision |
| Medium | Productionize or explicitly scope the FastAPI service | Replace in-memory state with persistent infrastructure, or keep it clearly limited to experimentation |
| Medium | Hardware/HITL/field validation | Pixhawk, Jetson, RTK, real-flight, and partner integrations cannot be replaced by software CI |
| Medium | Reconcile legacy documentation | Historical phase/release claims in supporting documents and draft PR [#510](https://github.com/sun475300-sudo/swarm-drone-atc/pull/510) require review against this README |
| Low | Triage historic issue | [#409](https://github.com/sun475300-sudo/swarm-drone-atc/issues/409) is a June manual-check issue that should be updated or closed |

## Contributing and security

- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [MIT License](LICENSE)

Real-world operation affecting people, aircraft, or property requires independent safety validation, regulatory approval, and an accountable operations model.
