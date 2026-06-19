#!/usr/bin/env python3
"""Poll api_jobs en voer ververs/match/cv_match uit."""

from __future__ import annotations

import base64
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

REPO = Path("/app")
sys.path.insert(0, str(REPO / "db"))
sys.path.insert(0, str(REPO / "rag"))
sys.path.insert(0, str(REPO))

os.environ.setdefault("RAG_INDEX_DIR", "/data/rag-index")

from app.services.cv_parser import parse_cv_bytes  # noqa: E402
from app.services.cv_store import load_active_cv_text  # noqa: E402
from app.services.jobs import append_log, claim_next_job, finish_job, reset_running_jobs  # noqa: E402
from app.services.llm_store import save_llm_output  # noqa: E402
from index_store import download_index, index_is_complete, upload_index  # noqa: E402
from llm_service import explain_match, generate_motivatie  # noqa: E402
from match_service import rank_vacancies_for_cv  # noqa: E402
from vacature_rag import VacatureRAG, rebuild_index, ensure_deps_on_path  # noqa: E402

ensure_deps_on_path()

INDEX_DIR = Path(os.environ["RAG_INDEX_DIR"])
VERVERS_SH = REPO / ".cursor/skills/ikwerk-ververs-data/scripts/run_ververs.sh"


def bootstrap_index() -> None:
    if index_is_complete(INDEX_DIR):
        return
    if download_index(INDEX_DIR):
        return
    try:
        rebuild_index(INDEX_DIR)
    except RuntimeError as exc:
        if "Geen vacatures" in str(exc):
            print(f"Index overgeslagen: {exc}", flush=True)
            return
        raise
    try:
        upload_index(INDEX_DIR)
    except Exception:
        pass


def run_ververs(job_id: str, params: dict) -> dict:
    sinds = params.get("sinds", "5d")
    cmd = ["bash", str(VERVERS_SH), sinds, "--no-txt"]
    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ},
    )
    assert proc.stdout
    for line in proc.stdout:
        append_log(job_id, line)
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ververs exit {code}")

    chunks = 0
    if params.get("rebuild_index", True):
        append_log(job_id, "RAG-index herbouwen...\n")
        chunks = rebuild_index(INDEX_DIR)
        append_log(job_id, f"RAG-index: {chunks} chunks\n")
        upload_index(INDEX_DIR)
    return {"ok": True, "chunks": chunks}


def run_match(job_id: str, params: dict) -> dict:
    n = 0
    if params.get("rebuild_index", True):
        append_log(job_id, "RAG-index herbouwen...\n")
        n = rebuild_index(INDEX_DIR)
        append_log(job_id, f"RAG-index: {n} chunks\n")
        upload_index(INDEX_DIR)
    return {"chunks": n}


def run_cv_match(job_id: str, params: dict) -> dict:
    from minio_client import download_bytes  # noqa: WPS433

    if params.get("cv_key"):
        raw = download_bytes(params["cv_key"])
    elif params.get("content_b64"):
        raw = base64.b64decode(params["content_b64"])
    else:
        raise ValueError("Geen CV in job-params")
    text = parse_cv_bytes(raw, params.get("filename", "cv.txt"))
    bootstrap_index()
    rag = VacatureRAG(index_dir=INDEX_DIR)
    rag.load()
    results = rank_vacancies_for_cv(
        text,
        rag=rag,
        location=params.get("location"),
        open_only=params.get("open_only", True),
        top_n=int(params.get("top_n", 30)),
    )
    return {
        "results": [
            {
                "slug": r.slug,
                "title": r.title,
                "organisation": r.organisation,
                "location": r.location,
                "url": r.url,
                "rag_score": r.rag_score,
                "keyword_score": r.keyword_score,
                "section": r.section,
                "snippet": r.snippet,
                "solliciteer_deadline": r.solliciteer_deadline,
            }
            for r in results
        ]
    }


def run_llm_motivatie(job_id: str, params: dict) -> dict:
    slug = params.get("slug", "")
    if not slug:
        raise ValueError("slug ontbreekt in job-params")
    append_log(job_id, f"Motivatiebrief genereren voor {slug}...\n")
    cv_kern = params.get("cv_kern", "")
    if cv_kern:
        result = generate_motivatie(
            slug,
            cv_kern=cv_kern,
            cv_uploaded=False,
            index_dir=INDEX_DIR,
            require_cv=False,
        )
    else:
        text = load_active_cv_text()
        result = generate_motivatie(
            slug,
            cv_kern=text,
            cv_uploaded=True,
            index_dir=INDEX_DIR,
            require_cv=True,
        )
    meta = save_llm_output("motivatie", result["slug"], job_id, result["text"], result["model"])
    append_log(job_id, f"Opgeslagen: {meta['storage_key']}\n")
    return {
        "slug": result["slug"],
        "model": result["model"],
        "storage_key": meta["storage_key"],
        "text_preview": meta["text_preview"],
    }


def run_llm_explain(job_id: str, params: dict) -> dict:
    slug = params.get("slug", "")
    if not slug:
        raise ValueError("slug ontbreekt in job-params")
    append_log(job_id, f"Match-uitleg genereren voor {slug}...\n")
    cv_text = params.get("cv_text", "")
    if not cv_text:
        cv_text = load_active_cv_text()
    result = explain_match(slug, cv_text, index_dir=INDEX_DIR)
    meta = save_llm_output("explain", result["slug"], job_id, result["text"], result["model"])
    append_log(job_id, f"Opgeslagen: {meta['storage_key']}\n")
    return {
        "slug": result["slug"],
        "model": result["model"],
        "storage_key": meta["storage_key"],
        "text_preview": meta["text_preview"],
    }


def handle_job(job: dict) -> None:
    job_id = job["id"]
    jtype = job["job_type"]
    params = job.get("params") or {}
    if isinstance(params, str):
        import json

        params = json.loads(params)
    try:
        if jtype == "ververs":
            result = run_ververs(job_id, params)
            finish_job(job_id, status="done", result=result)
        elif jtype == "match":
            result = run_match(job_id, params)
            finish_job(job_id, status="done", result=result)
        elif jtype == "cv_match":
            result = run_cv_match(job_id, params)
            finish_job(job_id, status="done", result=result)
        elif jtype == "llm_motivatie":
            result = run_llm_motivatie(job_id, params)
            finish_job(job_id, status="done", result=result)
        elif jtype == "llm_explain":
            result = run_llm_explain(job_id, params)
            finish_job(job_id, status="done", result=result)
        else:
            finish_job(job_id, status="failed", result={"error": f"onbekend type {jtype}"})
    except Exception as exc:
        append_log(job_id, traceback.format_exc())
        finish_job(job_id, status="failed", result={"error": str(exc)})


def main() -> None:
    n = reset_running_jobs()
    if n:
        print(f"Worker start: {n} running job(s) afgebroken", flush=True)
    bootstrap_index()
    while True:
        job = claim_next_job()
        if job:
            handle_job(job)
        else:
            time.sleep(2)


if __name__ == "__main__":
    main()
