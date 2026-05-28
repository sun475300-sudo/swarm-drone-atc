"""FastAPI backend skeleton for the SDACS web dashboard (replacement for Dash).

Phase: P711
Goal: progressive migration path from Dash to React + FastAPI + WebSocket.
This file ONLY provides the backend. The existing Dash app can keep running
during migration.

Endpoints (v0):
    GET  /healthz                  — liveness probe
    GET  /api/airspace/snapshot    — last known state (polling fallback)
    GET  /api/scenarios            — list of Monte Carlo scenarios
    POST /api/scenarios/{id}/run   — kick off a run (returns run_id)
    GET  /api/runs/{run_id}        — run status / metrics
    WS   /ws/telemetry             — 1 kHz server → client stream

Auth (v1 — stub here):
    JWT Bearer via Authorization header. See P712 for full RBAC.

Quickstart:
    pip install fastapi uvicorn[standard]
    uvicorn api.fastapi_server:app --reload --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, AsyncIterator

import numpy as np

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI and pydantic are required. "
        "pip install 'fastapi>=0.110' 'uvicorn[standard]>=0.29' 'pydantic>=2.5'"
    ) from exc

LOGGER = logging.getLogger("sdacs.fastapi")
API_VERSION = "1.1.0"


# --- In-memory state (replace with Redis/Postgres in P714) ---


@dataclass
class AirspaceSnapshot:
    """``AirspaceSnapshot`` 관련 기능을 제공한다."""
    timestamp_ns: int
    drones: list[dict] = field(default_factory=list)  # [{id, lat, lon, alt, vx, vy, vz, head}, ...]
    conflicts: list[dict] = field(default_factory=list)


@dataclass
class RunRecord:
    """``RunRecord`` 데이터를 표현한다."""
    run_id: str
    scenario_id: str
    status: str  # queued | running | completed | failed
    started_at_ns: int
    finished_at_ns: int | None = None
    metrics: dict = field(default_factory=dict)


class AppState:
    """Simple in-memory state. Swap with a real store later."""

    def __init__(self) -> None:
        """인스턴스를 초기화한다."""
        self.snapshot = AirspaceSnapshot(timestamp_ns=time.time_ns())
        self.scenarios = _build_scenario_catalog()
        self.runs: dict[str, RunRecord] = {}
        self.telemetry_subscribers: set[WebSocket] = set()
        self.live_tracks: dict[str, dict[str, Any]] = {}
        self.live_corridors: dict[str, int] = {}
        self.live_id_map: dict[str, int] = {}
        self.next_live_numeric_id = 1
        self.live_grid = None
        self.advisory_generator = None

    async def broadcast(self, payload: dict) -> None:
        """``broadcast`` 동작을 수행한다."""
        dead: list[WebSocket] = []
        for ws in list(self.telemetry_subscribers):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception as exc:
                LOGGER.warning("ws send failed: %s", exc)
                dead.append(ws)
        for ws in dead:
            self.telemetry_subscribers.discard(ws)

    def ensure_live_components(self):
        """``ensure_live_components`` 동작을 수행한다."""
        if self.live_grid is None:
            from src.airspace_manager import AirspaceGrid

            self.live_grid = AirspaceGrid()
        if self.advisory_generator is None:
            from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator

            self.advisory_generator = AdvisoryGenerator()
        return self.live_grid, self.advisory_generator

    def numeric_drone_id(self, drone_id: str) -> int:
        """``numeric_drone_id`` 동작을 수행한다."""
        existing = self.live_id_map.get(drone_id)
        if existing is not None:
            return existing
        numeric_id = self.next_live_numeric_id
        self.next_live_numeric_id += 1
        self.live_id_map[drone_id] = numeric_id
        return numeric_id


def _load_backend_info() -> dict[str, Any]:
    try:
        from simulation.apf_engine import get_apf_backend_info
    except Exception as exc:  # pragma: no cover - dependency/runtime specific
        LOGGER.warning("backend info unavailable: %s", exc)
        return {"gpu": False, "backend": "unavailable", "error": str(exc)}
    return get_apf_backend_info()


def _load_repo_scenarios() -> list[str]:
    try:
        from simulation.scenario_runner import list_scenarios as _list_scenarios
    except Exception as exc:  # pragma: no cover - dependency/runtime specific
        LOGGER.warning("scenario discovery unavailable: %s", exc)
        return []
    return list(_list_scenarios())


def _build_scenario_catalog() -> dict[str, dict[str, Any]]:
    discovered = _load_repo_scenarios()
    if discovered:
        return {
            name: {
                "name": name,
                "difficulty": "unknown",
                "source": "config/scenario_params",
            }
            for name in discovered
        }
    return {
        "empty_sky": {"name": "Empty Sky", "n_drones": 0, "difficulty": "trivial"},
        "light_traffic_10": {"name": "Light Traffic (10)", "n_drones": 10, "difficulty": "easy"},
        "dense_traffic_50": {"name": "Dense Traffic (50)", "n_drones": 50, "difficulty": "medium"},
        "stress_200": {"name": "Stress (200)", "n_drones": 200, "difficulty": "hard"},
        "crosswind_corridor": {"name": "Crosswind Corridor", "n_drones": 20, "difficulty": "medium"},
        "geofence_breach": {"name": "Geofence Breach", "n_drones": 15, "difficulty": "hard"},
        "remote_id_loss": {"name": "Remote ID Loss", "n_drones": 10, "difficulty": "easy"},
    }


def _live_airspace_stats(corridor_label: str) -> dict[str, Any]:
    """Return current AirspaceGrid statistics for a live (non-scenario) run.

    Wires ``scenario_id`` from a /api/scenarios/{id}/run POST that does not
    match any repo scenario YAML.  The caller treats this as the corridor label.

    For full live control (P714): accept drone positions via the WebSocket feed,
    call grid.assign_corridor() / grid.check_conflict(), and emit advisory events.
    """
    from src.airspace_manager import AirspaceGrid

    grid = AirspaceGrid()
    stats = grid.get_statistics()
    return {
        "corridor_label": corridor_label,
        "grid_utilization": stats.get("grid_utilization", 0.0),
        "active_corridors": stats.get("active_corridors", 0),
        "total_corridors": stats.get("total_corridors", 0),
        "occupied_cells": stats.get("occupied_cells", 0),
        "total_cells": stats.get("total_cells", 0),
    }


def _normalize_live_telemetry(payload: dict[str, Any]) -> dict[str, Any]:
    drone_id = str(payload.get("drone_id") or payload.get("id") or "").strip()
    if not drone_id:
        raise ValueError("telemetry payload missing drone_id")

    if "position" in payload:
        position = np.asarray(payload["position"], dtype=float)
    elif "pos" in payload:
        pos = payload["pos"]
        position = np.asarray([pos["x"], pos["y"], pos["z"]], dtype=float)
    else:
        position = np.asarray(
            [
                payload.get("x", 0.0),
                payload.get("y", 0.0),
                payload.get("z", payload.get("alt", 0.0)),
            ],
            dtype=float,
        )
    if position.shape != (3,):
        raise ValueError("telemetry position must be length-3")

    if "velocity" in payload:
        velocity = np.asarray(payload["velocity"], dtype=float)
    elif "vel" in payload:
        vel = payload["vel"]
        velocity = np.asarray([vel["x"], vel["y"], vel["z"]], dtype=float)
    else:
        velocity = np.asarray(
            [
                payload.get("vx", 0.0),
                payload.get("vy", 0.0),
                payload.get("vz", 0.0),
            ],
            dtype=float,
        )
    if velocity.shape != (3,):
        raise ValueError("telemetry velocity must be length-3")

    return {
        "drone_id": drone_id,
        "position": position,
        "velocity": velocity,
        "heading": float(payload.get("heading", payload.get("head", 0.0))),
        "battery_pct": float(payload.get("battery_pct", payload.get("bat", 100.0))),
        "timestamp_ns": int(payload.get("timestamp_ns", payload.get("t", time.time_ns()))),
    }


def _drop_live_corridor(grid: Any, corridor_id: int | None) -> None:
    if corridor_id is None or corridor_id not in grid.corridors:
        return
    corridor = grid.corridors.pop(corridor_id)
    for cell in corridor.cells:
        cell.occupying_corridors.discard(corridor_id)


def _estimate_cpa(
    position_a: np.ndarray,
    velocity_a: np.ndarray,
    position_b: np.ndarray,
    velocity_b: np.ndarray,
) -> tuple[float, float]:
    rel_pos = position_b - position_a
    rel_vel = velocity_b - velocity_a
    rel_speed_sq = float(np.dot(rel_vel, rel_vel))
    if rel_speed_sq <= 1e-9:
        return float(np.linalg.norm(rel_pos)), 0.0

    cpa_t = max(0.0, -float(np.dot(rel_pos, rel_vel)) / rel_speed_sq)
    cpa_delta = rel_pos + rel_vel * cpa_t
    cpa_dist = float(np.linalg.norm(cpa_delta))
    return cpa_dist, cpa_t


def _build_live_drone_view(track: dict[str, Any]) -> dict[str, Any]:
    position = track["position"]
    velocity = track["velocity"]
    return {
        "id": track["drone_id"],
        "x": float(position[0]),
        "y": float(position[1]),
        "z": float(position[2]),
        "vx": float(velocity[0]),
        "vy": float(velocity[1]),
        "vz": float(velocity[2]),
        "head": float(track["heading"]),
        "battery_pct": float(track["battery_pct"]),
    }


def _build_live_advisory(
    *,
    advisory_generator: Any,
    source_track: dict[str, Any],
    threat_track: dict[str, Any],
) -> tuple[Any, float]:
    from src.airspace_control.agents.drone_state import DroneState, FlightPhase

    cpa_dist, cpa_t = _estimate_cpa(
        source_track["position"],
        source_track["velocity"],
        threat_track["position"],
        threat_track["velocity"],
    )
    target = DroneState(
        drone_id=source_track["drone_id"],
        position=source_track["position"],
        velocity=source_track["velocity"],
        heading=source_track["heading"],
        battery_pct=source_track["battery_pct"],
        flight_phase=FlightPhase.ENROUTE,
    )
    threat = DroneState(
        drone_id=threat_track["drone_id"],
        position=threat_track["position"],
        velocity=threat_track["velocity"],
        heading=threat_track["heading"],
        battery_pct=threat_track["battery_pct"],
        flight_phase=FlightPhase.ENROUTE,
    )
    advisory = advisory_generator.generate(
        target=target,
        threat=threat,
        cpa_dist_m=cpa_dist,
        cpa_t_s=cpa_t,
        now_s=time.time(),
    )
    return advisory, cpa_dist


def _process_live_telemetry(state: AppState, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_live_telemetry(payload)
    grid, advisory_generator = state.ensure_live_components()
    drone_id = normalized["drone_id"]
    numeric_id = state.numeric_drone_id(drone_id)
    position = normalized["position"]
    velocity = normalized["velocity"]
    now_s = normalized["timestamp_ns"] / 1e9

    track = {
        **normalized,
        "numeric_id": numeric_id,
    }
    state.live_tracks[drone_id] = track

    previous_corridor_id = state.live_corridors.get(drone_id)
    _drop_live_corridor(grid, previous_corridor_id)
    projected_end = position + velocity * 10.0
    corridor_id = grid.assign_corridor(
        drone_id=numeric_id,
        start=position,
        end=projected_end,
        radius=20.0,
        ttl=15.0,
        current_time=now_s,
    )
    state.live_corridors[drone_id] = corridor_id
    grid.update_expiry(now_s)

    drones = [_build_live_drone_view(track) for track in state.live_tracks.values()]
    advisories: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for other_id, other_track in state.live_tracks.items():
        if other_id == drone_id:
            continue
        other_corridor_id = state.live_corridors.get(other_id)
        if other_corridor_id is None:
            continue

        corridor_conflict = grid.check_conflict(corridor_id, other_corridor_id)
        direct_distance = float(np.linalg.norm(position - other_track["position"]))
        separation_conflict = direct_distance < grid.min_separation
        if not corridor_conflict and not separation_conflict:
            continue

        advisory, cpa_dist = _build_live_advisory(
            advisory_generator=advisory_generator,
            source_track=track,
            threat_track=other_track,
        )
        advisory_payload = asdict(advisory)
        advisory_payload["distance_m"] = round(direct_distance, 3)
        advisory_payload["cpa_dist_m"] = round(cpa_dist, 3)
        advisories.append(advisory_payload)
        conflicts.append(
            {
                "pair": sorted([drone_id, other_id]),
                "distance_m": round(direct_distance, 3),
                "corridor_conflict": corridor_conflict,
                "advisory_type": advisory.advisory_type,
            }
        )

    state.snapshot = AirspaceSnapshot(
        timestamp_ns=normalized["timestamp_ns"],
        drones=drones,
        conflicts=conflicts,
    )
    stats = grid.get_statistics()
    return {
        "type": "live_airspace_update",
        "t": state.snapshot.timestamp_ns,
        "drones": drones,
        "conflicts": conflicts,
        "advisories": advisories,
        "stats": stats,
    }


def _run_simulation_sync(*, drones: int, duration_s: float, seed: int) -> dict[str, Any]:
    from simulation.simulator import SwarmSimulator

    sim = SwarmSimulator(
        config_path="config/default_simulation.yaml",
        scenario_cfg={"drones": {"default_count": drones}},
        seed=seed,
    )
    return sim.run(duration_s=duration_s).to_dict()


def _run_named_scenario_sync(
    *,
    scenario_name: str,
    n_runs: int,
    seed: int,
    duration_override_s: float | None,
) -> list[dict[str, Any]]:
    from simulation.scenario_runner import run_scenario as _run_scenario

    return _run_scenario(
        scenario_name=scenario_name,
        n_runs=n_runs,
        seed=seed,
        verbose=False,
        duration_override_s=duration_override_s,
    )


STATE = AppState()


# --- Lifespan (replaces deprecated startup/shutdown) ---


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """``lifespan`` 동작을 수행한다."""
    LOGGER.info("SDACS API starting")
    stream_task = asyncio.create_task(_demo_telemetry_stream())
    try:
        yield
    finally:
        stream_task.cancel()
        LOGGER.info("SDACS API stopped")


async def _demo_telemetry_stream() -> None:
    """Placeholder stream — replace with wire-up to src/airspace_manager.py."""
    import math

    t0 = time.time()
    while True:
        t = time.time() - t0
        STATE.snapshot = AirspaceSnapshot(
            timestamp_ns=time.time_ns(),
            drones=[
                {
                    "id": f"drone-{i}",
                    "lat": 34.93 + 0.0005 * math.cos(t * 0.1 + i),
                    "lon": 126.45 + 0.0005 * math.sin(t * 0.1 + i),
                    "alt": 60 + 10 * math.sin(t * 0.2 + i * 0.3),
                    "vx": 5.0 * math.cos(t * 0.1 + i),
                    "vy": 5.0 * math.sin(t * 0.1 + i),
                    "vz": 0.0,
                    "head": (t * 10 + i * 20) % 360,
                }
                for i in range(10)
            ],
            conflicts=[],
        )
        await STATE.broadcast(
            {
                "t": STATE.snapshot.timestamp_ns,
                "drones": STATE.snapshot.drones,
                "conflicts": STATE.snapshot.conflicts,
            }
        )
        await asyncio.sleep(0.1)


# --- Auth dependency (stub) ---


async def require_token(authorization: str = Header(default="")) -> str:
    # P712 will replace with full JWT validation.
    """``require_token`` 동작을 수행한다."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="missing bearer token")
    return authorization[len("Bearer ") :]


# --- Pydantic models ---


class RunScenarioBody(BaseModel):
    """``RunScenarioBody`` 관련 기능을 제공한다."""
    seed: int = Field(ge=0, le=2**31 - 1, default=0)
    method: str = Field(pattern="^(orca|apf|cbs|hybrid)$", default="hybrid")
    duration_s: int = Field(ge=1, le=3600, default=60)


class SimulateRequest(BaseModel):
    """``SimulateRequest`` 데이터를 표현한다."""
    drones: int = Field(default=50, ge=1, le=2000)
    duration: float = Field(default=60.0, ge=1, le=3600)
    seed: int = Field(default=42)


class ScenarioRunRequest(BaseModel):
    """``ScenarioRunRequest`` 데이터를 표현한다."""
    n_runs: int = Field(default=1, ge=1, le=100)
    seed: int = Field(default=42)
    duration: float | None = Field(default=None, ge=1, le=3600)


class EnvelopeError(BaseModel):
    """``EnvelopeError`` 관련 기능을 제공한다."""
    success: bool = False
    error: str


# --- App ---


app = FastAPI(
    title="SDACS API",
    version=API_VERSION,
    description="Swarm-Drone Airspace Control System — FastAPI backend (Phase 711).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health ---


@app.get("/healthz", tags=["infra"])
async def healthz() -> dict:
    """``healthz`` 동작을 수행한다."""
    return {"success": True, "status": "ok", "now_ns": time.time_ns()}


@app.get("/health", tags=["infra"])
async def health() -> dict[str, Any]:
    """``health`` 동작을 수행한다."""
    return {
        "status": "ok",
        "version": API_VERSION,
        "timestamp": time.time(),
        "gpu": _load_backend_info(),
    }


# --- Airspace snapshot ---


@app.get("/api/airspace/snapshot", tags=["airspace"])
async def get_snapshot() -> dict:
    """`snapshot` 정보를 조회한다."""
    return {
        "success": True,
        "data": {
            "t": STATE.snapshot.timestamp_ns,
            "drones": STATE.snapshot.drones,
            "conflicts": STATE.snapshot.conflicts,
        },
    }


# --- Scenarios ---


@app.get("/api/scenarios", tags=["scenarios"])
async def list_scenarios() -> dict:
    """``list_scenarios`` 동작을 수행한다."""
    STATE.scenarios = _build_scenario_catalog()
    return {"success": True, "data": STATE.scenarios}


@app.get("/scenarios", tags=["scenarios"])
async def scenarios() -> dict[str, Any]:
    """``scenarios`` 동작을 수행한다."""
    STATE.scenarios = _build_scenario_catalog()
    names = list(STATE.scenarios)
    return {"scenarios": names, "count": len(names)}


@app.post("/simulate", tags=["legacy"])
async def simulate(req: SimulateRequest) -> dict[str, Any]:
    """``simulate`` 동작을 수행한다."""
    try:
        return await asyncio.to_thread(
            _run_simulation_sync,
            drones=req.drones,
            duration_s=req.duration,
            seed=req.seed,
        )
    except Exception as exc:
        LOGGER.exception("legacy simulate failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/scenarios/{name}/run", tags=["legacy"])
async def scenario_run(name: str, req: ScenarioRunRequest | None = None) -> dict[str, Any]:
    """``scenario_run`` 동작을 수행한다."""
    body = req or ScenarioRunRequest()
    STATE.scenarios = _build_scenario_catalog()
    if name not in STATE.scenarios:
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found")

    try:
        results = await asyncio.to_thread(
            _run_named_scenario_sync,
            scenario_name=name,
            n_runs=body.n_runs,
            seed=body.seed,
            duration_override_s=body.duration,
        )
        return {"scenario": name, "runs": len(results), "results": results}
    except Exception as exc:
        LOGGER.exception("legacy scenario run failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scenarios/{scenario_id}/run", tags=["scenarios"])
async def run_scenario(
    scenario_id: str,
    body: RunScenarioBody,
    _token: str = Depends(require_token),
) -> dict:
    """``run_scenario`` 동작을 수행한다."""
    STATE.scenarios = _build_scenario_catalog()
    scenario_meta = STATE.scenarios.get(scenario_id)
    request_mode = "scenario" if scenario_meta is not None else "live_airspace"

    run_id = uuid.uuid4().hex
    record = RunRecord(
        run_id=run_id,
        scenario_id=scenario_id,
        status="queued",
        started_at_ns=time.time_ns(),
    )
    STATE.runs[run_id] = record

    # Fire and forget — in production, submit to a worker queue (RQ, Celery, Dramatiq).
    asyncio.create_task(_execute_run(run_id, body))

    return {
        "success": True,
        "data": {
            "run_id": run_id,
            "status": "queued",
            "mode": request_mode,
        },
    }


async def _execute_run(run_id: str, body: RunScenarioBody) -> None:
    record = STATE.runs[run_id]
    record.status = "running"
    try:
        if record.scenario_id in _load_repo_scenarios():
            results = await asyncio.to_thread(
                _run_named_scenario_sync,
                scenario_name=record.scenario_id,
                n_runs=1,
                seed=body.seed,
                duration_override_s=body.duration_s,
            )
            record.metrics = results[0] if results else {}
        else:
            # Non-scenario ID: treat as a live airspace control request keyed by
            # scenario_id as a corridor label.  AirspaceGrid manages corridor
            # assignment and conflict detection; get_statistics() returns metrics
            # that map to the standard RunRecord schema.
            #
            # Next step (P714): accept drone positions via the WebSocket feed,
            # call grid.assign_corridor() / grid.check_conflict(), and stream
            # advisory events back to subscribers rather than blocking here.
            record.metrics = await asyncio.to_thread(_live_airspace_stats, record.scenario_id)
        record.status = "completed"
    except Exception as exc:
        LOGGER.exception("run %s failed", run_id)
        record.metrics = {"error": str(exc)}
        record.status = "failed"
    finally:
        record.finished_at_ns = time.time_ns()


@app.get("/api/runs/{run_id}", tags=["scenarios"])
async def get_run(run_id: str) -> dict:
    """`run` 정보를 조회한다."""
    record = STATE.runs.get(run_id)
    if record is None:
        raise HTTPException(404, detail="run not found")
    return {
        "success": True,
        "data": {
            "run_id": record.run_id,
            "scenario_id": record.scenario_id,
            "status": record.status,
            "started_at_ns": record.started_at_ns,
            "finished_at_ns": record.finished_at_ns,
            "metrics": record.metrics,
        },
    }


# --- WebSocket telemetry ---


@app.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket) -> None:
    """``ws_telemetry`` 동작을 수행한다."""
    await ws.accept()
    STATE.telemetry_subscribers.add(ws)
    LOGGER.info("telemetry subscriber connected (total=%d)", len(STATE.telemetry_subscribers))
    try:
        while True:
            raw = await ws.receive_text()
            if not raw.strip():
                continue
            if raw.strip().lower() == "ping":
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                LOGGER.debug("ignoring non-json telemetry frame: %s", raw[:80])
                continue

            if payload.get("type") in {"telemetry", "live_telemetry"} or (
                "drone_id" in payload or "id" in payload
            ):
                try:
                    event = _process_live_telemetry(STATE, payload)
                except ValueError as exc:
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "error": str(exc),
                            }
                        )
                    )
                    continue
                await STATE.broadcast(event)
    except WebSocketDisconnect:
        pass
    finally:
        STATE.telemetry_subscribers.discard(ws)
        LOGGER.info("telemetry subscriber disconnected (total=%d)", len(STATE.telemetry_subscribers))


def run_dev_server(host: str = "0.0.0.0", port: int = 8000, log_level: str = "info") -> None:
    """``run_dev_server`` 동작을 수행한다."""
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    run_dev_server()
