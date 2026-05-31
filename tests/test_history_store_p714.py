"""P714 — PostgreSQL/TimescaleDB 이력 저장소 테스트 (SQLite 폴백 사용)."""

from __future__ import annotations

import time

import pytest

from simulation.history_store import (
    RETENTION_DAYS,
    HistoryStore,
    SQLiteHistoryStore,
    TimescaleHistoryStore,
)


@pytest.fixture
def store():
    """인메모리 SQLite 저장소 픽스처."""
    s = SQLiteHistoryStore(":memory:")
    yield s
    s.close()


class TestSQLiteHistoryStore:
    def test_save_and_query(self, store: SQLiteHistoryStore):
        record_id = store.save({"conflicts": 5, "scenario_id": "01_corridor"})
        assert record_id is not None
        results = store.query(since_hours=1)
        assert len(results) == 1
        assert results[0]["result"]["conflicts"] == 5

    def test_save_with_tags(self, store: SQLiteHistoryStore):
        store.save({"collisions": 0}, tags={"scenario": "02_merge", "method": "cbs"})
        results = store.query(scenario="02_merge", since_hours=1)
        assert len(results) == 1
        assert results[0]["tags"]["method"] == "cbs"

    def test_query_empty(self, store: SQLiteHistoryStore):
        results = store.query(since_hours=1)
        assert results == []

    def test_query_scenario_filter(self, store: SQLiteHistoryStore):
        store.save({"x": 1}, tags={"scenario": "s01"})
        store.save({"x": 2}, tags={"scenario": "s02"})
        results = store.query(scenario="s01", since_hours=1)
        assert len(results) == 1
        assert results[0]["tags"]["scenario"] == "s01"

    def test_query_limit(self, store: SQLiteHistoryStore):
        for i in range(10):
            store.save({"i": i})
        results = store.query(since_hours=1, limit=3)
        assert len(results) == 3

    def test_cleanup_old_records(self, store: SQLiteHistoryStore):
        # 최신 레코드 추가
        store.save({"fresh": True})
        # 보존 기간 초과 레코드 직접 삽입
        old_ts = time.time() - (RETENTION_DAYS + 1) * 86400
        store._conn.execute(
            "INSERT INTO sim_results (created_at, scenario, tags, payload) VALUES (?,?,?,?)",
            (old_ts, "old", "{}", '{"old": true}'),
        )
        store._conn.commit()

        deleted = store.cleanup_old_records()
        assert deleted == 1

        # 신규 레코드는 남아있어야 한다
        remaining = store.query(since_hours=24 * 365)
        assert len(remaining) == 1
        assert remaining[0]["result"]["fresh"] is True

    def test_cleanup_no_old_records(self, store: SQLiteHistoryStore):
        store.save({"recent": True})
        deleted = store.cleanup_old_records()
        assert deleted == 0

    def test_context_manager(self):
        with SQLiteHistoryStore(":memory:") as s:
            s.save({"test": True})
            results = s.query(since_hours=1)
        assert len(results) == 1

    def test_query_returns_iso_timestamp(self, store: SQLiteHistoryStore):
        store.save({"ts_test": True})
        results = store.query(since_hours=1)
        assert "T" in results[0]["created_at"]  # ISO format 확인


class TestHistoryStoreFactory:
    def test_create_returns_sqlite_without_dsn(self):
        store = HistoryStore.create(db_path=":memory:")
        assert isinstance(store, SQLiteHistoryStore)
        store.close()

    def test_create_falls_back_to_sqlite_on_bad_dsn(self):
        store = HistoryStore.create(dsn="postgresql://invalid:5432/nonexistent")
        assert isinstance(store, SQLiteHistoryStore)
        store.close()


class TestTimescaleHistoryStoreImport:
    def test_class_importable(self):
        assert TimescaleHistoryStore is not None

    def test_init_raises_without_psycopg2(self, monkeypatch):
        import sys
        monkeypatch.setitem(sys.modules, "psycopg2", None)
        with pytest.raises((ImportError, TypeError)):
            TimescaleHistoryStore("postgresql://fake/fake")
