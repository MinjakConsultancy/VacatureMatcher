from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path("/app")
ADMIN_TOKEN = os.environ.get("API_ADMIN_TOKEN", "")


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://vacature:vacature@postgres:5432/vacature",
    )


def rag_index_dir() -> Path:
    return Path(os.environ.get("RAG_INDEX_DIR", "/data/rag-index"))
