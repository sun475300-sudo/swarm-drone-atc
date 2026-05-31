"""P714 — PostgreSQL + TimescaleDB 연결 풀 관리."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

try:
    import asyncpg  # type: ignore
    _ASYNCPG_AVAILABLE = True
except ImportError:
    _ASYNCPG_AVAILABLE = False

_pool: "asyncpg.Pool | None" = None

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://sdacs:sdacs@localhost:5432/sdacs",
)


async def init_pool(dsn: str = DATABASE_URL, min_size: int = 2, max_size: int = 10) -> None:
    global _pool
    if not _ASYNCPG_AVAILABLE:
        return
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def acquire() -> AsyncIterator["asyncpg.Connection"]:
    if _pool is None:
        raise RuntimeError("DB pool not initialized — call init_pool() first")
    async with _pool.acquire() as conn:
        yield conn


def get_pool() -> "asyncpg.Pool | None":
    return _pool
