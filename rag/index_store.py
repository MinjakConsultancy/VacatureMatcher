"""Upload/download RAG TF-IDF index naar MinIO gold layer."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "db"))

from minio_client import _client, ensure_bucket, minio_config  # noqa: E402

INDEX_FILES = ("chunks.json", "meta.json", "vectorizer.joblib", "matrix.npz")
GOLD_PREFIX = "gold/rag-index"


def index_is_complete(index_dir: Path) -> bool:
    return all((index_dir / name).exists() for name in INDEX_FILES)


def upload_index(index_dir: Path, snapshot_id: str | None = None) -> str:
    index_dir = Path(index_dir)
    if not index_is_complete(index_dir):
        raise FileNotFoundError(f"Incomplete index in {index_dir}")

    bucket = ensure_bucket()
    client = _client()
    from datetime import datetime, timezone

    snap = snapshot_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for name in INDEX_FILES:
        for prefix in (f"{GOLD_PREFIX}/latest", f"{GOLD_PREFIX}/{snap}"):
            key = f"{prefix}/{name}"
            client.upload_file(str(index_dir / name), bucket, key)

    return f"s3://{bucket}/{GOLD_PREFIX}/latest/"


def download_index(target_dir: Path) -> bool:
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    bucket = ensure_bucket()
    client = _client()

    try:
        for name in INDEX_FILES:
            key = f"{GOLD_PREFIX}/latest/{name}"
            client.download_file(bucket, key, str(target_dir / name))
    except Exception:
        return False

    return index_is_complete(target_dir)
