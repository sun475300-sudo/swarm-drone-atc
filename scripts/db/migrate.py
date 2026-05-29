"""P714: SDACS 데이터베이스 마이그레이션 러너.

사용법:
    python scripts/db/migrate.py [--dry-run] [--db-url postgresql://...]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path

_logger = logging.getLogger("sdacs.migrate")

MIGRATIONS_DIR = Path(__file__).parent
MIGRATION_TABLE = "_migrations"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_connection(db_url: str) -> Any:
    """psycopg2 연결. psycopg2 미설치 시 RuntimeError."""
    try:
        import psycopg2  # type: ignore[import]
        return psycopg2.connect(db_url)
    except ImportError as exc:
        raise RuntimeError("psycopg2-binary 필요: pip install psycopg2-binary") from exc


def _ensure_migrations_table(cur: Any) -> None:
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
            filename    TEXT PRIMARY KEY,
            applied_at  TIMESTAMPTZ DEFAULT NOW(),
            sha256      TEXT NOT NULL
        )
    """)


def _applied(cur: Any) -> set[str]:
    cur.execute(f"SELECT filename FROM {MIGRATION_TABLE}")
    return {row[0] for row in cur.fetchall()}


def migrate(db_url: str, dry_run: bool = False) -> list[str]:
    """적용되지 않은 마이그레이션 파일을 순서대로 실행.

    Returns: 이번에 적용된 파일 목록.
    """
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        _logger.info("마이그레이션 파일 없음.")
        return []

    conn = _get_connection(db_url)
    try:
        conn.autocommit = False
        cur = conn.cursor()
        _ensure_migrations_table(cur)
        applied = _applied(cur)

        pending = [f for f in sql_files if f.name not in applied]
        if not pending:
            _logger.info("모든 마이그레이션 적용 완료.")
            conn.rollback()
            return []

        applied_now: list[str] = []
        for sql_file in pending:
            sha = _sha256(sql_file)
            sql = sql_file.read_text(encoding="utf-8")
            _logger.info("[%s] %s", "DRY-RUN" if dry_run else "APPLY", sql_file.name)
            if not dry_run:
                cur.execute(sql)
                cur.execute(
                    f"INSERT INTO {MIGRATION_TABLE} (filename, sha256) VALUES (%s, %s)",
                    (sql_file.name, sha),
                )
                applied_now.append(sql_file.name)

        if not dry_run:
            conn.commit()
        else:
            conn.rollback()

        return applied_now
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="SDACS DB 마이그레이션")
    parser.add_argument("--db-url", default=os.environ.get("DB_URL"),
                        help="PostgreSQL 연결 URL (환경변수 DB_URL 대체 가능)")
    parser.add_argument("--dry-run", action="store_true", help="실행하지 않고 미리 보기")
    args = parser.parse_args()

    if not args.db_url:
        _logger.error("--db-url 또는 DB_URL 환경변수 필요")
        sys.exit(1)

    applied = migrate(args.db_url, dry_run=args.dry_run)
    if applied:
        print(f"적용된 마이그레이션 ({len(applied)}개):")
        for name in applied:
            print(f"  ✓ {name}")
    else:
        print("새 마이그레이션 없음.")


# Any type hint for psycopg2 connection (no stub)
from typing import Any  # noqa: E402

if __name__ == "__main__":
    main()
