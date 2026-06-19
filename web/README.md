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
SCRAPE_SOURCE=auto
IKWERK_EMAIL=...    # optioneel; zonder wachtwoord → WbO
IKWERK_PASSWORD=...
API_ADMIN_TOKEN=    # optioneel; leeg = beheer-endpoints open (lokaal dev)
```

Voor beheer-acties (ververs, CV-upload): zet `API_ADMIN_TOKEN` in `.env` op de API-container, of laat leeg voor lokaal dev (geen auth).

**Data verversen** (Beheer): parameter **sinds** + optioneel vinkje **RAG-index herbouwen na ververs** (standaard aan). Zonder `IKWERK_EMAIL`/`IKWERK_PASSWORD` scrapet de worker automatisch van Werkenbijdeoverheid (geen login). Met credentials: IkWerk via Playwright (xvfb + reCAPTCHA v3). Forceer bron via `SCRAPE_SOURCE=ikwerk|wbo|auto` in `.env`.

**CV-match** gebeurt op de Match-pagina (upload → ranking); dat is los van data verversen.

## Ontwikkeling frontend lokaal

```bash
cd web/frontend && npm install && npm run dev
# API op localhost:8001
```

## RAG-index

Persistent volume `rag_index` op `/data/rag-index` in api/worker. Backup naar MinIO `gold/rag-index/latest/`.

Wordt standaard **herbouwd na Data verversen** (vinkje op Beheer). Handmatig zonder scrape: `cd rag && ./run.sh build_index.py` of `POST /api/jobs/match`.

## LLM (motivatiebrief & match-uitleg)

LLM-taken draaien **async via de worker**. Output op MinIO onder `gold/llm/`. Maximaal **één LLM-call tegelijk**; extra jobs wachten in `api_jobs`.

Kies de backend met `LLM_PROVIDER` in `.env` (zelfde waarde voor Docker en lokale CLI). **Geen fallback:** bij `openai_compatible` wordt Ollama niet geprobeerd, en omgekeerd.

| Provider | Variabelen |
|----------|------------|
| `ollama` | `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, … |
| `openai_compatible` | `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_API_KEY`, … |

### Ollama (`LLM_PROVIDER=ollama`)

```bash
ollama serve
ollama pull llama3.2
```

In `.env`:

```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=600
OLLAMA_KEEP_ALIVE=10m
```

### OpenAI-compatible (`LLM_PROVIDER=openai_compatible`)

```
LLM_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
OPENAI_TIMEOUT=600
```

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
