"""Compatibility wrapper for the canonical SDACS FastAPI backend.

Use `api.fastapi_server` as the implementation module.
This module keeps `uvicorn api.server:app` and older imports working.
"""

from __future__ import annotations

from fastapi import HTTPException

from api.fastapi_server import (
    ScenarioRunRequest,
    SimulateRequest,
    app,
    get_run,
    get_snapshot,
    health,
    healthz,
    list_scenarios,
    run_dev_server,
    run_scenario,
    scenario_run,
    scenarios,
    simulate,
    ws_telemetry,
)
from simulation.simulator import SwarmSimulator


async def simulate(req: SimulateRequest) -> dict[str, object]:
    """Legacy compatibility entry point for older direct imports/tests."""
    try:
        sim = SwarmSimulator(
            config_path="config/default_simulation.yaml",
            scenario_cfg={"drones": {"default_count": req.drones}},
            seed=req.seed,
        )
        return sim.run(duration_s=req.duration).to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

__all__ = [
    "ScenarioRunRequest",
    "SimulateRequest",
    "SwarmSimulator",
    "app",
    "get_run",
    "get_snapshot",
    "health",
    "healthz",
    "list_scenarios",
    "run_dev_server",
    "run_scenario",
    "scenario_run",
    "scenarios",
    "simulate",
    "ws_telemetry",
]


if __name__ == "__main__":
    run_dev_server()
