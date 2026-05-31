"""P714 — TimescaleDB 스키마 파일 검증."""
from __future__ import annotations

from pathlib import Path
import re
import pytest

MIGRATION = Path(__file__).parent.parent / "db" / "migrations" / "001_init_timescale.sql"


def _sql() -> str:
    return MIGRATION.read_text()


def test_migration_file_exists():
    assert MIGRATION.exists(), "db/migrations/001_init_timescale.sql 없음"


def test_timescaledb_extension():
    sql = _sql()
    assert "CREATE EXTENSION IF NOT EXISTS timescaledb" in sql


def test_telemetry_hypertable():
    sql = _sql()
    assert "create_hypertable('telemetry'" in sql


def test_retention_policy_30d():
    sql = _sql()
    assert "INTERVAL '30 days'" in sql


def test_users_table_has_role_check():
    sql = _sql()
    assert "CHECK (role IN ('viewer', 'operator', 'admin'))" in sql


def test_runs_table_has_status_check():
    sql = _sql()
    assert "CHECK (status IN ('queued', 'running', 'completed', 'failed'))" in sql


def test_seed_scenarios_present():
    sql = _sql()
    for scenario in ("empty_sky", "dense_traffic_50", "stress_200"):
        assert scenario in sql


def test_continuous_aggregate_defined():
    sql = _sql()
    assert "CREATE MATERIALIZED VIEW" in sql
    assert "timescaledb.continuous" in sql
