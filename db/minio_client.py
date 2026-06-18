"""MinIO/S3-client voor bronze scrape-batches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.client import Config

from db import minio_config


def _client():
    cfg = minio_config()
    endpoint = cfg["endpoint"]
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        region_name=cfg["region"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket() -> str:
    cfg = minio_config()
    bucket = cfg["bucket"]
    client = _client()
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)
    return bucket


def upload_file(local_path: Path, key: str) -> str:
    bucket = ensure_bucket()
    _client().upload_file(str(local_path), bucket, key)
    return f"s3://{bucket}/{key}"


def upload_json(data: Any, key: str) -> str:
    bucket = ensure_bucket()
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    _client().put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
    return f"s3://{bucket}/{key}"


def upload_bytes(data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    bucket = ensure_bucket()
    _client().put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return f"s3://{bucket}/{key}"


def download_bytes(key: str) -> bytes:
    cfg = minio_config()
    obj = _client().get_object(Bucket=cfg["bucket"], Key=key)
    return obj["Body"].read()


def download_json(key: str) -> Any:
    cfg = minio_config()
    obj = _client().get_object(Bucket=cfg["bucket"], Key=key)
    return json.loads(obj["Body"].read().decode("utf-8"))


def list_keys(prefix: str) -> list[str]:
    cfg = minio_config()
    bucket = cfg["bucket"]
    client = _client()
    keys: list[str] = []
    token = None
    while True:
        kwargs: dict = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents") or []:
            keys.append(obj["Key"])
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if uri.startswith("s3://"):
        rest = uri[5:]
        bucket, _, key = rest.partition("/")
        return bucket, key
    parsed = urlparse(uri)
    path = parsed.path.lstrip("/")
    bucket = path.split("/", 1)[0] if "/" in path else minio_config()["bucket"]
    key = path.split("/", 1)[1] if "/" in path else path
    return bucket, key
