"""P714 — 드론 텔레메트리 + 이벤트 영속 저장소 (TimescaleDB 백엔드)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from api.db import acquire


@dataclass(frozen=True)
class TelemetryPoint:
    ts: datetime
    drone_id: str
    run_id: str
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    speed: float = 0.0
    battery_pct: float = 100.0
    state: str = "flying"


@dataclass(frozen=True)
class ConflictEvent:
    ts: datetime
    run_id: str
    drone_a: str
    drone_b: str
    cpa_dist_m: float
    resolved: bool = False


@dataclass
class SimulationRun:
    run_id: str
    scenario: str
    drone_count: int = 0
    seed: int | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class TelemetryStore:
    """TimescaleDB 기반 텔레메트리 저장/조회."""

    async def insert_telemetry(self, points: list[TelemetryPoint]) -> None:
        if not points:
            return
        async with acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO drone_telemetry
                    (ts, drone_id, run_id, x, y, z, vx, vy, vz, speed, battery_pct, state)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT DO NOTHING
                """,
                [
                    (p.ts, p.drone_id, p.run_id,
                     p.x, p.y, p.z, p.vx, p.vy, p.vz,
                     p.speed, p.battery_pct, p.state)
                    for p in points
                ],
            )

    async def insert_conflict(self, event: ConflictEvent) -> None:
        async with acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conflict_events
                    (ts, run_id, drone_a, drone_b, cpa_dist_m, resolved)
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT DO NOTHING
                """,
                event.ts, event.run_id, event.drone_a, event.drone_b,
                event.cpa_dist_m, event.resolved,
            )

    async def upsert_run(self, run: SimulationRun) -> None:
        async with acquire() as conn:
            await conn.execute(
                """
                INSERT INTO simulation_runs
                    (run_id, scenario, started_at, ended_at, drone_count, seed, metrics)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (run_id) DO UPDATE SET
                    ended_at    = EXCLUDED.ended_at,
                    drone_count = EXCLUDED.drone_count,
                    seed        = EXCLUDED.seed,
                    metrics     = EXCLUDED.metrics
                """,
                run.run_id, run.scenario, run.started_at, run.ended_at,
                run.drone_count, run.seed, json.dumps(run.metrics),
            )

    async def latest_telemetry(
        self, run_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ts, drone_id, x, y, z, speed, battery_pct, state
                FROM drone_telemetry
                WHERE run_id = $1
                ORDER BY ts DESC
                LIMIT $2
                """,
                run_id, limit,
            )
        return [dict(r) for r in rows]

    async def conflict_summary(self, run_id: str) -> dict[str, int]:
        async with acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE NOT resolved) AS unresolved,
                    COUNT(*) FILTER (WHERE resolved)     AS resolved
                FROM conflict_events
                WHERE run_id = $1
                """,
                run_id,
            )
        return {"unresolved": row["unresolved"], "resolved": row["resolved"]}
