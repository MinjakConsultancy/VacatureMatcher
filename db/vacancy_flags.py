"""Persistent vacature-voorkeuren (niet relevant, etc.)."""

from __future__ import annotations

from db import connect


def get_dismissed_slugs() -> set[str]:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT vacancy_slug FROM vacancy_user_flags WHERE dismissed = TRUE"
            )
            return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()
    finally:
        conn.close()


def filter_dismissed_results(results: list[dict]) -> list[dict]:
    dismissed = get_dismissed_slugs()
    if not dismissed:
        return results
    return [r for r in results if r.get("slug") not in dismissed]
