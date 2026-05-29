"""TimescaleDB 마이그레이션 러너 (P714).

Usage:
    DB_URL=postgresql://sdacs:pass@localhost:5432/sdacs python scripts/db/migrate.py
    python scripts/db/migrate.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

MIGRATIONS = [
    "001_init_schema.sql",
    "002_retention_policy.sql",
]

SCRIPTS_DIR = Path(__file__).parent


def run(dry_run: bool = False) -> None:
    db_url = os.environ.get("DB_URL")
    if not db_url:
        sys.exit("DB_URL 환경 변수가 설정되지 않았습니다.")

    try:
        import psycopg2  # type: ignore[import]
    except ImportError:
        sys.exit("psycopg2 필요: pip install psycopg2-binary")

    conn = psycopg2.connect(db_url)
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                name        TEXT PRIMARY KEY,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        for fname in MIGRATIONS:
            cur.execute("SELECT 1 FROM _migrations WHERE name = %s", (fname,))
            if cur.fetchone():
                print(f"  skip  {fname} (already applied)")
                continue

            sql = (SCRIPTS_DIR / fname).read_text()
            if dry_run:
                print(f"  dry   {fname}")
                continue

            print(f"  apply {fname} ...", end="", flush=True)
            cur.execute(sql)
            cur.execute("INSERT INTO _migrations (name) VALUES (%s)", (fname,))
            print(" done")

    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
