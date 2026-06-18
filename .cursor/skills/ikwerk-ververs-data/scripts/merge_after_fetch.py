#!/usr/bin/env python3
"""Na ververs_data.mjs: upload staging → MinIO, ingest → Postgres."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DB = REPO / "db"
STAGING = Path(os.environ.get("SCRAPE_STAGING_DIR", "/tmp/vacature-scrape"))
LAST = STAGING / ".last-ververs.json"


def main() -> int:
    if not LAST.exists():
        print(f"Ontbreekt: {LAST}", file=sys.stderr)
        return 1
    py = sys.executable
    data = json.loads(LAST.read_text(encoding="utf-8"))
    sinds = data.get("sinds", "5d")
    run_id = data.get("run_id")

    upload = DB / "upload_scrape.py"
    if upload.exists():
        print("Upload scrape naar MinIO…")
        cmd = [py, str(upload), "--staging-dir", str(STAGING)]
        if run_id:
            cmd.extend(["--run-id", run_id])
        subprocess.run(cmd, cwd=REPO, check=False)

    ingest = DB / "ingest_run.py"
    if ingest.exists():
        print("Ingest naar Postgres…")
        cmd = [
            py,
            str(ingest),
            "--staging-dir",
            str(STAGING),
            "--sinds",
            sinds,
        ]
        if run_id:
            cmd.extend(["--run-id", run_id])
        subprocess.run(cmd, cwd=REPO, check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
