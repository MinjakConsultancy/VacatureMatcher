"""Minimale OpenAI-compatibele HTTP-client (geen extra dependencies).

Werkt met OpenAI-compatible HTTP APIs (bijv. OpenAI, lokale proxies).
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

DEFAULT_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "")
DEFAULT_TIMEOUT = float(os.environ.get("OPENAI_TIMEOUT", "600"))
DEFAULT_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()


def _url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    p = path if path.startswith("/") else f"/{path}"
    return f"{base}{p}"


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if DEFAULT_API_KEY:
        headers["Authorization"] = f"Bearer {DEFAULT_API_KEY}"
    return headers


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
        headers=_headers(),
    )
    effective_timeout = timeout or DEFAULT_TIMEOUT
    try:
        with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except TimeoutError as exc:
        raise RuntimeError(
            f"OpenAI-compatible endpoint reageerde niet binnen {effective_timeout:.0f}s "
            f"({method} {path}). Verhoog OPENAI_TIMEOUT of kies een sneller model."
        ) from exc


def is_available(base_url: str | None = None) -> bool:
    try:
        _request("GET", "/models", base_url=base_url, timeout=5)
        return True
    except Exception:
        return False


def list_models(base_url: str | None = None) -> list[str]:
    payload = _request("GET", "/models", base_url=base_url, timeout=10)
    data = payload.get("data") or payload.get("models") or []
    models: list[str] = []
    for m in data:
        if isinstance(m, dict):
            mid = m.get("id") or m.get("model") or m.get("name")
            if mid:
                models.append(str(mid))
        elif isinstance(m, str):
            models.append(m)
    return models


def resolve_model(base_url: str | None = None, model: str | None = None) -> str:
    if model:
        return model
    if DEFAULT_MODEL:
        return DEFAULT_MODEL
    models = list_models(base_url)
    if not models:
        raise RuntimeError("Geen OpenAI-compatibele modellen gevonden op OPENAI_BASE_URL.")
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
    body: dict[str, Any] = {
        "model": resolved,
        "messages": messages,
        "temperature": temperature,
    }
    last_err: Exception | None = None
    attempts = max(1, retries + 1)
    for attempt in range(attempts):
        try:
            payload = _request(
                "POST",
                "/chat/completions",
                base_url=base_url,
                body=body,
                timeout=timeout,
            )
            choices = payload.get("choices") or []
            if not choices:
                raise RuntimeError("Leeg antwoord (geen choices) van OpenAI-compatible endpoint")
            first = choices[0] if isinstance(choices, list) else None
            message = first.get("message") if isinstance(first, dict) else None
            content = (message or {}).get("content", "") if isinstance(message, dict) else ""
            content = (content or "").strip()
            if not content:
                # Some servers return `text` for completion-style responses.
                text = (first or {}).get("text", "") if isinstance(first, dict) else ""
                content = (text or "").strip()
            if not content:
                raise RuntimeError("Leeg antwoord van OpenAI-compatible endpoint")
            return content
        except RuntimeError as exc:
            last_err = exc
            if "niet binnen" not in str(exc) or attempt + 1 >= attempts:
                raise
    raise last_err  # pragma: no cover

