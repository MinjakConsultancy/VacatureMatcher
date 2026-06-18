from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.models import (
    CvMatchResultOut,
    CvStatusOut,
    JobCreateMatch,
    JobCreateVervers,
    JobOut,
    MatchResultOut,
    MotivatieStijlStatusOut,
)
from app.services.auth import require_admin
from app.services.cv_store import save_active_cv
from app.services.jobs import create_job, get_job, get_latest_cv_match_job, list_jobs
from app.services.motivatie_stijl_store import (
    get_active_motivatie_stijl_meta,
    save_active_motivatie_stijl,
)
from app.services.vacancies import get_dismissed_slugs

router = APIRouter(prefix="/api", tags=["jobs"])


def _match_results_from_job(job, *, job_id: str | None = None) -> CvMatchResultOut:
    dismissed = get_dismissed_slugs()
    results = []
    if job.result and "results" in job.result:
        for r in job.result["results"]:
            if r.get("slug") in dismissed:
                continue
            results.append(MatchResultOut(**r))
    jid = job_id or job.id
    return CvMatchResultOut(job_id=jid, status=job.status, results=results)


@router.get("/health")
def health():
    try:
        from app.deps import get_conn

        conn = get_conn()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}


@router.get("/stats", response_model=dict)
def stats_redirect():
    from app.services.vacancies import get_stats

    return get_stats().model_dump()


@router.post("/jobs/ververs", response_model=JobOut, dependencies=[Depends(require_admin)])
def start_ververs(body: JobCreateVervers):
    return create_job("ververs", body.model_dump())


@router.post("/jobs/match", response_model=JobOut, dependencies=[Depends(require_admin)])
def start_match(body: JobCreateMatch):
    return create_job("match", body.model_dump())


@router.get("/jobs", response_model=list[JobOut], dependencies=[Depends(require_admin)])
def jobs_list():
    return list_jobs()


@router.get("/jobs/{job_id}", response_model=JobOut)
def job_detail(job_id: str):
    job = get_job(job_id)
    if not job:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Job niet gevonden")
    return job


@router.get("/cv", response_model=CvStatusOut)
def cv_status():
    from app.services.cv_store import get_active_cv_meta

    meta = get_active_cv_meta()
    if not meta:
        return CvStatusOut(has_cv=False)
    return CvStatusOut(
        has_cv=True,
        filename=meta.get("filename"),
        uploaded_at=meta.get("uploaded_at"),
    )


@router.post("/cv", response_model=CvStatusOut, dependencies=[Depends(require_admin)])
async def upload_cv(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail="Bestand te groot (max 5MB)")
    filename = file.filename or "cv.txt"
    try:
        meta = save_active_cv(data, filename)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CvStatusOut(
        has_cv=True,
        filename=meta.get("filename"),
        uploaded_at=meta.get("uploaded_at"),
    )


@router.post("/match/cv", response_model=JobOut, dependencies=[Depends(require_admin)])
async def match_cv(
    file: UploadFile = File(...),
    location: str | None = Form(default=None),
    open_only: bool = Form(default=True),
    top_n: int = Form(default=30),
):
    import uuid

    from minio_client import upload_bytes  # noqa: WPS433

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail="Bestand te groot (max 5MB)")
    filename = file.filename or "cv.txt"
    job_id = str(uuid.uuid4())
    cv_key = f"cv-uploads/{job_id}/{filename}"
    upload_bytes(data, cv_key)
    try:
        save_active_cv(data, filename)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = {
        "filename": filename,
        "cv_key": cv_key,
        "location": location,
        "open_only": open_only,
        "top_n": top_n,
    }
    return create_job("cv_match", payload, job_id=job_id)


@router.get("/match/cv/latest", response_model=CvMatchResultOut)
def match_cv_latest():
    from fastapi import HTTPException

    job = get_latest_cv_match_job()
    if not job:
        raise HTTPException(status_code=404, detail="Geen voltooide CV-match gevonden")
    return _match_results_from_job(job)


@router.get("/match/cv/{job_id}", response_model=CvMatchResultOut)
def match_cv_result(job_id: str):
    job = get_job(job_id)
    if not job:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Job niet gevonden")
    return _match_results_from_job(job, job_id=job_id)


@router.get("/motivatie-stijl", response_model=MotivatieStijlStatusOut)
def motivatie_stijl_status():
    meta = get_active_motivatie_stijl_meta()
    if not meta:
        return MotivatieStijlStatusOut(has_motivatie=False)
    return MotivatieStijlStatusOut(
        has_motivatie=True,
        filename=meta.get("filename"),
        uploaded_at=meta.get("uploaded_at"),
    )


@router.post("/motivatie-stijl", response_model=MotivatieStijlStatusOut, dependencies=[Depends(require_admin)])
async def upload_motivatie_stijl(file: UploadFile = File(...)):
    from fastapi import HTTPException

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Bestand te groot (max 5MB)")
    filename = file.filename or "motivatie.txt"
    try:
        meta = save_active_motivatie_stijl(data, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MotivatieStijlStatusOut(
        has_motivatie=True,
        filename=meta.get("filename"),
        uploaded_at=meta.get("uploaded_at"),
    )
