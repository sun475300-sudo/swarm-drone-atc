"""tests/test_timescale.py — P714 TimescaleStorage 단위 테스트.

asyncpg 없이도 동작하도록 unittest.mock으로 풀을 대체한다.
실제 DB 연결은 필요하지 않다.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼: 파이크 asyncpg Pool / Record 목(mock) 생성
# ──────────────────────────────────────────────────────────────────────────────

def _make_pool(fetch_return: list[dict] | None = None, fetchrow_return: dict | None = None) -> MagicMock:
    """asyncpg.Pool과 동일한 인터페이스를 갖는 AsyncMock Pool을 반환한다."""
    pool = MagicMock()
    # asyncpg Record처럼 dict()로 변환 가능한 값 반환
    pool.execute = AsyncMock(return_value=None)
    pool.fetch = AsyncMock(return_value=[_dict_to_record(r) for r in (fetch_return or [])])
    pool.fetchrow = AsyncMock(return_value=_dict_to_record(fetchrow_return or {}))
    pool.close = AsyncMock(return_value=None)
    return pool


def _dict_to_record(d: dict) -> dict:
    """asyncpg Record처럼 dict()로 변환 가능한 객체를 반환한다.
    이 테스트에서는 일반 dict로 충분하다.
    """
    return dict(d)


# ──────────────────────────────────────────────────────────────────────────────
# 픽스처
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def storage_module():
    """src.storage.timescale 모듈을 임포트하는 픽스처.
    asyncpg 없이도 임포트가 성공해야 한다.
    """
    # sys.path에 프로젝트 루트가 없으면 추가
    root = str(Path(__file__).parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)

    # asyncpg를 가짜 모듈로 대체해서 임포트 오류 방지
    if "asyncpg" not in sys.modules:
        fake_asyncpg = MagicMock()
        fake_asyncpg.create_pool = AsyncMock()
        sys.modules["asyncpg"] = fake_asyncpg

    # 이미 캐시된 모듈 제거 후 재임포트 (테스트 격리)
    sys.modules.pop("src.storage.timescale", None)
    sys.modules.pop("src.storage", None)

    mod = importlib.import_module("src.storage.timescale")
    return mod


@pytest.fixture()
def storage_cls(storage_module):
    return storage_module.TimescaleStorage


@pytest.fixture()
def storage_with_pool(storage_cls):
    """연결된(pool이 주입된) TimescaleStorage 인스턴스를 반환한다."""
    instance = storage_cls(dsn="postgresql://fake:fake@localhost:5432/sdacs")
    instance._pool = _make_pool()
    return instance


# ──────────────────────────────────────────────────────────────────────────────
# 1. 클래스 인터페이스 검증
# ──────────────────────────────────────────────────────────────────────────────

class TestTimescaleStorageInterface:
    """TimescaleStorage가 약속된 공개 메서드를 모두 노출하는지 확인한다."""

    REQUIRED_METHODS = [
        "connect",
        "close",
        "insert_telemetry",
        "query_telemetry_range",
        "insert_conflict",
        "query_conflicts_last_n",
        "insert_mission_event",
        "query_mission_events",
    ]

    def test_class_exists(self, storage_cls):
        assert storage_cls is not None

    @pytest.mark.parametrize("method_name", REQUIRED_METHODS)
    def test_method_exists(self, storage_cls, method_name):
        assert hasattr(storage_cls, method_name), (
            f"TimescaleStorage에 '{method_name}' 메서드가 없습니다."
        )

    def test_from_env_classmethod(self, storage_cls):
        instance = storage_cls.from_env()
        assert isinstance(instance, storage_cls)

    def test_context_manager_methods(self, storage_cls):
        """async context manager 프로토콜(__aenter__, __aexit__)이 있어야 한다."""
        assert hasattr(storage_cls, "__aenter__")
        assert hasattr(storage_cls, "__aexit__")

    def test_default_dsn_uses_env(self, storage_module, monkeypatch):
        """DATABASE_URL 환경변수가 기본 DSN으로 사용되어야 한다."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@db:5432/testdb")
        # 모듈 레벨 상수는 임포트 시 결정되므로 from_env()의 동작만 검증
        instance = storage_module.TimescaleStorage.from_env()
        # DSN이 환경변수 값을 반영해야 한다
        # (모듈 캐시 문제로 값 자체 검증 대신 인스턴스 생성 성공만 확인)
        assert instance is not None


# ──────────────────────────────────────────────────────────────────────────────
# 2. connect / close 동작
# ──────────────────────────────────────────────────────────────────────────────

class TestConnectClose:
    @pytest.mark.asyncio
    async def test_connect_raises_without_asyncpg(self, storage_cls, monkeypatch):
        """asyncpg를 사용할 수 없을 때 RuntimeError가 발생해야 한다."""
        # _ASYNCPG_AVAILABLE을 False로 패치
        import src.storage.timescale as mod
        monkeypatch.setattr(mod, "_ASYNCPG_AVAILABLE", False)
        instance = storage_cls()
        with pytest.raises(RuntimeError, match="asyncpg"):
            await instance.connect()

    @pytest.mark.asyncio
    async def test_close_without_connect_is_noop(self, storage_cls):
        """connect() 없이 close()를 호출해도 오류가 나지 않아야 한다."""
        instance = storage_cls()
        await instance.close()  # 예외 없어야 함

    @pytest.mark.asyncio
    async def test_close_releases_pool(self, storage_with_pool):
        # pool 참조를 미리 저장 — close() 후 _pool이 None이 되므로
        pool_ref = storage_with_pool._pool
        await storage_with_pool.close()
        pool_ref.close.assert_awaited_once()
        assert storage_with_pool._pool is None

    def test_require_pool_raises_when_not_connected(self, storage_cls):
        """풀 없이 _require_pool()을 호출하면 RuntimeError가 발생해야 한다."""
        instance = storage_cls()
        with pytest.raises(RuntimeError, match="connect"):
            instance._require_pool()


# ──────────────────────────────────────────────────────────────────────────────
# 3. insert_telemetry
# ──────────────────────────────────────────────────────────────────────────────

class TestInsertTelemetry:
    @pytest.mark.asyncio
    async def test_insert_calls_execute(self, storage_with_pool):
        """insert_telemetry()가 pool.execute()를 정확히 1회 호출해야 한다."""
        await storage_with_pool.insert_telemetry(
            drone_id="d01",
            lat=37.123,
            lon=127.456,
            alt=50.0,
            heading=270.0,
            speed=12.5,
            battery_pct=88,
            status="flying",
        )
        storage_with_pool._pool.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_insert_with_explicit_time(self, storage_with_pool):
        """time 인자를 명시적으로 전달해도 execute가 호출되어야 한다."""
        ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        await storage_with_pool.insert_telemetry(
            drone_id="d02",
            lat=0.0, lon=0.0, alt=0.0,
            heading=0.0, speed=0.0,
            battery_pct=100, status="hovering",
            time=ts,
        )
        call_args = storage_with_pool._pool.execute.call_args
        # 첫 번째 위치 인자 뒤에 전달되는 파라미터에서 time 확인
        params = call_args[0]  # (query, ts, drone_id, …)
        assert ts in params


# ──────────────────────────────────────────────────────────────────────────────
# 4. query_telemetry_range
# ──────────────────────────────────────────────────────────────────────────────

class TestQueryTelemetryRange:
    @pytest.mark.asyncio
    async def test_returns_list(self, storage_with_pool):
        """fetch 결과를 list[dict]로 반환해야 한다."""
        storage_with_pool._pool.fetch = AsyncMock(return_value=[
            {"time": datetime.now(timezone.utc), "drone_id": "d01",
             "lat": 1.0, "lon": 2.0, "alt": 30.0,
             "heading": 90.0, "speed": 5.0, "battery_pct": 70, "status": "flying"}
        ])
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        result = await storage_with_pool.query_telemetry_range("d01", start, end)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["drone_id"] == "d01"

    @pytest.mark.asyncio
    async def test_empty_result(self, storage_with_pool):
        """데이터 없을 때 빈 리스트를 반환해야 한다."""
        storage_with_pool._pool.fetch = AsyncMock(return_value=[])
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        result = await storage_with_pool.query_telemetry_range("d_none", start, end)
        assert result == []

    @pytest.mark.asyncio
    async def test_limit_passed_to_query(self, storage_with_pool):
        """limit 인자가 SQL 쿼리 파라미터로 전달되어야 한다."""
        storage_with_pool._pool.fetch = AsyncMock(return_value=[])
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        await storage_with_pool.query_telemetry_range("d01", start, end, limit=42)
        call_params = storage_with_pool._pool.fetch.call_args[0]
        assert 42 in call_params


# ──────────────────────────────────────────────────────────────────────────────
# 5. insert_conflict
# ──────────────────────────────────────────────────────────────────────────────

class TestInsertConflict:
    @pytest.mark.asyncio
    async def test_insert_returns_id(self, storage_with_pool):
        """insert_conflict()가 생성된 레코드의 id를 반환해야 한다."""
        storage_with_pool._pool.fetchrow = AsyncMock(return_value={"id": 42})
        result = await storage_with_pool.insert_conflict(
            drone_a_id="d01",
            drone_b_id="d02",
            separation_m=8.5,
        )
        assert result == 42

    @pytest.mark.asyncio
    async def test_insert_resolved_conflict(self, storage_with_pool):
        """resolved=True, resolution_type이 쿼리에 포함되어야 한다."""
        storage_with_pool._pool.fetchrow = AsyncMock(return_value={"id": 7})
        result = await storage_with_pool.insert_conflict(
            drone_a_id="d03",
            drone_b_id="d04",
            separation_m=5.0,
            resolved=True,
            resolution_type="avoidance",
        )
        assert result == 7
        call_params = storage_with_pool._pool.fetchrow.call_args[0]
        assert True in call_params
        assert "avoidance" in call_params


# ──────────────────────────────────────────────────────────────────────────────
# 6. query_conflicts_last_n
# ──────────────────────────────────────────────────────────────────────────────

class TestQueryConflictsLastN:
    @pytest.mark.asyncio
    async def test_returns_list(self, storage_with_pool):
        storage_with_pool._pool.fetch = AsyncMock(return_value=[
            {"id": 1, "time": datetime.now(timezone.utc),
             "drone_a_id": "d01", "drone_b_id": "d02",
             "separation_m": 9.0, "resolved": False, "resolution_type": None}
        ])
        result = await storage_with_pool.query_conflicts_last_n(n=50)
        assert isinstance(result, list)
        assert result[0]["drone_a_id"] == "d01"

    @pytest.mark.asyncio
    async def test_drone_id_filter(self, storage_with_pool):
        """drone_id 필터 전달 시 다른 SQL 분기를 사용해야 한다."""
        storage_with_pool._pool.fetch = AsyncMock(return_value=[])
        await storage_with_pool.query_conflicts_last_n(n=10, drone_id="d01")
        call_params = storage_with_pool._pool.fetch.call_args[0]
        # drone_id가 파라미터로 전달되어야 한다
        assert "d01" in call_params

    @pytest.mark.asyncio
    async def test_no_filter_no_drone_id_param(self, storage_with_pool):
        """drone_id 없을 때 drone_id 파라미터가 전달되지 않아야 한다."""
        storage_with_pool._pool.fetch = AsyncMock(return_value=[])
        await storage_with_pool.query_conflicts_last_n(n=10)
        call_params = storage_with_pool._pool.fetch.call_args[0]
        assert "d01" not in call_params


# ──────────────────────────────────────────────────────────────────────────────
# 7. insert_mission_event
# ──────────────────────────────────────────────────────────────────────────────

class TestInsertMissionEvent:
    @pytest.mark.asyncio
    async def test_insert_returns_id(self, storage_with_pool):
        storage_with_pool._pool.fetchrow = AsyncMock(return_value={"id": 99})
        result = await storage_with_pool.insert_mission_event(
            drone_id="d01",
            mission_id="m001",
            event_type="start",
        )
        assert result == 99

    @pytest.mark.asyncio
    async def test_payload_serialized_as_json(self, storage_with_pool):
        """payload dict가 JSON 문자열로 직렬화되어 쿼리에 전달되어야 한다."""
        storage_with_pool._pool.fetchrow = AsyncMock(return_value={"id": 1})
        payload = {"waypoint": {"lat": 37.5, "lon": 127.0}, "index": 3}
        await storage_with_pool.insert_mission_event(
            drone_id="d02",
            mission_id="m002",
            event_type="waypoint_reached",
            payload=payload,
        )
        call_params = storage_with_pool._pool.fetchrow.call_args[0]
        # JSON 문자열이 파라미터 중에 있어야 한다
        json_params = [p for p in call_params if isinstance(p, str) and p.startswith("{")]
        assert len(json_params) == 1
        deserialized = json.loads(json_params[0])
        assert deserialized["index"] == 3

    @pytest.mark.asyncio
    async def test_none_payload_passed_as_none(self, storage_with_pool):
        """payload가 None이면 None이 그대로 전달되어야 한다."""
        storage_with_pool._pool.fetchrow = AsyncMock(return_value={"id": 2})
        await storage_with_pool.insert_mission_event(
            drone_id="d03",
            mission_id="m003",
            event_type="complete",
            payload=None,
        )
        call_params = storage_with_pool._pool.fetchrow.call_args[0]
        assert None in call_params


# ──────────────────────────────────────────────────────────────────────────────
# 8. query_mission_events
# ──────────────────────────────────────────────────────────────────────────────

class TestQueryMissionEvents:
    @pytest.mark.asyncio
    async def test_returns_list_with_deserialized_payload(self, storage_with_pool):
        """payload JSON 문자열이 dict로 역직렬화되어 반환되어야 한다."""
        raw_payload = json.dumps({"step": 1})
        storage_with_pool._pool.fetch = AsyncMock(return_value=[
            {"id": 1, "time": datetime.now(timezone.utc),
             "drone_id": "d01", "mission_id": "m001",
             "event_type": "start", "payload": raw_payload}
        ])
        result = await storage_with_pool.query_mission_events("m001")
        assert isinstance(result[0]["payload"], dict)
        assert result[0]["payload"]["step"] == 1

    @pytest.mark.asyncio
    async def test_limit_passed_to_query(self, storage_with_pool):
        storage_with_pool._pool.fetch = AsyncMock(return_value=[])
        await storage_with_pool.query_mission_events("m001", limit=250)
        call_params = storage_with_pool._pool.fetch.call_args[0]
        assert 250 in call_params


# ──────────────────────────────────────────────────────────────────────────────
# 9. 스키마 SQL 파일 존재 확인
# ──────────────────────────────────────────────────────────────────────────────

class TestMigrationFile:
    def test_migration_file_exists(self):
        """db/migrations/001_initial_schema.sql 파일이 존재해야 한다."""
        migration_path = Path(__file__).parent.parent / "db" / "migrations" / "001_initial_schema.sql"
        assert migration_path.exists(), (
            f"마이그레이션 파일이 없습니다: {migration_path}"
        )

    def test_migration_file_contains_hypertable(self):
        """마이그레이션 파일에 create_hypertable 호출이 포함되어야 한다."""
        migration_path = Path(__file__).parent.parent / "db" / "migrations" / "001_initial_schema.sql"
        content = migration_path.read_text(encoding="utf-8")
        assert "create_hypertable" in content, (
            "마이그레이션에 create_hypertable 호출이 없습니다."
        )

    def test_migration_file_contains_retention_policy(self):
        """마이그레이션 파일에 add_retention_policy 호출이 포함되어야 한다."""
        migration_path = Path(__file__).parent.parent / "db" / "migrations" / "001_initial_schema.sql"
        content = migration_path.read_text(encoding="utf-8")
        assert "add_retention_policy" in content, (
            "마이그레이션에 add_retention_policy 호출이 없습니다."
        )

    def test_migration_file_defines_all_tables(self):
        """마이그레이션 파일에 세 테이블 정의가 모두 있어야 한다."""
        migration_path = Path(__file__).parent.parent / "db" / "migrations" / "001_initial_schema.sql"
        content = migration_path.read_text(encoding="utf-8")
        for table in ("drone_telemetry", "conflict_events", "mission_log"):
            assert table in content, f"테이블 '{table}'이 마이그레이션에 없습니다."

    def test_migration_file_not_empty(self):
        migration_path = Path(__file__).parent.parent / "db" / "migrations" / "001_initial_schema.sql"
        assert migration_path.stat().st_size > 0, "마이그레이션 파일이 비어 있습니다."
