from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import ExplainMatchRequest, JobOut, LlmJobOut, LlmLatestOut, LlmStatusOut, MotivatieRequest
from app.services import llm
from app.services.cv_store import ActiveCvNotFoundError

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/status", response_model=LlmStatusOut)
def llm_status():
    return llm.llm_status()


@router.get("/queue", response_model=list[LlmJobOut])
def llm_queue():
    return llm.list_queue()


@router.get("/jobs/{job_id}", response_model=LlmJobOut)
def llm_job_detail(job_id: str):
    job = llm.get_llm_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="LLM-job niet gevonden")
    return job


@router.post("/vacancies/{slug}/motivatie", response_model=JobOut)
def start_motivatie(slug: str, body: MotivatieRequest | None = None):
    cv_kern = body.cv_kern if body else ""
    if not cv_kern.strip():
        try:
            from app.services.cv_store import get_active_cv_meta

            if not get_active_cv_meta():
                raise ActiveCvNotFoundError("Geen actief CV")
        except ActiveCvNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return llm.enqueue_motivatie(slug, cv_kern=cv_kern)


@router.get("/vacancies/{slug}/motivatie/latest", response_model=LlmLatestOut)
def motivatie_latest(slug: str):
    latest = llm.get_latest("motivatie", slug)
    if not latest:
        raise HTTPException(status_code=404, detail="Geen opgeslagen motivatiebrief")
    return latest


@router.post("/vacancies/{slug}/explain", response_model=JobOut)
def start_explain(slug: str, body: ExplainMatchRequest | None = None):
    cv_text = body.cv_text if body else ""
    if not cv_text.strip():
        try:
            from app.services.cv_store import get_active_cv_meta

            if not get_active_cv_meta():
                raise ActiveCvNotFoundError("Geen actief CV")
        except ActiveCvNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return llm.enqueue_explain(slug, cv_text=cv_text)


@router.get("/vacancies/{slug}/explain/latest", response_model=LlmLatestOut)
def explain_latest(slug: str):
    latest = llm.get_latest("explain", slug)
    if not latest:
        raise HTTPException(status_code=404, detail="Geen opgeslagen match-uitleg")
    return latest
