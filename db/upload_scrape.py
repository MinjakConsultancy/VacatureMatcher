#!/usr/bin/env python3
"""Upload scrape-batches uit staging naar MinIO (bronze layer)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "db"))

from minio_client import upload_file, upload_json  # noqa: E402

DEFAULT_STAGING = Path(os.environ.get("SCRAPE_STAGING_DIR", "/tmp/vacature-scrape"))


def staging_last_path(staging_dir: Path) -> Path:
    return staging_dir / ".last-ververs.json"


def upload_filter_run(
    run_id: str,
    sinds: str,
    filter_set: str,
    summary_path: Path,
    out_dir: Path,
) -> list[str]:
    keys: list[str] = []
    list_key = f"scrapes/{run_id}/list-{filter_set}-{sinds}.json"
    upload_json(json.loads(summary_path.read_text(encoding="utf-8")), list_key)
    keys.append(list_key)

    pat = re.compile(rf"^details-batch-{re.escape(sinds)}-{re.escape(filter_set)}-\d+\.json$")
    for path in sorted(out_dir.iterdir()):
        if not pat.match(path.name):
            continue
        batch_no = path.name.split("-")[-1].replace(".json", "")
        key = f"scrapes/{run_id}/details-batch-{filter_set}-{batch_no}.json"
        upload_file(path, key)
        keys.append(key)
    return keys


def upload_from_staging(staging_dir: Path, run_id: str | None = None) -> str:
    last = staging_last_path(staging_dir)
    if not last.exists():
        raise FileNotFoundError(f"Ontbreekt: {last}")
    data = json.loads(last.read_text(encoding="utf-8"))
    run_id = run_id or data.get("run_id") or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    sinds = data.get("sinds", "5d")
    uploaded = 0
    for entry in data.get("summaries", []):
        if isinstance(entry, str):
            summary_path = Path(entry)
            fs = _guess_filter_set(summary_path)
            out_dir = summary_path.parent
        else:
            summary_path = Path(entry["path"])
            fs = entry.get("filter_set") or _guess_filter_set(summary_path)
            out_dir = Path(entry.get("out_dir") or summary_path.parent)
        keys = upload_filter_run(run_id, sinds, fs, summary_path, out_dir)
        uploaded += len(keys)
        print(f"MinIO {fs}: {len(keys)} objecten onder scrapes/{run_id}/")

    data["run_id"] = run_id
    last.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Upload klaar: run_id={run_id}, {uploaded} objecten")
    return run_id


def _guess_filter_set(summary_path: Path) -> str:
    p = str(summary_path)
    if "/wbo/" in p:
        return "wbo"
    if "/ikwerk/" in p:
        return "ikwerk"
    if "/all/" in p or "-all-" in summary_path.name:
        return "all"
    if "ict" in p:
        return "ict"
    return "breed"


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload scrape batches naar MinIO")
    parser.add_argument("--sinds", default=None, help="(legacy) wordt uit .last-ververs.json gelezen")
    parser.add_argument("--filter", default=None, choices=["breed", "ict", "both", "all", "ikwerk", "wbo"])
    parser.add_argument("--run-id", help="Scrape run-id (default: uit metadata)")
    parser.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING)
    args = parser.parse_args()

    try:
        upload_from_staging(args.staging_dir, args.run_id)
    except Exception as exc:
        print(f"Upload mislukt: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
