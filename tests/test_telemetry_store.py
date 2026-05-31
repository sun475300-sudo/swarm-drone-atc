"""P714 TelemetryStore 단위 테스트 (asyncpg mock 사용)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.telemetry_store import (
    ConflictEvent,
    SimulationRun,
    TelemetryPoint,
    TelemetryStore,
)


def _utcnow() -> datetime:
    return datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def store() -> TelemetryStore:
    return TelemetryStore()


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.executemany = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value={"unresolved": 2, "resolved": 5})
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    return conn


@pytest.fixture
def patch_acquire(mock_conn):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    with patch("api.telemetry_store.acquire", _acquire):
        yield mock_conn


# ---------- TelemetryPoint ----------

def test_telemetry_point_immutable():
    p = TelemetryPoint(ts=_utcnow(), drone_id="d1", run_id="r1", x=1.0, y=2.0, z=3.0)
    with pytest.raises(Exception):
        p.drone_id = "d2"  # type: ignore[misc]


def test_telemetry_point_defaults():
    p = TelemetryPoint(ts=_utcnow(), drone_id="d1", run_id="r1", x=0, y=0, z=0)
    assert p.battery_pct == 100.0
    assert p.state == "flying"
    assert p.speed == 0.0


# ---------- insert_telemetry ----------

@pytest.mark.asyncio
async def test_insert_telemetry_empty_is_noop(store, patch_acquire):
    await store.insert_telemetry([])
    patch_acquire.executemany.assert_not_called()


@pytest.mark.asyncio
async def test_insert_telemetry_calls_executemany(store, patch_acquire):
    pts = [
        TelemetryPoint(ts=_utcnow(), drone_id=f"d{i}", run_id="run1",
                       x=float(i), y=0.0, z=10.0)
        for i in range(3)
    ]
    await store.insert_telemetry(pts)
    patch_acquire.executemany.assert_called_once()
    args = patch_acquire.executemany.call_args[0]
    assert len(args[1]) == 3


@pytest.mark.asyncio
async def test_insert_telemetry_passes_all_fields(store, patch_acquire):
    pt = TelemetryPoint(
        ts=_utcnow(), drone_id="d1", run_id="r1",
        x=1.0, y=2.0, z=3.0, vx=0.1, vy=0.2, vz=0.3,
        speed=5.0, battery_pct=80.0, state="hovering",
    )
    await store.insert_telemetry([pt])
    row = patch_acquire.executemany.call_args[0][1][0]
    assert row[1] == "d1"
    assert row[3] == 1.0
    assert row[10] == 80.0
    assert row[11] == "hovering"


# ---------- insert_conflict ----------

@pytest.mark.asyncio
async def test_insert_conflict(store, patch_acquire):
    ev = ConflictEvent(
        ts=_utcnow(), run_id="r1",
        drone_a="d1", drone_b="d2",
        cpa_dist_m=3.5, resolved=True,
    )
    await store.insert_conflict(ev)
    patch_acquire.execute.assert_called_once()
    call_args = patch_acquire.execute.call_args[0]
    assert "d1" in call_args
    assert call_args[-1] is True  # resolved


# ---------- upsert_run ----------

@pytest.mark.asyncio
async def test_upsert_run_serializes_metrics(store, patch_acquire):
    run = SimulationRun(
        run_id="r1", scenario="corridor",
        drone_count=10, seed=42,
        metrics={"NMR": 0.0, "AU": 0.98},
    )
    await store.upsert_run(run)
    patch_acquire.execute.assert_called_once()
    args = patch_acquire.execute.call_args[0]
    metrics_arg = args[-1]
    parsed = json.loads(metrics_arg)
    assert parsed["NMR"] == 0.0
    assert parsed["AU"] == 0.98


# ---------- latest_telemetry ----------

@pytest.mark.asyncio
async def test_latest_telemetry_returns_dicts(store, patch_acquire):
    patch_acquire.fetch.return_value = [
        {"ts": _utcnow(), "drone_id": "d1", "x": 1.0, "y": 2.0,
         "z": 3.0, "speed": 5.0, "battery_pct": 90.0, "state": "flying"}
    ]
    result = await store.latest_telemetry("r1", limit=50)
    assert isinstance(result, list)
    assert result[0]["drone_id"] == "d1"


@pytest.mark.asyncio
async def test_latest_telemetry_default_limit(store, patch_acquire):
    await store.latest_telemetry("r1")
    call_args = patch_acquire.fetch.call_args[0]
    assert 100 in call_args


# ---------- conflict_summary ----------

@pytest.mark.asyncio
async def test_conflict_summary(store, patch_acquire):
    summary = await store.conflict_summary("r1")
    assert summary["unresolved"] == 2
    assert summary["resolved"] == 5


@pytest.mark.asyncio
async def test_conflict_summary_passes_run_id(store, patch_acquire):
    await store.conflict_summary("myrun")
    args = patch_acquire.fetchrow.call_args[0]
    assert "myrun" in args
