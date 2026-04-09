"""FastAPI Server for SDACS with WebSocket support.

RESTful API for drone swarm ATC simulation control and monitoring.
Includes real-time WebSocket streams for telemetry, events, and metrics.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import numpy as np
import yaml
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from simulation.simulator import SwarmSimulator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SDACS API",
    description="군집드론 공역통제 자동화 시스템 (Swarm Drone Airspace Control System) API",
    version="2.1.0",
)

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active simulations: sim_id -> {simulator, thread, result, status, config, ws_clients}
_simulations: dict[str, dict[str, Any]] = {}
_lock = threading.RLock()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class DroneStatus(BaseModel):
    """Current state of a single drone."""
    drone_id: str
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    velocity_magnitude: float
    battery_pct: float
    flight_phase: str
    distance_flown_m: float
    timestamp_s: float


class DroneListResponse(BaseModel):
    """List of drones with pagination."""
    simulation_id: str
    count: int
    drones: list[DroneStatus]
    timestamp_s: float


class ConflictAlert(BaseModel):
    """Conflict detection event."""
    conflict_id: str
    drone_ids: list[str]
    severity: str  # low, medium, high
    distance_m: float
    timestamp_s: float


class ConflictListResponse(BaseModel):
    """List of active conflicts."""
    simulation_id: str
    active_count: int
    conflicts: list[ConflictAlert]
    timestamp_s: float


class MetricsResponse(BaseModel):
    """Real-time or final metrics."""
    simulation_id: str
    timestamp_s: float
    collision_count: int
    near_miss_count: int
    conflicts_total: int
    conflict_resolution_rate_pct: float
    advisories_issued: int
    clearances_approved: int
    clearances_denied: int
    comm_drop_rate: float
    total_distance_km: float
    energy_efficiency_wh_per_km: float
    advisory_latency_p50: float
    advisory_latency_p99: float


class SimulationConfig(BaseModel):
    """Configuration for starting a simulation."""
    duration: int = Field(default=60, ge=1, le=3600, description="Simulation duration in seconds")
    num_drones: int = Field(default=50, ge=1, le=2000, description="Number of drones")
    scenario: str = Field(default="default", description="Scenario name")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp_s: float
    version: str
    active_simulations: int


class SimulationSummary(BaseModel):
    """Summary of a simulation."""
    simulation_id: str
    status: str
    config: dict
    started_at_s: float
    elapsed_s: Optional[float] = None
    sim_time_s: Optional[float] = None


class SimulationStatusResponse(BaseModel):
    """Detailed status of a simulation."""
    simulation_id: str
    status: str
    config: dict
    started_at_s: float
    elapsed_s: float
    sim_time_s: Optional[float] = None
    drones_active: Optional[int] = None
    error: Optional[str] = None
    result_summary: Optional[dict] = None


class ScenarioInfo(BaseModel):
    """Information about an available scenario."""
    name: str
    description: Optional[str] = None
    default_drones: int


class ScenariosListResponse(BaseModel):
    """List of available scenarios."""
    scenarios: list[ScenarioInfo]
    total: int


class ConfigGetResponse(BaseModel):
    """Current simulation configuration."""
    drones_default_count: int
    bounds_m: float
    dt_s: float
    bounds_vertical_m: float
    conflict_detection_threshold_m: float


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration."""
    drones_default_count: Optional[int] = None
    bounds_m: Optional[float] = None
    dt_s: Optional[float] = None


class TelemetryMessage(BaseModel):
    """WebSocket telemetry message."""
    type: str = "telemetry"
    simulation_id: str
    timestamp_s: float
    drones: list[DroneStatus]


class EventMessage(BaseModel):
    """WebSocket event message."""
    type: str = "event"
    simulation_id: str
    timestamp_s: float
    event_type: str
    event_data: dict


class MetricsUpdateMessage(BaseModel):
    """WebSocket metrics update message."""
    type: str = "metrics"
    simulation_id: str
    timestamp_s: float
    metrics: MetricsResponse


# ---------------------------------------------------------------------------
# WebSocket Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages WebSocket connections for a simulation."""

    def __init__(self) -> None:
        self.telemetry_clients: set[WebSocket] = set()
        self.event_clients: set[WebSocket] = set()
        self.metrics_clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect_telemetry(self, ws: WebSocket) -> None:
        """Add a telemetry client."""
        await ws.accept()
        async with self._lock:
            self.telemetry_clients.add(ws)

    async def disconnect_telemetry(self, ws: WebSocket) -> None:
        """Remove a telemetry client."""
        async with self._lock:
            self.telemetry_clients.discard(ws)

    async def connect_event(self, ws: WebSocket) -> None:
        """Add an event client."""
        await ws.accept()
        async with self._lock:
            self.event_clients.add(ws)

    async def disconnect_event(self, ws: WebSocket) -> None:
        """Remove an event client."""
        async with self._lock:
            self.event_clients.discard(ws)

    async def connect_metrics(self, ws: WebSocket) -> None:
        """Add a metrics client."""
        await ws.accept()
        async with self._lock:
            self.metrics_clients.add(ws)

    async def disconnect_metrics(self, ws: WebSocket) -> None:
        """Remove a metrics client."""
        async with self._lock:
            self.metrics_clients.discard(ws)

    async def broadcast_telemetry(self, message: dict) -> None:
        """Broadcast telemetry to all connected clients."""
        async with self._lock:
            for ws in list(self.telemetry_clients):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send telemetry: {e}")
                    self.telemetry_clients.discard(ws)

    async def broadcast_event(self, message: dict) -> None:
        """Broadcast event to all connected clients."""
        async with self._lock:
            for ws in list(self.event_clients):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send event: {e}")
                    self.event_clients.discard(ws)

    async def broadcast_metrics(self, message: dict) -> None:
        """Broadcast metrics to all connected clients."""
        async with self._lock:
            for ws in list(self.metrics_clients):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send metrics: {e}")
                    self.metrics_clients.discard(ws)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_sim(sim_id: str) -> dict[str, Any]:
    """Get simulation by ID or raise 404."""
    with _lock:
        if sim_id not in _simulations:
            raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        return _simulations[sim_id]


def _run_sim_thread(sim_id: str, simulator: SwarmSimulator, duration: float) -> None:
    """Background thread that executes a simulation."""
    entry = _simulations[sim_id]
    try:
        result = simulator.run(duration_s=duration)
        with _lock:
            entry["result"] = result
            entry["status"] = "completed"
    except Exception as e:
        with _lock:
            entry["status"] = "failed"
            entry["error"] = str(e)
        logger.error(f"Simulation {sim_id} failed: {e}")


def _extract_drones(sim: dict[str, Any]) -> list[DroneStatus]:
    """Extract drone states from a running or completed simulation."""
    simulator: SwarmSimulator = sim["simulator"]
    drones = []
    t = float(simulator.env.now) if hasattr(simulator, 'env') else 0.0

    for did, ds in simulator._drones.items():
        velocity = ds.velocity if hasattr(ds, 'velocity') else np.zeros(3)
        vx = float(velocity[0]) if len(velocity) > 0 else 0.0
        vy = float(velocity[1]) if len(velocity) > 1 else 0.0
        vz = float(velocity[2]) if len(velocity) > 2 else 0.0

        drones.append(DroneStatus(
            drone_id=did,
            x=float(ds.position[0]),
            y=float(ds.position[1]),
            z=float(ds.position[2]),
            vx=vx,
            vy=vy,
            vz=vz,
            velocity_magnitude=float(getattr(ds, "speed", 0.0)),
            battery_pct=float(getattr(ds, "battery_pct", 100.0)),
            flight_phase=str(getattr(ds, "flight_phase", "UNKNOWN").name if hasattr(getattr(ds, "flight_phase", None), "name") else str(getattr(ds, "flight_phase", "UNKNOWN"))),
            distance_flown_m=float(getattr(ds, "distance_flown_m", 0.0)),
            timestamp_s=t,
        ))
    return drones


def _extract_conflicts(analytics) -> list[ConflictAlert]:
    """Extract conflict events from analytics."""
    conflicts = []
    if not hasattr(analytics, '_events'):
        return conflicts

    for event in analytics._events:
        if event.get("type") == "CONFLICT":
            conflict_id = f"conf_{event.get('t', 0):.1f}_{event.get('drone_id', 'unknown')}"
            conflicts.append(ConflictAlert(
                conflict_id=conflict_id,
                drone_ids=[event.get('drone_id', 'unknown')],
                severity="medium",
                distance_m=event.get('distance_m', 0.0),
                timestamp_s=event.get('t', 0.0),
            ))
    return conflicts


def _build_metrics_from_result(sim_id: str, result) -> MetricsResponse:
    """Build MetricsResponse from a SimulationResult."""
    return MetricsResponse(
        simulation_id=sim_id,
        timestamp_s=datetime.now().timestamp(),
        collision_count=result.collision_count,
        near_miss_count=result.near_miss_count,
        conflicts_total=result.conflicts_total,
        conflict_resolution_rate_pct=result.conflict_resolution_rate_pct,
        advisories_issued=result.advisories_issued,
        clearances_approved=result.clearances_approved,
        clearances_denied=result.clearances_denied,
        comm_drop_rate=result.comm_drop_rate,
        total_distance_km=result.total_distance_km,
        energy_efficiency_wh_per_km=result.energy_efficiency_wh_per_km,
        advisory_latency_p50=result.advisory_latency_p50,
        advisory_latency_p99=result.advisory_latency_p99,
    )


def _get_available_scenarios() -> list[ScenarioInfo]:
    """Get list of available scenarios."""
    scenarios = []
    scenario_dir = "config/scenario_params"

    if not os.path.isdir(scenario_dir):
        return scenarios

    for filename in os.listdir(scenario_dir):
        if filename.endswith(".yaml"):
            name = filename[:-5]  # Remove .yaml
            try:
                path = os.path.join(scenario_dir, filename)
                with open(path) as f:
                    cfg = yaml.safe_load(f) or {}
                    default_drones = cfg.get("drones", {}).get("default_count", 50)
                    scenarios.append(ScenarioInfo(
                        name=name,
                        description=cfg.get("description", None),
                        default_drones=default_drones,
                    ))
            except Exception as e:
                logger.warning(f"Failed to load scenario {name}: {e}")

    return sorted(scenarios, key=lambda s: s.name)


# ---------------------------------------------------------------------------
# Endpoints: Root & Health
# ---------------------------------------------------------------------------

@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint."""
    return {
        "service": "SDACS API",
        "version": "2.1.0",
        "description": "군집드론 공역통제 자동화 시스템 (Swarm Drone Airspace Control System)",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    with _lock:
        active = sum(1 for s in _simulations.values() if s["status"] == "running")
    return HealthResponse(
        status="healthy",
        timestamp_s=datetime.now().timestamp(),
        version="2.1.0",
        active_simulations=active,
    )


# ── Simulation Lifecycle ──────────────────────────────────────────────────

@app.post("/api/simulation/start", response_model=SimulationSummary)
async def start_simulation(config: SimulationConfig) -> SimulationSummary:
    """Start a new simulation in a background thread.

    Args:
        config: Simulation configuration (duration, num_drones, scenario, seed)

    Returns:
        SimulationSummary with simulation ID and initial status
    """
    sim_id = f"sim_{uuid.uuid4().hex[:8]}"

    # Load scenario config if specified
    scenario_cfg = None
    if config.scenario != "default":
        scenario_path = f"config/scenario_params/{config.scenario}.yaml"
        if os.path.exists(scenario_path):
            try:
                with open(scenario_path) as f:
                    scenario_cfg = yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"Failed to load scenario {config.scenario}: {e}")

    seed = config.seed if config.seed is not None else 42

    # Create simulator
    try:
        simulator = SwarmSimulator(
            config_path="config/default_simulation.yaml",
            scenario_cfg=scenario_cfg,
            seed=seed,
        )
        simulator._cfg["drones"]["default_count"] = config.num_drones
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize simulator: {e}")

    started_at = time.time()
    with _lock:
        entry: dict[str, Any] = {
            "simulator": simulator,
            "thread": None,
            "result": None,
            "status": "running",
            "error": None,
            "config": config.model_dump(),
            "started_at": started_at,
            "ws_manager": ConnectionManager(),
        }
        _simulations[sim_id] = entry

    # Start simulation in background thread
    t = threading.Thread(
        target=_run_sim_thread,
        args=(sim_id, simulator, float(config.duration)),
        daemon=True,
    )
    entry["thread"] = t
    t.start()

    return SimulationSummary(
        simulation_id=sim_id,
        status="running",
        config=config.model_dump(),
        started_at_s=started_at,
    )


@app.get("/api/simulation")
async def list_simulations() -> dict[str, Any]:
    """List all simulations with their status."""
    with _lock:
        simulations = []
        for sid, s in _simulations.items():
            elapsed = time.time() - s["started_at"]
            sim_time = None
            if s["status"] == "running" and hasattr(s["simulator"], "env"):
                sim_time = float(s["simulator"].env.now)

            simulations.append({
                "simulation_id": sid,
                "status": s["status"],
                "config": s["config"],
                "started_at_s": s["started_at"],
                "elapsed_s": elapsed,
                "sim_time_s": sim_time,
            })

    return {"simulations": simulations, "total": len(simulations)}


@app.get("/api/simulation/{simulation_id}/status", response_model=SimulationStatusResponse)
async def get_simulation_status(simulation_id: str) -> SimulationStatusResponse:
    """Get detailed status of a simulation."""
    sim = _get_sim(simulation_id)

    elapsed = time.time() - sim["started_at"]
    sim_time = None
    drones_active = None

    if sim["status"] == "running" and hasattr(sim["simulator"], "env"):
        simulator: SwarmSimulator = sim["simulator"]
        sim_time = float(simulator.env.now)
        drones_active = len(simulator._drones)

    result_summary = None
    if sim["result"] is not None:
        result_summary = {
            "collisions": sim["result"].collision_count,
            "resolution_rate": sim["result"].conflict_resolution_rate_pct,
            "total_distance_km": sim["result"].total_distance_km,
        }

    return SimulationStatusResponse(
        simulation_id=simulation_id,
        status=sim["status"],
        config=sim["config"],
        started_at_s=sim["started_at"],
        elapsed_s=elapsed,
        sim_time_s=sim_time,
        drones_active=drones_active,
        error=sim.get("error"),
        result_summary=result_summary,
    )


@app.post("/api/simulation/{simulation_id}/stop")
async def stop_simulation(simulation_id: str) -> dict[str, Any]:
    """Request graceful stop of a simulation."""
    sim = _get_sim(simulation_id)

    with _lock:
        if sim["status"] != "running":
            return {
                "simulation_id": simulation_id,
                "status": sim["status"],
                "message": "Not running",
            }
        sim["status"] = "stopping"

    return {
        "simulation_id": simulation_id,
        "status": "stopping",
        "message": "Stop signal sent",
    }


# ── Drone Queries ─────────────────────────────────────────────────────────

@app.get("/api/drones/{drone_id}", response_model=DroneStatus)
async def get_drone(drone_id: str, simulation_id: Optional[str] = Query(None)) -> DroneStatus:
    """Get single drone status.

    If simulation_id is not provided, searches across all active simulations.
    """
    with _lock:
        sims_to_search = {simulation_id: _simulations[simulation_id]} if simulation_id else _simulations

    for sid, sim in sims_to_search.items():
        try:
            simulator: SwarmSimulator = sim["simulator"]
            ds = simulator._drones.get(drone_id)
            if ds is not None:
                t = float(simulator.env.now) if hasattr(simulator, "env") else 0.0
                velocity = ds.velocity if hasattr(ds, 'velocity') else np.zeros(3)
                return DroneStatus(
                    drone_id=drone_id,
                    x=float(ds.position[0]),
                    y=float(ds.position[1]),
                    z=float(ds.position[2]),
                    vx=float(velocity[0]) if len(velocity) > 0 else 0.0,
                    vy=float(velocity[1]) if len(velocity) > 1 else 0.0,
                    vz=float(velocity[2]) if len(velocity) > 2 else 0.0,
                    velocity_magnitude=float(getattr(ds, "speed", 0.0)),
                    battery_pct=float(getattr(ds, "battery_pct", 100.0)),
                    flight_phase=str(getattr(ds, "flight_phase", "UNKNOWN").name if hasattr(getattr(ds, "flight_phase", None), "name") else str(getattr(ds, "flight_phase", "UNKNOWN"))),
                    distance_flown_m=float(getattr(ds, "distance_flown_m", 0.0)),
                    timestamp_s=t,
                )
        except Exception as e:
            logger.warning(f"Error searching for drone {drone_id} in {sid}: {e}")

    raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found")


@app.get("/api/drones", response_model=DroneListResponse)
async def get_drones(
    simulation_id: str,
    phase: Optional[str] = Query(None, description="Filter by flight phase"),
    limit: int = Query(100, ge=1, le=2000),
) -> DroneListResponse:
    """Get drone states from a specific simulation."""
    sim = _get_sim(simulation_id)
    drones = _extract_drones(sim)

    if phase:
        drones = [d for d in drones if d.flight_phase.upper() == phase.upper()]

    drones = drones[:limit]
    return DroneListResponse(
        simulation_id=simulation_id,
        count=len(drones),
        drones=drones,
        timestamp_s=datetime.now().timestamp(),
    )


@app.get("/api/simulation/{simulation_id}/drones", response_model=DroneListResponse)
async def get_drones_by_sim(
    simulation_id: str,
    phase: Optional[str] = Query(None, description="Filter by flight phase"),
    limit: int = Query(100, ge=1, le=2000),
) -> DroneListResponse:
    """Get drone states from a specific simulation (deprecated: use /api/drones)."""
    return await get_drones(simulation_id, phase, limit)


# ── Conflicts ─────────────────────────────────────────────────────────────

@app.get("/api/conflicts", response_model=ConflictListResponse)
async def get_conflicts(
    simulation_id: str,
    severity: Optional[str] = Query(None, description="Filter: low|medium|high"),
) -> ConflictListResponse:
    """Get conflict events from a simulation."""
    sim = _get_sim(simulation_id)
    simulator: SwarmSimulator = sim["simulator"]

    if not hasattr(simulator, "analytics") or simulator.analytics is None:
        return ConflictListResponse(
            simulation_id=simulation_id,
            active_count=0,
            conflicts=[],
            timestamp_s=datetime.now().timestamp(),
        )

    events = [
        e for e in simulator.analytics._events
        if e.get("type") in ("CONFLICT", "NEAR_MISS", "COLLISION")
    ]

    severity_map = {"COLLISION": "high", "NEAR_MISS": "medium", "CONFLICT": "low"}
    if severity:
        events = [e for e in events if severity_map.get(e.get("type", "")) == severity.lower()]

    conflicts = [
        ConflictAlert(
            conflict_id=f"conf_{e.get('t', 0):.1f}_{e.get('drone_id', 'unknown')}",
            drone_ids=[e.get("drone_id", "unknown")],
            severity=severity_map.get(e.get("type", ""), "low"),
            distance_m=e.get("distance_m", 0.0),
            timestamp_s=e.get("t", 0.0),
        )
        for e in events
    ]

    return ConflictListResponse(
        simulation_id=simulation_id,
        active_count=len(conflicts),
        conflicts=conflicts,
        timestamp_s=datetime.now().timestamp(),
    )


@app.get("/api/simulation/{simulation_id}/conflicts")
async def get_conflicts_legacy(
    simulation_id: str,
    severity: Optional[str] = Query(None),
) -> dict[str, Any]:
    """Get conflict events (legacy endpoint)."""
    resp = await get_conflicts(simulation_id, severity)
    return resp.model_dump()


# ── Metrics ───────────────────────────────────────────────────────────────

@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(simulation_id: str) -> MetricsResponse:
    """Get simulation metrics.

    Available during and after simulation completes.
    """
    sim = _get_sim(simulation_id)
    result = sim.get("result")

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Simulation metrics not yet available",
        )

    return _build_metrics_from_result(simulation_id, result)


@app.get("/api/simulation/{simulation_id}/metrics")
async def get_metrics_legacy(simulation_id: str) -> dict[str, Any]:
    """Get metrics (legacy endpoint)."""
    resp = await get_metrics(simulation_id)
    return resp.model_dump()


@app.get("/api/simulation/{simulation_id}/result")
async def get_full_result(simulation_id: str) -> dict[str, Any]:
    """Get full simulation result as dictionary."""
    sim = _get_sim(simulation_id)
    result = sim.get("result")

    if result is None:
        raise HTTPException(status_code=409, detail="Simulation not yet completed")

    return result.to_dict()


# ── Configuration ──────────────────────────────────────────────────────────

@app.get("/api/config", response_model=ConfigGetResponse)
async def get_config() -> ConfigGetResponse:
    """Get current global configuration."""
    try:
        with open("config/default_simulation.yaml") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load default config: {e}")
        cfg = {}

    return ConfigGetResponse(
        drones_default_count=cfg.get("drones", {}).get("default_count", 50),
        bounds_m=float(cfg.get("airspace", {}).get("bounds_m", 1000.0)),
        dt_s=float(cfg.get("simulation", {}).get("dt_s", 0.1)),
        bounds_vertical_m=float(cfg.get("airspace", {}).get("bounds_vertical_m", 120.0)),
        conflict_detection_threshold_m=float(cfg.get("conflict_detection", {}).get("threshold_m", 100.0)),
    )


# ── Scenarios ──────────────────────────────────────────────────────────────

@app.get("/api/scenarios", response_model=ScenariosListResponse)
async def get_scenarios() -> ScenariosListResponse:
    """Get list of available scenarios."""
    scenarios = _get_available_scenarios()
    return ScenariosListResponse(scenarios=scenarios, total=len(scenarios))


@app.post("/api/scenario/{scenario_name}", response_model=SimulationSummary)
async def run_scenario(
    scenario_name: str,
    duration: int = Query(60, ge=1, le=3600),
    seed: Optional[int] = Query(None),
) -> SimulationSummary:
    """Run a named scenario.

    Args:
        scenario_name: Name of scenario (without .yaml extension)
        duration: Duration in seconds
        seed: Random seed (optional)
    """
    scenario_path = f"config/scenario_params/{scenario_name}.yaml"

    if not os.path.exists(scenario_path):
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_name}' not found",
        )

    try:
        with open(scenario_path) as f:
            scenario_cfg = yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenario: {e}")

    config = SimulationConfig(
        duration=duration,
        num_drones=scenario_cfg.get("drones", {}).get("default_count", 50),
        scenario=scenario_name,
        seed=seed,
    )

    return await start_simulation(config)


# ── Airspace ──────────────────────────────────────────────────────────────

@app.get("/api/zones")
async def get_zones() -> dict[str, Any]:
    """Get airspace zone configuration."""
    zone_path = "config/airspace_zones.yaml"

    if os.path.exists(zone_path):
        try:
            with open(zone_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load zones: {e}")

    return {"message": "No airspace zone config found", "zones": []}


# ── WebSocket Endpoints ───────────────────────────────────────────────────

@app.websocket("/ws/telemetry/{simulation_id}")
async def websocket_telemetry(websocket: WebSocket, simulation_id: str) -> None:
    """WebSocket endpoint for real-time drone telemetry.

    Broadcasts drone position, velocity, battery, and flight phase at 1 Hz.

    Args:
        websocket: WebSocket connection
        simulation_id: ID of the simulation to stream telemetry from
    """
    sim = _get_sim(simulation_id)
    manager = sim["ws_manager"]

    await manager.connect_telemetry(websocket)

    try:
        # Broadcast telemetry at 1 Hz
        while True:
            await asyncio.sleep(1.0)

            if sim["status"] not in ("running", "stopping"):
                break

            drones = _extract_drones(sim)
            message = {
                "type": "telemetry",
                "simulation_id": simulation_id,
                "timestamp_s": datetime.now().timestamp(),
                "drones_count": len(drones),
                "drones": [d.model_dump() for d in drones],
            }

            await manager.broadcast_telemetry(message)

    except WebSocketDisconnect:
        await manager.disconnect_telemetry(websocket)
    except Exception as e:
        logger.error(f"WebSocket telemetry error: {e}")
        await manager.disconnect_telemetry(websocket)


@app.websocket("/ws/events/{simulation_id}")
async def websocket_events(websocket: WebSocket, simulation_id: str) -> None:
    """WebSocket endpoint for real-time simulation events.

    Broadcasts conflict, collision, advisory, and phase change events.

    Args:
        websocket: WebSocket connection
        simulation_id: ID of the simulation to stream events from
    """
    sim = _get_sim(simulation_id)
    manager = sim["ws_manager"]

    await manager.connect_event(websocket)

    try:
        last_event_count = 0

        while True:
            await asyncio.sleep(0.1)  # Poll at 10 Hz

            if sim["status"] not in ("running", "stopping"):
                break

            simulator: SwarmSimulator = sim["simulator"]
            if not hasattr(simulator, "analytics") or simulator.analytics is None:
                continue

            # Get new events since last poll
            analytics = simulator.analytics
            current_events = analytics._events

            for event in current_events[last_event_count:]:
                message = {
                    "type": "event",
                    "simulation_id": simulation_id,
                    "timestamp_s": datetime.now().timestamp(),
                    "event_type": event.get("type"),
                    "event_data": event,
                }
                await manager.broadcast_event(message)

            last_event_count = len(current_events)

    except WebSocketDisconnect:
        await manager.disconnect_event(websocket)
    except Exception as e:
        logger.error(f"WebSocket events error: {e}")
        await manager.disconnect_event(websocket)


@app.websocket("/ws/metrics/{simulation_id}")
async def websocket_metrics(websocket: WebSocket, simulation_id: str) -> None:
    """WebSocket endpoint for aggregated metrics.

    Broadcasts aggregated KPIs every 5 seconds.

    Args:
        websocket: WebSocket connection
        simulation_id: ID of the simulation to stream metrics from
    """
    sim = _get_sim(simulation_id)
    manager = sim["ws_manager"]

    await manager.connect_metrics(websocket)

    try:
        while True:
            await asyncio.sleep(5.0)  # Update every 5 seconds

            if sim["status"] not in ("running", "stopping"):
                break

            result = sim.get("result")
            if result is None:
                continue

            metrics = _build_metrics_from_result(simulation_id, result)
            message = {
                "type": "metrics",
                "simulation_id": simulation_id,
                "timestamp_s": datetime.now().timestamp(),
                "metrics": metrics.model_dump(),
            }

            await manager.broadcast_metrics(message)

    except WebSocketDisconnect:
        await manager.disconnect_metrics(websocket)
    except Exception as e:
        logger.error(f"WebSocket metrics error: {e}")
        await manager.disconnect_metrics(websocket)


# ── Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import numpy as np  # Required for helper functions

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
