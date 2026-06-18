"""Laad referentie-motivatiebrief uit MinIO (voor llm_service in worker/rag)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def load_active_motivatie_stijl_text() -> str | None:
    repo = Path(os.environ.get("APP_ROOT", "/app"))
    for p in (repo, repo / "db"):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
    try:
        from minio_client import download_bytes, download_json  # noqa: WPS433

        meta = download_json("profile/motivatie-stijl/meta.json")
        if not isinstance(meta, dict):
            return None
        return download_bytes("profile/motivatie-stijl/parsed.txt").decode("utf-8", errors="replace")
    except Exception:
        return None
