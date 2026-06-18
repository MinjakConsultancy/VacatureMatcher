-- User flags + filter_set 'all' voor volledige scrape

INSERT INTO filter_sets (id, label, query_params) VALUES
    ('all', 'Alle vacatures (geen filters)', '')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS vacancy_user_flags (
    vacancy_slug TEXT PRIMARY KEY REFERENCES vacancies (slug) ON DELETE CASCADE,
    dismissed    BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_vacancy_user_flags_dismissed
    ON vacancy_user_flags (dismissed) WHERE dismissed = TRUE;
