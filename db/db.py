"""Database- en omgevingshulp voor vacature-ETL."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def database_url() -> str:
    load_dotenv()
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL niet gezet (zie .env.example)")
    return url


def connect():
    import psycopg

    return psycopg.connect(database_url())


def minio_config() -> dict[str, str]:
    load_dotenv()
    return {
        "endpoint": os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"),
        "access_key": os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        "secret_key": os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        "bucket": os.environ.get("MINIO_BUCKET", "ikwerk-vacatures"),
        "region": os.environ.get("MINIO_REGION", "us-east-1"),
    }
