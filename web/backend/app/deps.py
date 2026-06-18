from __future__ import annotations

import sys
from pathlib import Path

REPO = Path("/app")
for p in (REPO / "db", REPO / "rag"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from db import connect as _db_connect  # noqa: E402


def get_conn():
    return _db_connect()


def run_migrations() -> None:
    mig_dir = REPO / "db" / "migrations"
    for name in ("002_api_jobs.sql", "003_vacancy_user_flags.sql", "004_scrape_sources.sql"):
        mig = mig_dir / name
        if not mig.exists():
            continue
        sql = mig.read_text(encoding="utf-8")
        conn = get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
        finally:
            conn.close()
