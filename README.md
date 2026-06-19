# Vacature Explorer

Open-source tool om vacatures van [IkWerk voor Nederland](https://www.ikwerkvoornederland.nl) en/of [Werkenbijdeoverheid](https://www.werkenbijdeoverheid.nl/vacatures) te verzamelen, te doorzoeken en te matchen tegen je CV met **RAG** (TF-IDF) en **keyword-scoring**. Optioneel: motivatiebrieven en match-uitleg via een lokale of OpenAI-compatible LLM.

## Quick start

```bash
cp .env.example .env   # IKWERK_* optioneel; zonder credentials scrapet WbO automatisch
docker compose up -d --build
```

| Service | URL |
|---------|-----|
| Web UI | http://localhost:3001 |
| API docs | http://localhost:8001/docs |
| MinIO console | http://localhost:19001 |

## Architectuur (kort)

```
Scraper (IkWerk of WbO) → MinIO (raw) → Postgres → RAG-index → CV-match / LLM-jobs
```

**Scrape-bron** (`SCRAPE_SOURCE=auto|ikwerk|wbo`): met `IKWERK_EMAIL` + `IKWERK_PASSWORD` wordt IkWerk gebruikt; anders Werkenbijdeoverheid (sitemap, geen login). Overlappende vacatures worden op `slug` gededupliceerd in Postgres.

- **API** (`web/backend`): FastAPI, read-only RAG-index.
- **Worker** (`web/worker`): scrape, index rebuild, CV-match, LLM (async job queue).
- **Frontend** (`web/frontend`): React — vacatures, CV-match, beheer.

Zie [docs/architecture.md](docs/architecture.md) en [docs/scoring.md](docs/scoring.md).

## LLM (motivatiebrief & match-uitleg)

De worker genereert teksten via **één** LLM-backend. Kies expliciet met `LLM_PROVIDER` in `.env` — er is **geen fallback** tussen Ollama en OpenAI-compatible.

| `LLM_PROVIDER` | Gebruikt | Niet gebruikt |
|----------------|----------|---------------|
| `ollama` (default) | `OLLAMA_*` | `OPENAI_*` |
| `openai_compatible` | `OPENAI_*` | `OLLAMA_*` |

Docker Compose leest `LLM_PROVIDER` uit `.env` en geeft die door aan api/worker. Na wijziging: `docker compose up -d api worker`.

### Ollama op de Docker-host

Ollama draait op je **host** (niet in een container). Containers praten via `host.docker.internal`:

```bash
ollama serve
ollama pull llama3.2
```

In `.env`:

```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2
```

Gebruik **niet** `localhost` in `OLLAMA_BASE_URL` voor Docker — dat wijst naar de container zelf.

### OpenAI-compatible endpoint

Voor een externe `/v1`-API (OpenAI, ToCode, lokale proxy):

```
LLM_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://jouw-endpoint/v1
OPENAI_MODEL=jouw-model
OPENAI_API_KEY=...   # indien vereist
```

Zorg dat het endpoint **bereikbaar is vanuit de worker-container** (VPN/firewall).

Zie ook [web/README.md](web/README.md) voor API-endpoints en opslag op MinIO.

## CV-match scores

Twee scores per vacature op `/match`:

- **RAG** (primair): TF-IDF cosine similarity tussen CV en vacature-chunks.
- **Keywords** (tiebreaker): configureerbare termen — zie `/match/uitleg`.

## Ontwikkeling

```bash
# Python tests (Python 3.13+)
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r web/backend/requirements.txt -r db/requirements.txt -r rag/requirements.txt -r requirements-dev.txt
pytest

# Frontend
cd web/frontend && npm install && npm run dev
```

Voorbeelddata: `examples/vacatures.sample.json`, `examples/cv-voorbeeld.txt`.

```bash
python db/import_json.py examples/vacatures.sample.json
cd rag && ./run.sh build_index.py
```

## Security

- **`.env` blijft lokaal** en staat in `.gitignore` — commit nooit secrets.
- Zet `API_ADMIN_TOKEN` in productie; zonder token zijn beheer-endpoints open (alleen voor lokaal dev).
- Roteer `IKWERK_PASSWORD` als het ooit buiten `.env` is gedeeld.

## License

MIT — zie [LICENSE](LICENSE).
