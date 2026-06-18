-- Vacature silver layer (PostgreSQL)

CREATE TABLE IF NOT EXISTS filter_sets (
    id          TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    query_params TEXT NOT NULL
);

INSERT INTO filter_sets (id, label, query_params) VALUES
    ('breed', 'Breed Wo+Hbo schaal 12-14', 'werkdenkniveau=CWD.04,CWD.08&salarisniveau=12,13,14'),
    ('ict', 'Smal ICT schaal 12-13', 'salarisniveau=12,13&vakgebied=CVG.08&werkdenkniveau=CWD.04'),
    ('ikwerk', 'IkWerk (ingelogd)', 'publishedSince'),
    ('wbo', 'Werkenbijdeoverheid (sitemap)', 'lastmod')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS scrape_runs (
    id              TEXT NOT NULL,
    filter_set      TEXT REFERENCES filter_sets (id),
    sinds           TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    minio_list_key  TEXT,
    vacancy_count   INTEGER,
    status          TEXT NOT NULL DEFAULT 'running',
    PRIMARY KEY (id, filter_set)
);

CREATE TABLE IF NOT EXISTS vacancies (
    slug                    TEXT PRIMARY KEY,
    url                     TEXT NOT NULL,
    title                   TEXT NOT NULL,
    organisation            TEXT,
    location                TEXT,
    scale                   TEXT,
    hours                   TEXT,
    education               TEXT,
    kenmerk                 TEXT,
    plaatsingsdatum         DATE,
    solliciteer_deadline    DATE,
    status                  TEXT NOT NULL DEFAULT 'open',
    summary                 TEXT,
    detail_text             TEXT,
    detail_minio_key        TEXT,
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vacancies_deadline ON vacancies (solliciteer_deadline);
CREATE INDEX IF NOT EXISTS idx_vacancies_location ON vacancies (location);
CREATE INDEX IF NOT EXISTS idx_vacancies_organisation ON vacancies (organisation);

CREATE TABLE IF NOT EXISTS vacancy_vakgebieden (
    vacancy_slug    TEXT NOT NULL REFERENCES vacancies (slug) ON DELETE CASCADE,
    vakgebied       TEXT NOT NULL,
    sort_order      SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (vacancy_slug, vakgebied)
);

CREATE TABLE IF NOT EXISTS vacancy_contacts (
    id              SERIAL PRIMARY KEY,
    vacancy_slug    TEXT NOT NULL REFERENCES vacancies (slug) ON DELETE CASCADE,
    contact_type    TEXT NOT NULL,
    name            TEXT,
    email           TEXT,
    phone           TEXT,
    sort_order      SMALLINT NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_vacancy_contacts_slug ON vacancy_contacts (vacancy_slug);

CREATE TABLE IF NOT EXISTS vacancy_filters (
    vacancy_slug    TEXT NOT NULL REFERENCES vacancies (slug) ON DELETE CASCADE,
    filter_set      TEXT NOT NULL REFERENCES filter_sets (id),
    PRIMARY KEY (vacancy_slug, filter_set)
);

CREATE TABLE IF NOT EXISTS vacancy_sections (
    id              SERIAL PRIMARY KEY,
    vacancy_slug    TEXT NOT NULL REFERENCES vacancies (slug) ON DELETE CASCADE,
    section_type    TEXT NOT NULL,
    text            TEXT NOT NULL,
    sort_order      SMALLINT NOT NULL DEFAULT 0,
    UNIQUE (vacancy_slug, section_type, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_vacancy_sections_slug ON vacancy_sections (vacancy_slug);

CREATE TABLE IF NOT EXISTS vacancy_chunks (
    id              SERIAL PRIMARY KEY,
    vacancy_slug    TEXT NOT NULL REFERENCES vacancies (slug) ON DELETE CASCADE,
    section_id      INTEGER REFERENCES vacancy_sections (id) ON DELETE SET NULL,
    chunk_idx       SMALLINT NOT NULL DEFAULT 0,
    text            TEXT NOT NULL
);

CREATE OR REPLACE VIEW vacancies_open AS
SELECT v.*
FROM vacancies v
WHERE v.status = 'open'
  AND (v.solliciteer_deadline IS NULL OR CURRENT_DATE < v.solliciteer_deadline);
