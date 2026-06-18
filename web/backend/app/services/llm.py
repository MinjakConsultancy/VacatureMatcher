from __future__ import annotations

import sys
from pathlib import Path

from app.models import JobOut, LlmJobOut, LlmLatestOut
from app.services.jobs import LLM_JOB_TYPES, create_job, get_job, list_llm_queue
from app.services.llm_store import load_latest_text, load_text

REPO = Path("/app")
for p in (REPO / "rag",):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from llm_service import status  # noqa: E402


def llm_status() -> dict:
    return status()


def enqueue_motivatie(slug: str, *, cv_kern: str = "") -> JobOut:
    params: dict = {"slug": slug}
    if cv_kern.strip():
        params["cv_kern"] = cv_kern
    return create_job("llm_motivatie", params)


def enqueue_explain(slug: str, *, cv_text: str = "") -> JobOut:
    params: dict = {"slug": slug}
    if cv_text.strip():
        params["cv_text"] = cv_text
    return create_job("llm_explain", params)


def get_latest(kind: str, slug: str) -> LlmLatestOut | None:
    data = load_latest_text(kind, slug)
    if not data:
        return None
    return LlmLatestOut(
        slug=data.get("slug", slug),
        model=data.get("model", ""),
        text=data.get("text", ""),
        job_id=data.get("job_id", ""),
        created_at=data.get("created_at"),
        storage_key=data.get("storage_key"),
    )


def job_to_llm_out(job: JobOut) -> LlmJobOut:
    slug = None
    if job.params:
        slug = job.params.get("slug")
    text = None
    model = None
    storage_key = None
    text_preview = None
    if job.result:
        slug = job.result.get("slug") or slug
        model = job.result.get("model")
        storage_key = job.result.get("storage_key")
        text_preview = job.result.get("text_preview")
        if job.status == "done" and storage_key:
            try:
                text = load_text(storage_key)
            except Exception:
                text = text_preview
        elif text_preview:
            text = text_preview
    return LlmJobOut(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        queue_position=job.queue_position,
        slug=slug,
        model=model,
        text=text,
        storage_key=storage_key,
        text_preview=text_preview,
        log_tail=job.log_tail,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


def get_llm_job(job_id: str) -> LlmJobOut | None:
    job = get_job(job_id)
    if not job:
        return None
    if job.job_type not in LLM_JOB_TYPES:
        return None
    return job_to_llm_out(job)


def list_queue() -> list[LlmJobOut]:
    return [job_to_llm_out(j) for j in list_llm_queue()]
