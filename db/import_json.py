#!/usr/bin/env python3
"""Importeer vacatures.json naar PostgreSQL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "db"))

from db import connect  # noqa: E402
from parse_vacancy import parse_vacancy  # noqa: E402
from upsert import upsert_vacancy  # noqa: E402

DEFAULT_JSON = REPO_ROOT / "examples" / "vacatures.sample.json"


def load_json(path: Path, filter_set: str) -> list[tuple[dict, str]]:
    if not path.exists():
        print(f"Bestand niet gevonden: {path}", file=sys.stderr)
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    seen: set[str] = set()
    merged: list[tuple[dict, str]] = []
    for row in rows:
        slug = row.get("slug")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        merged.append((row, filter_set))
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Import vacatures.json → Postgres")
    parser.add_argument(
        "json_path",
        nargs="?",
        type=Path,
        default=DEFAULT_JSON,
        help=f"Pad naar vacatures JSON (default: {DEFAULT_JSON.name})",
    )
    parser.add_argument(
        "--filter-set",
        choices=["breed", "ict", "all"],
        default="breed",
        help="Filter-set label in vacancy_filters",
    )
    parser.add_argument("--dry-run", action="store_true", help="Alleen parsen, geen DB-write")
    args = parser.parse_args()

    rows = load_json(args.json_path, args.filter_set)
    if not rows:
        return 1

    parsed = [parse_vacancy(row) for row, _ in rows]
    print(f"Geladen: {len(parsed)} vacatures uit {args.json_path}")

    if args.dry_run:
        for p in parsed[:3]:
            print(f"  {p.slug}: {p.organisation} | {p.location}")
        return 0

    conn = connect()
    try:
        with conn:
            for (row, filter_set), item in zip(rows, parsed):
                upsert_vacancy(conn, item, filter_set=filter_set)
        print(f"Geïmporteerd: {len(parsed)} vacatures")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
