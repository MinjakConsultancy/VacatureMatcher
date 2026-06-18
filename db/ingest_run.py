#!/usr/bin/env python3
"""Ingest scrape-run (staging of MinIO) naar PostgreSQL silver layer."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "db"))

from db import connect  # noqa: E402
from minio_client import download_json, upload_json  # noqa: E402
from parse_vacancy import parse_vacancy  # noqa: E402
from upsert import upsert_vacancy  # noqa: E402

DEFAULT_STAGING = Path(os.environ.get("SCRAPE_STAGING_DIR", "/tmp/vacature-scrape"))


def staging_last_path(staging_dir: Path) -> Path:
    return staging_dir / ".last-ververs.json"


def _load_details(out_dir: Path, sinds: str, prefix: str) -> dict[str, str]:
    details: dict[str, str] = {}
    if not out_dir.exists():
        return details
    pat = re.compile(rf"^details-batch-{re.escape(sinds)}-{re.escape(prefix)}-\d+\.json$")
    for path in sorted(out_dir.iterdir()):
        if not pat.match(path.name):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        val = payload.get("result", {}).get("value") or payload.get("value") or payload
        if isinstance(val, dict):
            details.update(val)
    return details


def merge_run_from_staging(
    sinds: str,
    filter_set: str,
    summary_path: Path,
    out_dir: Path,
    run_id: str,
) -> tuple[list[dict[str, Any]], str]:
    list_rows = json.loads(summary_path.read_text(encoding="utf-8"))
    details = _load_details(out_dir, sinds, filter_set)
    merged: list[dict[str, Any]] = []
    for row in list_rows:
        item = dict(row)
        url = item.get("url", "")
        if url in details:
            item["detail_text"] = details[url]
            item["detail_minio_key"] = (
                f"scrapes/{run_id}/details/{filter_set}/{item.get('slug', '')}.txt"
            )
        merged.append(item)
    minio_key = f"scrapes/{run_id}/list-{filter_set}-{sinds}.json"
    return merged, minio_key


def _filter_sets_from_meta(meta: dict[str, Any]) -> list[str]:
    sets = meta.get("filter_sets")
    if isinstance(sets, list) and sets:
        return [str(s) for s in sets]
    fs = meta.get("filter_set")
    if fs:
        return [str(fs)]
    # legacy meta
    filter_arg = meta.get("filter", "both")
    if filter_arg == "both":
        return ["breed", "ict"]
    if filter_arg == "all":
        return ["all"]
    return [filter_arg]


def ingest_staging(
    staging_dir: Path,
    *,
    sinds: str | None = None,
    run_id: str | None = None,
) -> str:
    last = staging_last_path(staging_dir)
    if not last.exists():
        raise FileNotFoundError(f"Ontbreekt: {last}")
    meta = json.loads(last.read_text(encoding="utf-8"))
    run_id = run_id or meta.get("run_id") or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    sinds = sinds or meta.get("sinds", "5d")
    allowed = set(_filter_sets_from_meta(meta))
    summaries = meta.get("summaries", [])
    if not summaries:
        raise ValueError("Geen summaries in .last-ververs.json")
    conn = connect()
    total = 0
    try:
        with conn:
            for entry in summaries:
                if isinstance(entry, str):
                    summary_path = Path(entry)
                    fs = "all" if "/all/" in str(summary_path) else ("ict" if "ict" in str(summary_path) else "breed")
                    out_dir = summary_path.parent
                else:
                    summary_path = Path(entry["path"])
                    fs = entry.get("filter_set") or meta.get("filter_set") or "ikwerk"
                    out_dir = Path(entry.get("out_dir") or summary_path.parent)
                if fs not in allowed:
                    continue
                rows, minio_key = merge_run_from_staging(sinds, fs, summary_path, out_dir, run_id)
                try:
                    upload_json(json.loads(summary_path.read_text(encoding="utf-8")), minio_key)
                except Exception as exc:
                    print(f"MinIO upload overgeslagen ({exc})", file=sys.stderr)

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO scrape_runs (id, filter_set, sinds, minio_list_key, vacancy_count, status)
                        VALUES (%s, %s, %s, %s, %s, 'running')
                        ON CONFLICT (id, filter_set) DO NOTHING
                        """,
                        (run_id, fs, sinds, minio_key, len(rows)),
                    )

                for row in rows:
                    parsed = parse_vacancy(row)
                    detail_key = row.get("detail_minio_key")
                    upsert_vacancy(conn, parsed, filter_set=fs, detail_minio_key=detail_key)
                    total += 1

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE scrape_runs
                        SET finished_at = NOW(), status = 'done', vacancy_count = %s
                        WHERE id = %s AND filter_set = %s
                        """,
                        (len(rows), run_id, fs),
                    )
        print(f"Ingest klaar: run={run_id}, {total} vacatures")
    finally:
        conn.close()
    return run_id


def ingest_from_minio(run_id: str, sinds: str, filter_sets: list[str]) -> str:
    conn = connect()
    total = 0
    try:
        with conn:
            for fs in filter_sets:
                list_key = f"scrapes/{run_id}/list-{fs}-{sinds}.json"
                list_rows = download_json(list_key)
                details: dict[str, str] = {}
                prefix = f"scrapes/{run_id}/details-batch-{fs}-"
                from minio_client import list_keys  # noqa: WPS433

                for key in list_keys(prefix):
                    payload = download_json(key)
                    val = payload.get("result", {}).get("value") or payload.get("value") or payload
                    if isinstance(val, dict):
                        details.update(val)

                merged: list[dict[str, Any]] = []
                for row in list_rows:
                    item = dict(row)
                    url = item.get("url", "")
                    if url in details:
                        item["detail_text"] = details[url]
                    merged.append(item)

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO scrape_runs (id, filter_set, sinds, minio_list_key, vacancy_count, status)
                        VALUES (%s, %s, %s, %s, %s, 'running')
                        ON CONFLICT (id, filter_set) DO NOTHING
                        """,
                        (run_id, fs, sinds, list_key, len(merged)),
                    )

                for row in merged:
                    parsed = parse_vacancy(row)
                    upsert_vacancy(conn, parsed, filter_set=fs)
                    total += 1

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE scrape_runs
                        SET finished_at = NOW(), status = 'done', vacancy_count = %s
                        WHERE id = %s AND filter_set = %s
                        """,
                        (len(merged), run_id, fs),
                    )
        print(f"Ingest van MinIO klaar: run={run_id}, {total} vacatures")
    finally:
        conn.close()
    return run_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest scrape → Postgres")
    parser.add_argument("--sinds", default=None)
    parser.add_argument(
        "--filter",
        default=None,
        choices=["breed", "ict", "both", "all", "ikwerk", "wbo"],
        help="(legacy) filter op filter_set; default uit .last-ververs.json",
    )
    parser.add_argument("--run-id", help="Scrape run-id")
    parser.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--from-minio", action="store_true", help="Lees batches uit MinIO i.p.v. staging")
    args = parser.parse_args()

    try:
        if args.from_minio:
            if not args.run_id:
                raise ValueError("--from-minio vereist --run-id")
            sinds = args.sinds or "5d"
            if args.filter:
                sets = [args.filter] if args.filter not in ("both",) else ["breed", "ict"]
            else:
                last = staging_last_path(args.staging_dir)
                meta = json.loads(last.read_text(encoding="utf-8")) if last.exists() else {}
                sets = _filter_sets_from_meta(meta)
            ingest_from_minio(args.run_id, sinds, sets)
        else:
            ingest_staging(
                args.staging_dir,
                sinds=args.sinds,
                run_id=args.run_id,
            )
    except Exception as exc:
        print(f"Ingest mislukt: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
