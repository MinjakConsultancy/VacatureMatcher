from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.services.cv_parser import parse_cv_bytes

REPO = Path("/app")
if str(REPO / "db") not in sys.path:
    sys.path.insert(0, str(REPO / "db"))

from minio_client import download_bytes, download_json, upload_bytes, upload_json  # noqa: E402

CV_PREFIX = "profile/cv"
META_KEY = f"{CV_PREFIX}/meta.json"
PARSED_KEY = f"{CV_PREFIX}/parsed.txt"


class ActiveCvNotFoundError(FileNotFoundError):
    """Geen actief CV op MinIO."""


def _source_key(filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".bin"
    return f"{CV_PREFIX}/source{ext}"


def _content_type(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if name.endswith(".txt"):
        return "text/plain; charset=utf-8"
    return "application/octet-stream"


def save_active_cv(data: bytes, filename: str) -> dict:
    filename = filename or "cv.txt"
    parsed = parse_cv_bytes(data, filename)
    source_key = _source_key(filename)
    upload_bytes(data, source_key, content_type=_content_type(filename))
    upload_bytes(parsed.encode("utf-8"), PARSED_KEY, content_type="text/plain; charset=utf-8")
    meta = {
        "filename": filename,
        "source_key": source_key,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "content_type": _content_type(filename),
    }
    upload_json(meta, META_KEY)
    return meta


def get_active_cv_meta() -> dict | None:
    try:
        meta = download_json(META_KEY)
    except Exception:
        return None
    if not isinstance(meta, dict):
        return None
    try:
        download_bytes(PARSED_KEY)
    except Exception:
        return None
    return meta


def load_active_cv_text() -> str:
    meta = get_active_cv_meta()
    if not meta:
        raise ActiveCvNotFoundError("Geen actief CV geüpload")
    return download_bytes(PARSED_KEY).decode("utf-8", errors="replace")
