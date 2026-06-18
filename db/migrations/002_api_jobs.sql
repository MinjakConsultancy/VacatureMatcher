CREATE TABLE IF NOT EXISTS api_jobs (
    id          UUID PRIMARY KEY,
    job_type    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued',
    params      JSONB,
    log_tail    TEXT,
    result      JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_jobs_created ON api_jobs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_jobs_status ON api_jobs (status);
