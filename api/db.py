"""P714: SQLAlchemy 비동기 엔진 + 모델 정의.

환경변수:
    SDACS_DATABASE_URL  — 기본값: sqlite+aiosqlite:///./sdacs.db (개발용)
                          프로덕션: postgresql+asyncpg://user:pass@host/dbname

TimescaleDB:
    DroneSnapshot 테이블은 TimescaleDB hypertable 대상.
    `api/migrations/` Alembic 마이그레이션에서
    SELECT create_hypertable('drone_snapshot', 'recorded_at') 실행.
"""

from __future__ import annotations

import os
import time
from typing import Any

from sqlalchemy import JSON, BigInteger, Column, Float, Index, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_DATABASE_URL = os.environ.get(
    "SDACS_DATABASE_URL", "sqlite+aiosqlite:///./sdacs.db"
)

engine = create_async_engine(_DATABASE_URL, echo=False, future=True)
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    """SQLAlchemy 선언형 기반 클래스."""


class DroneSnapshot(Base):
    """드론 위치/상태 스냅샷 — TimescaleDB hypertable 대상 (time column: recorded_at).

    30일 보존 정책: TimescaleDB 파티션 + retention policy로 자동 삭제.
    """

    __tablename__ = "drone_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recorded_at: Mapped[int] = mapped_column(BigInteger, index=True, default=lambda: time.time_ns())
    drone_id: Mapped[str] = mapped_column(String(64), index=True)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    z: Mapped[float] = mapped_column(Float)
    vx: Mapped[float] = mapped_column(Float, default=0.0)
    vy: Mapped[float] = mapped_column(Float, default=0.0)
    vz: Mapped[float] = mapped_column(Float, default=0.0)
    heading: Mapped[float] = mapped_column(Float, default=0.0)
    battery_pct: Mapped[float] = mapped_column(Float, default=100.0)
    flight_phase: Mapped[str] = mapped_column(String(32), default="ENROUTE")

    __table_args__ = (
        Index("ix_drone_snapshot_drone_time", "drone_id", "recorded_at"),
    )


class RunRecord(Base):
    """시뮬레이션 실행 기록 — in-memory AppState.runs 영속화 대상."""

    __tablename__ = "run_record"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    started_at_ns: Mapped[int] = mapped_column(BigInteger)
    finished_at_ns: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AuditLog(Base):
    """감사 로그 — 사용자 행동 추적."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recorded_at: Mapped[int] = mapped_column(BigInteger, index=True, default=lambda: time.time_ns())
    username: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(128))
    detail: Mapped[str] = mapped_column(Text, default="")
    source_ip: Mapped[str] = mapped_column(String(64), default="")


async def init_db() -> None:
    """테이블 생성 (개발/테스트용). 프로덕션에서는 Alembic 마이그레이션 사용."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:  # type: ignore[return]
    """FastAPI Dependency — DB 세션 제공."""
    async with AsyncSessionLocal() as session:
        yield session  # type: ignore[misc]
