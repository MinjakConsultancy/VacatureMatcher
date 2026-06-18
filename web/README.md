# Vacature Web App

Zie ook de [root README](../README.md) en [docs/scoring.md](../docs/scoring.md).

Interactieve vacature-browser op Postgres + RAG.

## Start

```bash
docker compose up -d --build
```

- **UI**: http://localhost:3001
- **API**: http://localhost:8001/docs
- **MinIO**: http://localhost:19001

Zet in `.env` (optioneel):

```
API_ADMIN_TOKEN=een-geheim-token
SCRAPE_SOURCE=auto
IKWERK_EMAIL=...    # optioneel; zonder wachtwoord → WbO
IKWERK_PASSWORD=...
```

Voor beheer-acties (ververs, match, CV-upload): token invullen op `/beheer` of leeg laten als `API_ADMIN_TOKEN` niet gezet is.

**Data verversen** (Beheer → Data verversen): alleen parameter **sinds**. Zonder `IKWERK_EMAIL`/`IKWERK_PASSWORD` scrapet de worker automatisch van Werkenbijdeoverheid (geen login). Met credentials: IkWerk via Playwright (xvfb + reCAPTCHA v3). Forceer bron via `SCRAPE_SOURCE=ikwerk|wbo|auto` in `.env`.

## Ontwikkeling frontend lokaal

```bash
cd web/frontend && npm install && npm run dev
# API op localhost:8001
```

## RAG-index

Persistent volume `rag_index` op `/data/rag-index` in api/worker. Backup naar MinIO `gold/rag-index/latest/`.

## Ollama (lokale LLM)

LLM-taken draaien **async via de worker** (niet meer sync in de API). Output wordt opgeslagen op MinIO onder `gold/llm/`. Maximaal **één Ollama-call tegelijk**; extra jobs wachten in `api_jobs` met wachtrijpositie.

### Setup

```bash
ollama serve
ollama pull llama3.2
```

In `.env`:

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=600
OLLAMA_KEEP_ALIVE=10m
```

De **worker** (niet de API) praat met Ollama via `host.docker.internal:11434`.

### Gebruik

| Waar | Wat |
|------|-----|
| **UI detail** | Tab *Motivatie (LLM)* → genereer brief of match-uitleg (poll + wachtrijpositie) |
| **UI match** | Per resultaatrij knop *Uitleg* |
| **API** | `POST /api/llm/vacancies/{slug}/motivatie` → `JobOut` |
| | `GET /api/llm/jobs/{id}` → status, `queue_position`, tekst als klaar |
| | `GET /api/llm/vacancies/{slug}/motivatie/latest` → laatste opgeslagen brief |
| | `GET /api/llm/queue` → wachtende LLM-jobs |
| **CLI** | `cd rag && python3 ollama_motivatie.py <slug> -o brief.md` (sync, geen opslag) |

### Opslag (MinIO gold)

```
gold/llm/motivatie/{slug}/{job_id}.md
gold/llm/motivatie/{slug}/latest.json
gold/llm/explain/{slug}/{job_id}.md
gold/llm/explain/{slug}/latest.json
```

### CV voor motivatie

Upload CV op `/match` (`POST /api/cv` of via match-upload). Actief profiel: `profile/cv/` op MinIO.

### Architectuur

```
UI → POST enqueue → api_jobs (queue)
worker → Ollama (max 1 tegelijk) → MinIO gold/llm/
UI → poll GET /api/llm/jobs/{id}
```
