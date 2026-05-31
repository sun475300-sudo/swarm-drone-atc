"""P714 — PostgreSQL + TimescaleDB telemetry store.

Schema:
    drone_telemetry  — hypertable, partitioned by time
    conflict_events  — regular table with FK reference
    run_records      — simulation run metadata

Retention:
    30-day drop_chunks policy applied to drone_telemetry.

Environment variables:
    SDACS_DB_DSN  — asyncpg DSN, e.g. postgresql://user:pass@localhost/sdacs

Usage (async):
    store = await TelemetryStore.create()
    await store.insert_telemetry(drone_id="D01", ts=time.time(), lat=35.1, lon=126.8, alt=50.0)
    rows = await store.query_telemetry("D01", limit=100)
    await store.close()
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger("sdacs.db_store")

_DSN_DEFAULT = "postgresql://sdacs:sdacs@localhost:5432/sdacs"
_DSN: str = os.environ.get("SDACS_DB_DSN", _DSN_DEFAULT)

# DDL executed once at startup
_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS drone_telemetry (
    time        TIMESTAMPTZ NOT NULL,
    drone_id    TEXT        NOT NULL,
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION,
    alt_m       DOUBLE PRECISION,
    vx_ms       DOUBLE PRECISION,
    vy_ms       DOUBLE PRECISION,
    vz_ms       DOUBLE PRECISION,
    heading_deg DOUBLE PRECISION,
    battery_pct DOUBLE PRECISION,
    run_id      TEXT
);

SELECT create_hypertable('drone_telemetry', 'time', if_not_exists => TRUE);

SELECT add_retention_policy(
    'drone_telemetry',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

CREATE TABLE IF NOT EXISTS conflict_events (
    id          BIGSERIAL   PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_id      TEXT,
    drone_a     TEXT        NOT NULL,
    drone_b     TEXT        NOT NULL,
    cpa_dist_m  DOUBLE PRECISION,
    resolved    BOOLEAN     DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS run_records (
    run_id      TEXT        PRIMARY KEY,
    scenario_id TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'queued',
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    metrics     JSONB
);

CREATE INDEX IF NOT EXISTS drone_telemetry_drone_id_idx
    ON drone_telemetry (drone_id, time DESC);

CREATE INDEX IF NOT EXISTS conflict_events_run_id_idx
    ON conflict_events (run_id, time DESC);
"""


@dataclass
class TelemetryRow:
    time: float  # Unix timestamp
    drone_id: str
    lat: float
    lon: float
    alt_m: float
    vx_ms: float = 0.0
    vy_ms: float = 0.0
    vz_ms: float = 0.0
    heading_deg: float = 0.0
    battery_pct: float = 100.0
    run_id: str | None = None


class TelemetryStore:
    """Async wrapper around asyncpg pool for drone telemetry persistence."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool

    @classmethod
    async def create(cls, dsn: str = _DSN, *, apply_schema: bool = True) -> "TelemetryStore":
        """Connect to Postgres and (optionally) create tables."""
        try:
            import asyncpg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("asyncpg required: pip install asyncpg") from exc

        pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10, command_timeout=30)
        store = cls(pool)
        if apply_schema:
            await store._apply_schema()
        LOGGER.info("TelemetryStore connected: %s", dsn.split("@")[-1])
        return store

    async def _apply_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_SCHEMA_SQL)

    async def insert_telemetry(self, row: TelemetryRow) -> None:
        from datetime import datetime, timezone

        ts = datetime.fromtimestamp(row.time, tz=timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO drone_telemetry
                    (time, drone_id, lat, lon, alt_m, vx_ms, vy_ms, vz_ms, heading_deg, battery_pct, run_id)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                """,
                ts,
                row.drone_id,
                row.lat,
                row.lon,
                row.alt_m,
                row.vx_ms,
                row.vy_ms,
                row.vz_ms,
                row.heading_deg,
                row.battery_pct,
                row.run_id,
            )

    async def insert_telemetry_batch(self, rows: list[TelemetryRow]) -> None:
        """Bulk-insert telemetry rows (one transaction)."""
        from datetime import datetime, timezone

        records = [
            (
                datetime.fromtimestamp(r.time, tz=timezone.utc),
                r.drone_id, r.lat, r.lon, r.alt_m,
                r.vx_ms, r.vy_ms, r.vz_ms, r.heading_deg, r.battery_pct, r.run_id,
            )
            for r in rows
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO drone_telemetry
                    (time, drone_id, lat, lon, alt_m, vx_ms, vy_ms, vz_ms, heading_deg, battery_pct, run_id)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                """,
                records,
            )

    async def query_telemetry(
        self,
        drone_id: str,
        *,
        limit: int = 200,
        since_s: float | None = None,
    ) -> list[dict[str, Any]]:
        from datetime import datetime, timezone

        if since_s is not None:
            since_ts = datetime.fromtimestamp(since_s, tz=timezone.utc)
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM drone_telemetry WHERE drone_id=$1 AND time > $2 ORDER BY time DESC LIMIT $3",
                    drone_id, since_ts, limit,
                )
        else:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM drone_telemetry WHERE drone_id=$1 ORDER BY time DESC LIMIT $2",
                    drone_id, limit,
                )
        return [dict(r) for r in rows]

    async def upsert_run(self, run_id: str, scenario_id: str, status: str, metrics: dict | None = None) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO run_records (run_id, scenario_id, status, metrics)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (run_id) DO UPDATE
                    SET status = EXCLUDED.status,
                        finished_at = CASE WHEN EXCLUDED.status IN ('completed','failed') THEN NOW() ELSE run_records.finished_at END,
                        metrics = COALESCE(EXCLUDED.metrics, run_records.metrics)
                """,
                run_id, scenario_id, status,
                json.dumps(metrics) if metrics else None,
            )

    async def insert_conflict(
        self, run_id: str, drone_a: str, drone_b: str, cpa_dist_m: float, resolved: bool = False
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conflict_events (run_id, drone_a, drone_b, cpa_dist_m, resolved)
                VALUES ($1, $2, $3, $4, $5)
                """,
                run_id, drone_a, drone_b, cpa_dist_m, resolved,
            )

    async def close(self) -> None:
        await self._pool.close()
        LOGGER.info("TelemetryStore pool closed")
