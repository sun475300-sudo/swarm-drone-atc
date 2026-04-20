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
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI and pydantic are required. "
        "pip install 'fastapi>=0.110' 'uvicorn[standard]>=0.29' 'pydantic>=2.5'"
    ) from exc

LOGGER = logging.getLogger("sdacs.fastapi")


# --- In-memory state (replace with Redis/Postgres in P714) ---


@dataclass
class AirspaceSnapshot:
    timestamp_ns: int
    drones: list[dict] = field(default_factory=list)  # [{id, lat, lon, alt, vx, vy, vz, head}, ...]
    conflicts: list[dict] = field(default_factory=list)


@dataclass
class RunRecord:
    run_id: str
    scenario_id: str
    status: str  # queued | running | completed | failed
    started_at_ns: int
    finished_at_ns: Optional[int] = None
    metrics: dict = field(default_factory=dict)


class AppState:
    """Simple in-memory state. Swap with a real store later."""

    def __init__(self) -> None:
        self.snapshot = AirspaceSnapshot(timestamp_ns=time.time_ns())
        self.scenarios: dict[str, dict] = {
            "empty_sky": {"name": "Empty Sky", "n_drones": 0, "difficulty": "trivial"},
            "light_traffic_10": {"name": "Light Traffic (10)", "n_drones": 10, "difficulty": "easy"},
            "dense_traffic_50": {"name": "Dense Traffic (50)", "n_drones": 50, "difficulty": "medium"},
            "stress_200": {"name": "Stress (200)", "n_drones": 200, "difficulty": "hard"},
            "crosswind_corridor": {"name": "Crosswind Corridor", "n_drones": 20, "difficulty": "medium"},
            "geofence_breach": {"name": "Geofence Breach", "n_drones": 15, "difficulty": "hard"},
            "remote_id_loss": {"name": "Remote ID Loss", "n_drones": 10, "difficulty": "easy"},
        }
        self.runs: dict[str, RunRecord] = {}
        self.telemetry_subscribers: set[WebSocket] = set()

    async def broadcast(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.telemetry_subscribers):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception as exc:
                LOGGER.warning("ws send failed: %s", exc)
                dead.append(ws)
        for ws in dead:
            self.telemetry_subscribers.discard(ws)


STATE = AppState()


# --- Lifespan (replaces deprecated startup/shutdown) ---


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
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
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="missing bearer token")
    return authorization[len("Bearer ") :]


# --- Pydantic models ---


class RunScenarioBody(BaseModel):
    seed: int = Field(ge=0, le=2**31 - 1, default=0)
    method: str = Field(pattern="^(orca|apf|cbs|hybrid)$", default="hybrid")
    duration_s: int = Field(ge=1, le=3600, default=60)


class EnvelopeError(BaseModel):
    success: bool = False
    error: str


# --- App ---


app = FastAPI(
    title="SDACS API",
    version="0.1.0",
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
    return {"success": True, "status": "ok", "now_ns": time.time_ns()}


# --- Airspace snapshot ---


@app.get("/api/airspace/snapshot", tags=["airspace"])
async def get_snapshot() -> dict:
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
    return {"success": True, "data": STATE.scenarios}


@app.post("/api/scenarios/{scenario_id}/run", tags=["scenarios"])
async def run_scenario(
    scenario_id: str,
    body: RunScenarioBody,
    _token: str = Depends(require_token),
) -> dict:
    if scenario_id not in STATE.scenarios:
        raise HTTPException(404, detail=f"scenario '{scenario_id}' not found")

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

    return {"success": True, "data": {"run_id": run_id, "status": "queued"}}


async def _execute_run(run_id: str, body: RunScenarioBody) -> None:
    record = STATE.runs[run_id]
    record.status = "running"
    try:
        # TODO: wire to src/airspace_manager.py. For now simulate latency.
        await asyncio.sleep(2.0)
        record.metrics = {
            "near_miss_rate": 0.00012,
            "min_separation_m": 4.8,
            "path_efficiency": 0.91,
            "makespan_s": 58.2,
        }
        record.status = "completed"
    except Exception as exc:
        LOGGER.exception("run %s failed", run_id)
        record.metrics = {"error": str(exc)}
        record.status = "failed"
    finally:
        record.finished_at_ns = time.time_ns()


@app.get("/api/runs/{run_id}", tags=["scenarios"])
async def get_run(run_id: str) -> dict:
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
    await ws.accept()
    STATE.telemetry_subscribers.add(ws)
    LOGGER.info("telemetry subscriber connected (total=%d)", len(STATE.telemetry_subscribers))
    try:
        # Keep the socket alive; the server pushes via broadcast().
        while True:
            # Accept optional client keep-alives but don't require them.
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        STATE.telemetry_subscribers.discard(ws)
        LOGGER.info("telemetry subscriber disconnected (total=%d)", len(STATE.telemetry_subscribers))
