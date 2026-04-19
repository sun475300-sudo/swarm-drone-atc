"""FastAPI REST API server for SDACS.

Endpoints:
  GET  /health              — server status + GPU/backend info
  POST /simulate            — run simulation synchronously
  GET  /scenarios            — list available scenarios
  POST /scenarios/{name}/run — run a named scenario

Run:
  uvicorn api.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from simulation.apf_engine import get_apf_backend_info
from simulation.scenario_runner import list_scenarios, run_scenario
from simulation.simulator import SwarmSimulator

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"
RATE_LIMIT_MAX_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60

app = FastAPI(title="SDACS API", version=API_VERSION)

# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate limiting (IP-based, per-minute window)
# ---------------------------------------------------------------------------
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Any) -> Response:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    # Prune expired entries
    timestamps = _rate_limit_store[client_ip]
    _rate_limit_store[client_ip] = [t for t in timestamps if t > window_start]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return Response(
            content='{"detail":"Rate limit exceeded. Try again later."}',
            status_code=429,
            media_type="application/json",
        )

    _rate_limit_store[client_ip].append(now)
    return await call_next(request)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SimulateRequest(BaseModel):
    drones: int = Field(default=50, ge=1, le=2000)
    duration: float = Field(default=60.0, ge=1, le=3600)
    seed: int = Field(default=42)


class ScenarioRunRequest(BaseModel):
    n_runs: int = Field(default=1, ge=1, le=100)
    seed: int = Field(default=42)
    duration: Optional[float] = Field(default=None, ge=1, le=3600)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, Any]:
    backend_info = get_apf_backend_info()
    return {
        "status": "ok",
        "version": API_VERSION,
        "timestamp": time.time(),
        "gpu": backend_info,
    }


# ---------------------------------------------------------------------------
# POST /simulate
# ---------------------------------------------------------------------------

@app.post("/simulate")
async def simulate(req: SimulateRequest) -> dict[str, Any]:
    try:
        sim = SwarmSimulator(
            config_path="config/default_simulation.yaml",
            seed=req.seed,
        )
        sim._cfg["drones"]["default_count"] = req.drones
        result = sim.run(duration_s=req.duration)
        return result.to_dict()
    except Exception as exc:
        logger.exception("Simulation failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /scenarios
# ---------------------------------------------------------------------------

@app.get("/scenarios")
async def scenarios() -> dict[str, Any]:
    names = list_scenarios()
    return {"scenarios": names, "count": len(names)}


# ---------------------------------------------------------------------------
# POST /scenarios/{name}/run
# ---------------------------------------------------------------------------

@app.post("/scenarios/{name}/run")
async def scenario_run(name: str, req: ScenarioRunRequest | None = None) -> dict[str, Any]:
    body = req or ScenarioRunRequest()
    available = list_scenarios()
    if name not in available:
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found")

    try:
        results = run_scenario(
            scenario_name=name,
            n_runs=body.n_runs,
            seed=body.seed,
            verbose=False,
            duration_override_s=body.duration,
        )
        return {"scenario": name, "runs": len(results), "results": results}
    except Exception as exc:
        logger.exception("Scenario run failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
