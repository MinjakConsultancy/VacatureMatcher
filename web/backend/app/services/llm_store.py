from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/app")
if str(REPO / "db") not in sys.path:
    sys.path.insert(0, str(REPO / "db"))

from minio_client import download_bytes, download_json, upload_bytes, upload_json  # noqa: E402

GOLD_PREFIX = "gold/llm"
TEXT_PREVIEW_LEN = 500


def _output_key(kind: str, slug: str, job_id: str) -> str:
    return f"{GOLD_PREFIX}/{kind}/{slug}/{job_id}.md"


def _latest_key(kind: str, slug: str) -> str:
    return f"{GOLD_PREFIX}/{kind}/{slug}/latest.json"


def save_llm_output(
    kind: str,
    slug: str,
    job_id: str,
    text: str,
    model: str,
) -> dict:
    storage_key = _output_key(kind, slug, job_id)
    upload_bytes(text.encode("utf-8"), storage_key, content_type="text/markdown; charset=utf-8")
    meta = {
        "job_id": job_id,
        "slug": slug,
        "kind": kind,
        "model": model,
        "storage_key": storage_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "text_preview": text[:TEXT_PREVIEW_LEN],
    }
    upload_json(meta, _latest_key(kind, slug))
    return meta


def load_latest_meta(kind: str, slug: str) -> dict | None:
    try:
        meta = download_json(_latest_key(kind, slug))
    except Exception:
        return None
    if not isinstance(meta, dict):
        return None
    return meta


def load_latest_text(kind: str, slug: str) -> dict | None:
    meta = load_latest_meta(kind, slug)
    if not meta:
        return None
    key = meta.get("storage_key")
    if not key:
        return None
    try:
        text = download_bytes(key).decode("utf-8", errors="replace")
    except Exception:
        return None
    return {**meta, "text": text}


def load_text(storage_key: str) -> str:
    return download_bytes(storage_key).decode("utf-8", errors="replace")
