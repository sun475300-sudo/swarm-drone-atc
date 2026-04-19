# SDACS Docker Deployment

Reproducible container for the Swarm Drone Airspace Control System (SDACS).
This image packages the SimPy-based simulation engine and the Dash 3D
visualization so the full stack can be launched with a single command on any
host that has Docker Engine 20.10+.

## Contents

| File | Purpose |
|------|---------|
| `Dockerfile` (repo root) | Builds the Python 3.10-slim image with scientific-Python deps |
| `docker-compose.yaml` (repo root) | Orchestrates the `sdacs` service, ports, volumes, and env |
| `.dockerignore` (repo root) | Keeps build context small and deterministic |
| `docker/README.md` | Detailed deployment notes (this file) |

## Quick Start

```bash
# from the repository root
docker compose build          # build the image (~1.5 GB, first build only)
docker compose up             # run the Dash dashboard at http://localhost:8050
docker compose up -d          # run detached (background)
docker compose down           # stop and remove the container
```

Open http://localhost:8050 in a browser to view the 3D simulator UI.

## Image Details

- Base image: `python:3.10-slim`
- Runtime Python: 3.10
- Exposed port: `8050` (Dash HTTP server)
- Default command: `python main.py visualize`
- Environment:
  - `PYTHONUNBUFFERED=1` — real-time stdout/stderr streaming
  - `PYTHONIOENCODING=utf-8` — prevents Korean log corruption on Windows hosts

### System dependencies (installed via apt)

- `git` — pip sometimes needs it for VCS installs
- `build-essential` — C toolchain for NumPy/SciPy wheels fallback
- `libgl1-mesa-glx` — required by matplotlib/plotly backends
- `libglib2.0-0` — required transitively by the same plotting stack

### Python dependencies (installed via pip)

Pinned by `requirements.txt`:
- numpy, scipy, pandas, simpy, pyyaml, joblib, tqdm
- matplotlib, plotly, seaborn, dash
- pytest, pytest-cov, pytest-asyncio

## Volume Mounts

`docker-compose.yaml` mounts two host paths into the container so that
configuration edits and simulation artifacts survive container restarts:

| Host path | Container path | Mode | Purpose |
|-----------|----------------|------|---------|
| `./config` | `/app/config` | read-only | Scenario YAMLs, Monte Carlo sweeps, default params |
| `./results` | `/app/results` | read-write | Per-run CSVs, logs, plots |

Add additional mounts (e.g. `./logs:/app/logs`) under the `volumes:` key if you
need them for your deployment.

## Running other CLI subcommands

The default CMD launches the visualizer. To run a simulation or Monte Carlo
sweep instead, override the command:

```bash
# 60-second simulation
docker compose run --rm sdacs python main.py simulate --duration 60

# Pre-defined scenario
docker compose run --rm sdacs python main.py scenario high_density

# Monte Carlo quick sweep
docker compose run --rm sdacs python main.py monte-carlo --mode quick

# pytest (requires tests/ to be present in the image — re-enable in .dockerignore)
docker compose run --rm sdacs pytest tests/ -v
```

## Configuration

Edit any file under `./config/` on the host and restart the container:

```bash
docker compose restart sdacs
```

The mount is read-only inside the container, so the app can never write back to
your host config. Runtime outputs always go to `./results/`.

## Troubleshooting

**Build fails with "No space left on device"**
The first build downloads ~1.5 GB of wheels. Prune old images:
`docker system prune -a`.

**Dashboard is not reachable at http://localhost:8050**
Confirm the port is not already in use:
- Linux/macOS: `lsof -i :8050`
- Windows:    `netstat -ano | findstr 8050`

If occupied, change the host side of the port mapping in
`docker-compose.yaml`, e.g. `- "8060:8050"`, then visit http://localhost:8060.

**Korean logs show `???` on Windows**
Already handled: `PYTHONIOENCODING=utf-8` is set in both the Dockerfile and
the compose environment. Make sure your host terminal also supports UTF-8
(`chcp 65001` in cmd.exe).

**Module not found / stale build**
After pulling new code, rebuild without cache:
`docker compose build --no-cache`.

## Image Size Expectations

The resulting image is roughly 1.5 GB uncompressed:

| Layer | Approx size | Notes |
|-------|-------------|-------|
| `python:3.10-slim` base | ~125 MB | Official Debian slim image |
| apt system deps | ~250 MB | git, build-essential, libgl, libglib |
| pip dependencies | ~1.0 GB | numpy, scipy, pandas, plotly, dash, matplotlib |
| application source | ~20 MB | everything under `/app` after `.dockerignore` |

To shrink further consider:
- Removing `build-essential` after pip install (multi-stage build)
- Using `python:3.10-alpine` (requires more manual compilation of scientific wheels)
- Splitting runtime and dev dependencies into separate requirements files

## CI / Production Notes

- The compose file pins `restart: unless-stopped` so the container comes back
  automatically after host reboots or transient crashes.
- For production behind a reverse proxy, expose only the Docker network and
  proxy 8050 through nginx/traefik with TLS.
- Mount `./results` to a persistent volume (e.g. an attached block device) if
  you need to retain Monte Carlo output across container rebuilds.
- The image contains no secrets. All runtime configuration comes from YAML
  files under `./config/` and environment variables set in compose.
