"""Minimale Ollama HTTP-client (geen extra dependencies)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "")
DEFAULT_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "600"))
DEFAULT_KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "10m")


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _request(
    method: str,
    path: str,
    *,
    base_url: str | None = None,
    body: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> Any:
    base = base_url or DEFAULT_BASE_URL
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        _url(base, path),
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    effective_timeout = timeout or DEFAULT_TIMEOUT
    try:
        with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except TimeoutError as exc:
        raise RuntimeError(
            f"Ollama reageerde niet binnen {effective_timeout:.0f}s "
            f"({method} {path}). Verhoog OLLAMA_TIMEOUT of kies een sneller model."
        ) from exc


def is_available(base_url: str | None = None) -> bool:
    try:
        _request("GET", "/api/tags", base_url=base_url, timeout=5)
        return True
    except Exception:
        return False


def list_models(base_url: str | None = None) -> list[str]:
    payload = _request("GET", "/api/tags", base_url=base_url, timeout=10)
    models = payload.get("models") or []
    return [m.get("name", "") for m in models if m.get("name")]


def resolve_model(base_url: str | None = None, model: str | None = None) -> str:
    if model:
        return model
    if DEFAULT_MODEL:
        return DEFAULT_MODEL
    models = list_models(base_url)
    if not models:
        raise RuntimeError("Geen Ollama-modellen gevonden. Draai: ollama pull llama3.2")
    return models[0]


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
    temperature: float = 0.4,
    retries: int = 1,
) -> str:
    resolved = resolve_model(base_url, model)
    body = {
        "model": resolved,
        "messages": messages,
        "stream": False,
        "keep_alive": DEFAULT_KEEP_ALIVE,
        "options": {"temperature": temperature},
    }
    last_err: Exception | None = None
    attempts = max(1, retries + 1)
    for attempt in range(attempts):
        try:
            payload = _request(
                "POST",
                "/api/chat",
                base_url=base_url,
                body=body,
                timeout=timeout,
            )
            message = payload.get("message") or {}
            content = message.get("content", "").strip()
            if not content:
                raise RuntimeError("Leeg antwoord van Ollama")
            return content
        except RuntimeError as exc:
            last_err = exc
            if "niet binnen" not in str(exc) or attempt + 1 >= attempts:
                raise
    raise last_err  # pragma: no cover
