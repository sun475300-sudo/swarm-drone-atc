"""P714 — TimescaleDB async 클라이언트 (asyncpg 기반)."""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

try:
    import asyncpg
    _HAS_ASYNCPG = True
except ImportError:
    asyncpg = None  # type: ignore
    _HAS_ASYNCPG = False

_DSN = os.environ.get(
    "SDACS_DB_DSN",
    "postgresql://sdacs:sdacs@localhost:5432/sdacs",
)

_pool: Optional[Any] = None


async def get_pool():
    global _pool
    if not _HAS_ASYNCPG:
        raise RuntimeError("asyncpg not installed: pip install asyncpg")
    if _pool is None:
        _pool = await asyncpg.create_pool(_DSN, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def acquire() -> AsyncIterator[Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def insert_run(scenario: str, method: str, seed: int, n_drones: int, duration_s: float) -> str:
    async with acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO sim_runs (scenario, method, seed, n_drones, duration_s)
               VALUES ($1, $2, $3, $4, $5) RETURNING run_id""",
            scenario, method, seed, n_drones, duration_s,
        )
        return str(row["run_id"])


async def finish_run(run_id: str, metrics: dict) -> None:
    async with acquire() as conn:
        await conn.execute(
            """UPDATE sim_runs SET finished_at = NOW(), status = 'done', metrics = $2
               WHERE run_id = $1""",
            uuid.UUID(run_id), metrics,
        )


async def insert_telemetry_batch(rows: list[dict]) -> None:
    """rows: [{ts, run_id, drone_id, x, y, z, vx, vy, vz, battery_pct, state}]"""
    if not rows:
        return
    async with acquire() as conn:
        await conn.executemany(
            """INSERT INTO telemetry (ts, run_id, drone_id, x, y, z, vx, vy, vz, battery_pct, state)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
            [
                (r["ts"], uuid.UUID(r["run_id"]), r["drone_id"],
                 r["x"], r["y"], r["z"],
                 r.get("vx"), r.get("vy"), r.get("vz"),
                 r.get("battery_pct"), r.get("state"))
                for r in rows
            ],
        )


async def query_run_metrics(run_id: str) -> Optional[dict]:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT metrics, status, started_at, finished_at FROM sim_runs WHERE run_id = $1",
            uuid.UUID(run_id),
        )
        if row is None:
            return None
        return dict(row)
