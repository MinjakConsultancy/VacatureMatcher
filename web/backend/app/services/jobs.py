from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Json

from app.deps import get_conn
from app.models import JobOut

LLM_JOB_TYPES = ("llm_motivatie", "llm_explain")


def _row_to_job(row: tuple, cols: list[str], *, queue_position: int | None = None) -> JobOut:
    data = dict(zip(cols, row))
    return JobOut(
        id=str(data["id"]),
        job_type=data["job_type"],
        status=data["status"],
        params=data.get("params"),
        log_tail=data.get("log_tail"),
        result=data.get("result"),
        created_at=data["created_at"],
        finished_at=data.get("finished_at"),
        queue_position=queue_position,
    )


def _enrich_queue_position(job: JobOut) -> JobOut:
    if job.job_type not in LLM_JOB_TYPES or job.status != "queued":
        return job
    pos = llm_queue_position(job.id)
    return job.model_copy(update={"queue_position": pos})


def llm_job_running(conn=None) -> bool:
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM api_jobs
                WHERE status = 'running' AND job_type = ANY(%s)
                LIMIT 1
                """,
                (list(LLM_JOB_TYPES),),
            )
            return cur.fetchone() is not None
    finally:
        if own_conn:
            conn.close()


def llm_queue_position(job_id: str) -> int | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT job_type, status, created_at FROM api_jobs WHERE id = %s
                """,
                (job_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            job_type, status, created_at = row
            if job_type not in LLM_JOB_TYPES or status != "queued":
                return None
            cur.execute(
                """
                SELECT COUNT(*) FROM api_jobs
                WHERE status = 'queued'
                  AND job_type = ANY(%s)
                  AND created_at < %s
                """,
                (list(LLM_JOB_TYPES), created_at),
            )
            ahead = cur.fetchone()[0]
            return int(ahead) + 1
    finally:
        conn.close()


def list_llm_queue(limit: int = 20) -> list[JobOut]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, job_type, status, params, log_tail, result, created_at, finished_at
                FROM api_jobs
                WHERE job_type = ANY(%s) AND status IN ('queued', 'running')
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (list(LLM_JOB_TYPES), limit),
            )
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()
    jobs = [_row_to_job(r, cols) for r in rows]
    return [_enrich_queue_position(j) for j in jobs]


def create_job(job_type: str, params: dict[str, Any] | None = None, *, job_id: str | None = None) -> JobOut:
    job_id = job_id or str(uuid.uuid4())
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO api_jobs (id, job_type, status, params)
                    VALUES (%s, %s, 'queued', %s)
                    RETURNING id, job_type, status, params, log_tail, result, created_at, finished_at
                    """,
                    (job_id, job_type, Json(params or {})),
                )
                row = cur.fetchone()
                cols = [d.name for d in cur.description]
    finally:
        conn.close()
    return _enrich_queue_position(_row_to_job(row, cols))


def get_job(job_id: str) -> JobOut | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, job_type, status, params, log_tail, result, created_at, finished_at
                FROM api_jobs WHERE id = %s
                """,
                (job_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
    finally:
        conn.close()
    return _enrich_queue_position(_row_to_job(row, cols))


def list_jobs(limit: int = 20) -> list[JobOut]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, job_type, status, params, log_tail, result, created_at, finished_at
                FROM api_jobs ORDER BY created_at DESC LIMIT %s
                """,
                (limit,),
            )
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()
    return [_enrich_queue_position(_row_to_job(r, cols)) for r in rows]


def get_latest_cv_match_job() -> JobOut | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, job_type, status, params, log_tail, result, created_at, finished_at
                FROM api_jobs
                WHERE job_type = 'cv_match' AND status = 'done'
                ORDER BY finished_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
    finally:
        conn.close()
    return _row_to_job(row, cols)


def claim_next_job() -> dict[str, Any] | None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM api_jobs
                    WHERE status = 'running' AND job_type = ANY(%s)
                    LIMIT 1
                    """,
                    (list(LLM_JOB_TYPES),),
                )
                llm_busy = cur.fetchone() is not None

                if llm_busy:
                    cur.execute(
                        """
                        SELECT id, job_type, params FROM api_jobs
                        WHERE status = 'queued' AND job_type != ALL(%s)
                        ORDER BY created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """,
                        (list(LLM_JOB_TYPES),),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, job_type, params FROM api_jobs
                        WHERE status = 'queued'
                        ORDER BY created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """
                    )
                row = cur.fetchone()
                if not row:
                    return None
                job_id, job_type, params = row
                cur.execute(
                    "UPDATE api_jobs SET status = 'running' WHERE id = %s",
                    (job_id,),
                )
    finally:
        conn.close()
    return {"id": str(job_id), "job_type": job_type, "params": params or {}}


def reset_running_jobs(*, reason: str = "Worker herstart — job afgebroken") -> int:
    """Markeer alle running jobs als failed (bij worker-opstart)."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE api_jobs
                    SET status = 'failed',
                        result = %s,
                        finished_at = %s,
                        log_tail = COALESCE(log_tail, '') || %s
                    WHERE status = 'running'
                    RETURNING id
                    """,
                    (
                        Json({"error": reason}),
                        datetime.now(timezone.utc),
                        f"\n{reason}\n",
                    ),
                )
                return len(cur.fetchall())
    finally:
        conn.close()


def append_log(job_id: str, text: str) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE api_jobs SET log_tail = COALESCE(log_tail, '') || %s WHERE id = %s
                    """,
                    (text, job_id),
                )
    finally:
        conn.close()


def finish_job(job_id: str, *, status: str, result: dict | None = None) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE api_jobs
                    SET status = %s, result = %s, finished_at = %s
                    WHERE id = %s
                    """,
                    (status, Json(result) if result else None, datetime.now(timezone.utc), job_id),
                )
    finally:
        conn.close()
