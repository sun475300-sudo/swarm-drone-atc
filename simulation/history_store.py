"""
P714 — 시뮬레이션 이력 저장소
==============================
PostgreSQL + TimescaleDB를 이용한 시뮬레이션 결과 이력 저장.
30일 보존 정책 자동 적용.

TimescaleDB가 없으면 SQLite로 폴백하여 개발·테스트 환경에서도 사용 가능.

사용법:
    store = HistoryStore.create(dsn="postgresql://...")
    store.save(result_dict, tags={"scenario": "01_corridor"})
    store.cleanup_old_records()
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


class HistoryStore(ABC):
    """시뮬레이션 이력 저장소 추상 기본 클래스."""

    @abstractmethod
    def save(self, result: dict[str, Any], tags: dict[str, str] | None = None) -> str:
        """결과를 저장하고 레코드 ID를 반환한다."""

    @abstractmethod
    def query(
        self,
        scenario: str | None = None,
        since_hours: int = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """최근 N시간 이내 결과를 조회한다."""

    @abstractmethod
    def cleanup_old_records(self) -> int:
        """RETENTION_DAYS 초과 레코드를 삭제하고 삭제 건수를 반환한다."""

    @abstractmethod
    def close(self) -> None:
        """연결을 닫는다."""

    @classmethod
    def create(cls, dsn: str | None = None, db_path: str | None = None) -> "HistoryStore":
        """dsn이 제공되면 TimescaleDB, 아니면 SQLite를 사용한다."""
        if dsn:
            try:
                return TimescaleHistoryStore(dsn)
            except Exception as exc:
                logger.warning("TimescaleDB 연결 실패, SQLite로 폴백: %s", exc)

        path = db_path or str(Path(__file__).parent.parent / "data" / "history.db")
        return SQLiteHistoryStore(path)


class SQLiteHistoryStore(HistoryStore):
    """SQLite 기반 이력 저장소 (개발/테스트 폴백)."""

    def __init__(self, db_path: str = ":memory:") -> None:
        """인스턴스를 초기화한다."""
        self._db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._setup_schema()

    def _setup_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sim_results (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  REAL    NOT NULL,
                scenario    TEXT,
                tags        TEXT,
                payload     TEXT    NOT NULL
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_created_at ON sim_results(created_at)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scenario ON sim_results(scenario)"
        )
        self._conn.commit()

    def save(self, result: dict[str, Any], tags: dict[str, str] | None = None) -> str:
        ts = time.time()
        scenario = (tags or {}).get("scenario") or result.get("scenario_id", "")
        cur = self._conn.execute(
            "INSERT INTO sim_results (created_at, scenario, tags, payload) VALUES (?,?,?,?)",
            (ts, scenario, json.dumps(tags or {}), json.dumps(result)),
        )
        self._conn.commit()
        return str(cur.lastrowid)

    def query(
        self,
        scenario: str | None = None,
        since_hours: int = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        cutoff = time.time() - since_hours * 3600
        if scenario:
            rows = self._conn.execute(
                "SELECT id, created_at, scenario, tags, payload "
                "FROM sim_results WHERE created_at >= ? AND scenario = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (cutoff, scenario, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, created_at, scenario, tags, payload "
                "FROM sim_results WHERE created_at >= ? "
                "ORDER BY created_at DESC LIMIT ?",
                (cutoff, limit),
            ).fetchall()

        return [
            {
                "id": r[0],
                "created_at": datetime.fromtimestamp(r[1], tz=timezone.utc).isoformat(),
                "scenario": r[2],
                "tags": json.loads(r[3]),
                "result": json.loads(r[4]),
            }
            for r in rows
        ]

    def cleanup_old_records(self) -> int:
        cutoff = time.time() - RETENTION_DAYS * 86400
        cur = self._conn.execute(
            "DELETE FROM sim_results WHERE created_at < ?", (cutoff,)
        )
        self._conn.commit()
        deleted = cur.rowcount
        if deleted:
            logger.info("이력 정리: %d건 삭제 (보존 기간 %d일 초과)", deleted, RETENTION_DAYS)
        return deleted

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SQLiteHistoryStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class TimescaleHistoryStore(HistoryStore):
    """PostgreSQL + TimescaleDB 기반 이력 저장소.

    요구사항:
        pip install psycopg2-binary
        TimescaleDB 확장 활성화: CREATE EXTENSION IF NOT EXISTS timescaledb;
    """

    def __init__(self, dsn: str) -> None:
        """인스턴스를 초기화한다."""
        try:
            import psycopg2
        except ImportError as exc:
            raise ImportError(
                "psycopg2 required: pip install psycopg2-binary"
            ) from exc

        self._conn = psycopg2.connect(dsn)
        self._setup_schema()

    def _setup_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sim_results (
                    id          BIGSERIAL,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    scenario    TEXT,
                    tags        JSONB,
                    payload     JSONB NOT NULL
                )
            """)
            # TimescaleDB hypertable (시계열 최적화)
            cur.execute("""
                SELECT create_hypertable(
                    'sim_results', 'created_at',
                    if_not_exists => TRUE
                )
            """)
            # 30일 보존 정책
            cur.execute("""
                SELECT add_retention_policy(
                    'sim_results',
                    INTERVAL '30 days',
                    if_not_exists => TRUE
                )
            """)
        self._conn.commit()

    def save(self, result: dict[str, Any], tags: dict[str, str] | None = None) -> str:
        import json as _json
        scenario = (tags or {}).get("scenario") or result.get("scenario_id", "")
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sim_results (scenario, tags, payload) VALUES (%s, %s, %s) RETURNING id",
                (scenario, _json.dumps(tags or {}), _json.dumps(result)),
            )
            row_id = cur.fetchone()[0]
        self._conn.commit()
        return str(row_id)

    def query(
        self,
        scenario: str | None = None,
        since_hours: int = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        import json as _json
        interval = f"{since_hours} hours"
        with self._conn.cursor() as cur:
            if scenario:
                cur.execute(
                    "SELECT id, created_at, scenario, tags, payload FROM sim_results "
                    "WHERE created_at >= NOW() - INTERVAL %s AND scenario = %s "
                    "ORDER BY created_at DESC LIMIT %s",
                    (interval, scenario, limit),
                )
            else:
                cur.execute(
                    "SELECT id, created_at, scenario, tags, payload FROM sim_results "
                    "WHERE created_at >= NOW() - INTERVAL %s "
                    "ORDER BY created_at DESC LIMIT %s",
                    (interval, limit),
                )
            rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "created_at": r[1].isoformat(),
                "scenario": r[2],
                "tags": _json.loads(r[3]) if isinstance(r[3], str) else r[3],
                "result": _json.loads(r[4]) if isinstance(r[4], str) else r[4],
            }
            for r in rows
        ]

    def cleanup_old_records(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sim_results WHERE created_at < NOW() - INTERVAL %s RETURNING id",
                (f"{RETENTION_DAYS} days",),
            )
            deleted = cur.rowcount
        self._conn.commit()
        if deleted:
            logger.info("이력 정리: %d건 삭제", deleted)
        return deleted

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "TimescaleHistoryStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
