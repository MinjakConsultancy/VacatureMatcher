#!/usr/bin/env python3
"""Exporteer Postgres-vacatures naar vacatures.json (debug/fallback)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "db"))

from db import connect  # noqa: E402


def export_vacancies(filter_set: str | None = None) -> list[dict]:
    conn = connect()
    try:
        with conn.cursor() as cur:
            if filter_set:
                cur.execute(
                    """
                    SELECT v.*
                    FROM vacancies v
                    JOIN vacancy_filters vf ON vf.vacancy_slug = v.slug
                    WHERE vf.filter_set = %s
                    ORDER BY v.title
                    """,
                    (filter_set,),
                )
            else:
                cur.execute("SELECT * FROM vacancies ORDER BY title")
            cols = [d.name for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]

            for row in rows:
                slug = row["slug"]
                cur.execute(
                    "SELECT vakgebied FROM vacancy_vakgebieden WHERE vacancy_slug = %s ORDER BY sort_order",
                    (slug,),
                )
                row["vakgebieden"] = [r[0] for r in cur.fetchall()]
                cur.execute(
                    """
                    SELECT contact_type, name, email, phone
                    FROM vacancy_contacts WHERE vacancy_slug = %s ORDER BY sort_order
                    """,
                    (slug,),
                )
                row["contacts"] = [
                    {"contact_type": r[0], "name": r[1], "email": r[2], "phone": r[3]}
                    for r in cur.fetchall()
                ]
                for date_col in ("plaatsingsdatum", "solliciteer_deadline"):
                    if row.get(date_col):
                        row[date_col] = row[date_col].isoformat()
                for ts_col in ("first_seen_at", "last_seen_at"):
                    if row.get(ts_col):
                        row[ts_col] = row[ts_col].isoformat()
                row.pop("detail_minio_key", None)
    finally:
        conn.close()

    out = []
    for row in rows:
        out.append(
            {
                "slug": row["slug"],
                "url": row["url"],
                "title": row["title"],
                "organisation": row.get("organisation") or "",
                "location": row.get("location") or "",
                "hours": row.get("hours") or "",
                "scale": row.get("scale") or "",
                "education": row.get("education") or "",
                "deadline": row.get("solliciteer_deadline") or "-",
                "summary": row.get("summary") or "",
                "detail_text": row.get("detail_text") or "",
                "vakgebieden": row.get("vakgebieden") or [],
                "contacts": row.get("contacts") or [],
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Postgres → vacatures.json")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "examples" / "vacatures.export.json",
    )
    parser.add_argument("--filter-set", choices=["breed", "ict", "all", "ikwerk", "wbo"])
    args = parser.parse_args()

    rows = export_vacancies(args.filter_set)
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Geëxporteerd: {len(rows)} → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
