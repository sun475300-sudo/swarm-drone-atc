"""Tests for P714 — simulation/db_store.py (schema + store interface)."""
from __future__ import annotations

import time

import pytest


class TestTelemetryRow:
    def test_default_values(self) -> None:
        from simulation.db_store import TelemetryRow
        row = TelemetryRow(time=time.time(), drone_id="D01", lat=35.1, lon=126.8, alt_m=50.0)
        assert row.vx_ms == 0.0
        assert row.battery_pct == 100.0
        assert row.run_id is None

    def test_custom_values(self) -> None:
        from simulation.db_store import TelemetryRow
        row = TelemetryRow(
            time=1000.0,
            drone_id="D02",
            lat=35.2,
            lon=126.9,
            alt_m=30.0,
            vx_ms=2.5,
            vy_ms=-1.0,
            vz_ms=0.5,
            heading_deg=90.0,
            battery_pct=75.0,
            run_id="run-abc",
        )
        assert row.vx_ms == 2.5
        assert row.run_id == "run-abc"


class TestSchemaSql:
    def test_schema_contains_hypertable(self) -> None:
        from simulation.db_store import _SCHEMA_SQL
        assert "create_hypertable" in _SCHEMA_SQL

    def test_schema_contains_retention(self) -> None:
        from simulation.db_store import _SCHEMA_SQL
        assert "add_retention_policy" in _SCHEMA_SQL
        assert "30 days" in _SCHEMA_SQL

    def test_schema_creates_drone_telemetry(self) -> None:
        from simulation.db_store import _SCHEMA_SQL
        assert "drone_telemetry" in _SCHEMA_SQL

    def test_schema_creates_conflict_events(self) -> None:
        from simulation.db_store import _SCHEMA_SQL
        assert "conflict_events" in _SCHEMA_SQL

    def test_schema_creates_run_records(self) -> None:
        from simulation.db_store import _SCHEMA_SQL
        assert "run_records" in _SCHEMA_SQL

    def test_schema_has_indices(self) -> None:
        from simulation.db_store import _SCHEMA_SQL
        assert "CREATE INDEX" in _SCHEMA_SQL


class TestTelemetryStoreImport:
    def test_class_exists(self) -> None:
        from simulation.db_store import TelemetryStore
        assert TelemetryStore is not None

    def test_create_is_coroutine(self) -> None:
        import asyncio
        import inspect
        from simulation.db_store import TelemetryStore
        assert inspect.iscoroutinefunction(TelemetryStore.create)

    def test_insert_telemetry_is_coroutine(self) -> None:
        import inspect
        from simulation.db_store import TelemetryStore
        assert inspect.iscoroutinefunction(TelemetryStore.insert_telemetry)

    def test_query_telemetry_is_coroutine(self) -> None:
        import inspect
        from simulation.db_store import TelemetryStore
        assert inspect.iscoroutinefunction(TelemetryStore.query_telemetry)

    def test_upsert_run_is_coroutine(self) -> None:
        import inspect
        from simulation.db_store import TelemetryStore
        assert inspect.iscoroutinefunction(TelemetryStore.upsert_run)

    def test_insert_conflict_is_coroutine(self) -> None:
        import inspect
        from simulation.db_store import TelemetryStore
        assert inspect.iscoroutinefunction(TelemetryStore.insert_conflict)

    def test_close_is_coroutine(self) -> None:
        import inspect
        from simulation.db_store import TelemetryStore
        assert inspect.iscoroutinefunction(TelemetryStore.close)
