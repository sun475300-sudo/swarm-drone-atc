"""P714 — TimescaleDB 스키마 및 클라이언트 단위 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"
CLIENT_PATH = Path(__file__).parent.parent / "db" / "timescale_client.py"


class TestSchemaFile:
    def test_schema_file_exists(self):
        assert SCHEMA_PATH.exists(), "db/schema.sql missing"

    def test_schema_has_hypertable(self):
        content = SCHEMA_PATH.read_text()
        assert "create_hypertable" in content

    def test_schema_has_retention_policy(self):
        content = SCHEMA_PATH.read_text()
        assert "add_retention_policy" in content

    def test_schema_has_telemetry_table(self):
        content = SCHEMA_PATH.read_text()
        assert "CREATE TABLE IF NOT EXISTS telemetry" in content

    def test_schema_has_sim_runs_table(self):
        content = SCHEMA_PATH.read_text()
        assert "CREATE TABLE IF NOT EXISTS sim_runs" in content

    def test_schema_has_audit_log(self):
        content = SCHEMA_PATH.read_text()
        assert "audit_log" in content


class TestClientModule:
    def test_client_file_exists(self):
        assert CLIENT_PATH.exists(), "db/timescale_client.py missing"

    def test_client_import_ok(self):
        import db.timescale_client as tc
        assert callable(tc.insert_run)
        assert callable(tc.finish_run)
        assert callable(tc.insert_telemetry_batch)
        assert callable(tc.query_run_metrics)
