---
name: ikwerk-vacature-match
description: >-
  Matcht IkWerk-vacatures tegen een CV, genereert motivatiebrieven via RAG/LLM.
  Gebruik bij vacature-match, motivatiebrief, CV rematch, of werken in de vacature-repo.
---

# IkWerk vacature-match

## Randvoorwaarden

- **Nooit solliciteren**: geen Reageer/Solliciteren op IkWerk.
- **CV**: upload via web `/match` of `CV_PATH` / `examples/cv-voorbeeld.txt` voor CLI.
- **Credentials**: `.env` (`IKWERK_EMAIL`, `IKWERK_PASSWORD`) — gitignored.

## Web-app (aanbevolen)

```bash
docker compose up -d --build
```

- Vacatures: http://localhost:3001
- CV-match + scores: `/match` — uitleg: `/match/uitleg`
- Beheer (ververs, index): `/beheer`

## CLI match

```bash
cd rag && ./run.sh rag_match.py --cv ../examples/cv-voorbeeld.txt
```

## Data verversen

Zie [@ikwerk-ververs-data](../ikwerk-ververs-data/SKILL.md).

## Projectstructuur

| Pad | Inhoud |
|-----|--------|
| `web/` | React UI + FastAPI + worker |
| `rag/` | TF-IDF index, match, LLM |
| `db/` | Postgres schema, ingest |
| `scraper/` | Playwright scripts |
| `examples/` | Voorbeeld-CV, vacatures, keywords |
