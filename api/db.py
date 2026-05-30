"""SDACS 데이터베이스 스키마 및 연결 유틸리티 — Phase P714.

PostgreSQL + TimescaleDB 기반 이력 저장소.

스키마:
    telemetry        — 드론 위치/속도 시계열 (TimescaleDB hypertable)
    conflicts        — 충돌 이벤트 이력
    runs             — 시뮬레이션 실행 기록
    audit_events     — 감사 로그 (API 접근 기록)

환경변수:
    SDACS_DB_URL     — PostgreSQL DSN (예: postgresql://user:pass@host:5432/sdacs)

사용법:
    from api.db import get_db, init_schema

    # 앱 시작 시 스키마 초기화
    async with get_db() as conn:
        await init_schema(conn)

주의: asyncpg가 설치된 경우에만 실제 DB 연결. 미설치 시 no-op 스텁 동작.
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

_DB_URL: str = os.getenv("SDACS_DB_URL", "")

# DDL — TimescaleDB hypertable on 'telemetry'
_SCHEMA_DDL = """
-- 드론 텔레메트리 (1 kHz 수집 → 30일 보존)
CREATE TABLE IF NOT EXISTS telemetry (
    time        TIMESTAMPTZ         NOT NULL,
    drone_id    TEXT                NOT NULL,
    run_id      TEXT,
    x           DOUBLE PRECISION    NOT NULL,
    y           DOUBLE PRECISION    NOT NULL,
    z           DOUBLE PRECISION    NOT NULL,
    vx          DOUBLE PRECISION    NOT NULL DEFAULT 0,
    vy          DOUBLE PRECISION    NOT NULL DEFAULT 0,
    vz          DOUBLE PRECISION    NOT NULL DEFAULT 0,
    heading     DOUBLE PRECISION    NOT NULL DEFAULT 0,
    battery_pct DOUBLE PRECISION    NOT NULL DEFAULT 100
);

-- TimescaleDB hypertable 변환 (이미 존재하면 무시)
SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);

-- 30일 보존 정책
SELECT add_retention_policy('telemetry', INTERVAL '30 days', if_not_exists => TRUE);

-- 충돌/근접 이벤트 이력
CREATE TABLE IF NOT EXISTS conflicts (
    id          BIGSERIAL           PRIMARY KEY,
    time        TIMESTAMPTZ         NOT NULL DEFAULT now(),
    run_id      TEXT,
    drone_a     TEXT                NOT NULL,
    drone_b     TEXT                NOT NULL,
    dist_m      DOUBLE PRECISION    NOT NULL,
    cpa_t_s     DOUBLE PRECISION    NOT NULL DEFAULT 0,
    resolved    BOOLEAN             NOT NULL DEFAULT FALSE
);

-- 시뮬레이션 실행 기록
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT                PRIMARY KEY,
    scenario_id TEXT                NOT NULL,
    status      TEXT                NOT NULL DEFAULT 'queued',
    started_at  TIMESTAMPTZ         NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    metrics     JSONB               NOT NULL DEFAULT '{}'
);

-- 감사 로그
CREATE TABLE IF NOT EXISTS audit_events (
    id          BIGSERIAL           PRIMARY KEY,
    time        TIMESTAMPTZ         NOT NULL DEFAULT now(),
    sub         TEXT                NOT NULL,
    role        TEXT                NOT NULL,
    action      TEXT                NOT NULL,
    detail      TEXT                NOT NULL DEFAULT ''
);

-- 기본 인덱스
CREATE INDEX IF NOT EXISTS telemetry_drone_time ON telemetry (drone_id, time DESC);
CREATE INDEX IF NOT EXISTS conflicts_run_time   ON conflicts (run_id, time DESC);
CREATE INDEX IF NOT EXISTS audit_sub_time       ON audit_events (sub, time DESC);
"""


# ---------------------------------------------------------------------------
# asyncpg 연결 (없으면 no-op 스텁)
# ---------------------------------------------------------------------------

try:
    import asyncpg  # type: ignore
    _HAS_ASYNCPG = True
except ImportError:
    _HAS_ASYNCPG = False


class _StubConn:
    """asyncpg 미설치 시 사용되는 no-op 연결 스텁."""

    async def execute(self, query: str, *args: Any) -> None:
        pass

    async def fetch(self, query: str, *args: Any) -> list[dict]:
        return []

    async def fetchrow(self, query: str, *args: Any) -> dict | None:
        return None

    async def fetchval(self, query: str, *args: Any) -> Any:
        return None

    async def copy_records_to_table(self, *args: Any, **kwargs: Any) -> None:
        pass


@asynccontextmanager
async def get_db() -> AsyncIterator[Any]:
    """DB 연결 컨텍스트 매니저.

    SDACS_DB_URL이 설정되지 않거나 asyncpg가 없으면 no-op 스텁 반환.
    """
    if not _HAS_ASYNCPG or not _DB_URL:
        yield _StubConn()
        return

    conn = await asyncpg.connect(_DB_URL)
    try:
        yield conn
    finally:
        await conn.close()


async def init_schema(conn: Any) -> None:
    """DDL을 실행해 스키마를 초기화한다. 멱등 (IF NOT EXISTS)."""
    await conn.execute(_SCHEMA_DDL)


# ---------------------------------------------------------------------------
# 편의 함수 — 각 엔드포인트에서 직접 호출
# ---------------------------------------------------------------------------

async def insert_telemetry_batch(conn: Any, rows: list[dict]) -> None:
    """드론 텔레메트리 배치 삽입.

    Args:
        rows: [{drone_id, run_id, x, y, z, vx, vy, vz, heading, battery_pct}]
    """
    if not rows:
        return
    records = [
        (
            time.time(),
            r["drone_id"],
            r.get("run_id"),
            float(r["x"]),
            float(r["y"]),
            float(r["z"]),
            float(r.get("vx", 0)),
            float(r.get("vy", 0)),
            float(r.get("vz", 0)),
            float(r.get("heading", 0)),
            float(r.get("battery_pct", 100)),
        )
        for r in rows
    ]
    await conn.copy_records_to_table(
        "telemetry",
        records=records,
        columns=["time", "drone_id", "run_id", "x", "y", "z", "vx", "vy", "vz", "heading", "battery_pct"],
    )


async def insert_conflict(
    conn: Any,
    *,
    run_id: str | None,
    drone_a: str,
    drone_b: str,
    dist_m: float,
    cpa_t_s: float = 0.0,
) -> None:
    """충돌 이벤트 기록."""
    await conn.execute(
        "INSERT INTO conflicts (run_id, drone_a, drone_b, dist_m, cpa_t_s) VALUES ($1,$2,$3,$4,$5)",
        run_id, drone_a, drone_b, dist_m, cpa_t_s,
    )


async def upsert_run(conn: Any, *, run_id: str, scenario_id: str, status: str, metrics: dict | None = None) -> None:
    """시뮬레이션 실행 기록 upsert."""
    import json as _json
    await conn.execute(
        """
        INSERT INTO runs (run_id, scenario_id, status, metrics)
        VALUES ($1, $2, $3, $4::jsonb)
        ON CONFLICT (run_id) DO UPDATE
            SET status = EXCLUDED.status,
                finished_at = CASE WHEN EXCLUDED.status IN ('completed','failed') THEN now() ELSE runs.finished_at END,
                metrics = EXCLUDED.metrics
        """,
        run_id, scenario_id, status, _json.dumps(metrics or {}),
    )


async def insert_audit_event(conn: Any, *, sub: str, role: str, action: str, detail: str = "") -> None:
    """감사 이벤트를 DB에 기록."""
    await conn.execute(
        "INSERT INTO audit_events (sub, role, action, detail) VALUES ($1,$2,$3,$4)",
        sub, role, action, detail,
    )


async def fetch_telemetry_history(
    conn: Any,
    *,
    drone_id: str | None = None,
    run_id: str | None = None,
    limit: int = 1000,
) -> list[dict]:
    """텔레메트리 이력 조회."""
    clauses = []
    args: list[Any] = []
    if drone_id:
        args.append(drone_id)
        clauses.append(f"drone_id = ${len(args)}")
    if run_id:
        args.append(run_id)
        clauses.append(f"run_id = ${len(args)}")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    args.append(limit)
    rows = await conn.fetch(
        f"SELECT * FROM telemetry {where} ORDER BY time DESC LIMIT ${len(args)}",
        *args,
    )
    return [dict(r) for r in rows]
