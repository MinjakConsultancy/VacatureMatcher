---
name: ikwerk-ververs-data
description: >-
  Ververs vacaturedata (IkWerk of Werkenbijdeoverheid): lijst + detailteksten,
  ingest naar Postgres. Gebruik bij ververs data, fetch vacatures, sinds=gisteren,
  sinds=5d, nieuwe vacatures ophalen, of @ikwerk-ververs-data vóór een match.
---

# Vacaturedata verversen

Workflow om vacatures op te halen en in Postgres te zetten. Daarna pas `@ikwerk-vacature-match` voor rematch/motivaties.

## Bron

| `SCRAPE_SOURCE` | Gedrag |
|-----------------|--------|
| `auto` (default) | IkWerk als `IKWERK_EMAIL` + `IKWERK_PASSWORD` gezet, anders Werkenbijdeoverheid |
| `ikwerk` | Alleen IkWerk (login verplicht) |
| `wbo` | Alleen Werkenbijdeoverheid (sitemap + details, geen login) |

## Randvoorwaarden

- **Nooit solliciteren**: geen Reageer/Solliciteren, geen uploads.
- **Credentials** (optioneel): `{repo-root}/.env` met `IKWERK_EMAIL` en `IKWERK_PASSWORD` voor IkWerk.
- **Docker** (voor Postgres + MinIO): `docker compose up -d` in repo-root. Zie `DATABASE_URL` en `MINIO_*` in `.env.example`.
- **Playwright**: eenmalig `cd scraper && npm install playwright` (of via `run_ververs.sh`).
- **Docker-worker**: logt automatisch in met `IKWERK_*` uit `.env` via xvfb (geen handmatige login). Profiel: volume `ikwerk_profile`.
- Lokaal met `--headed`: alleen als automatisch inloggen faalt (zeldzaam).

## Skill aanroepen

Parameters in het chatbericht:

| Parameter | Voorbeelden | Betekenis |
|-----------|-------------|-----------|
| `sinds=` | `sinds=gisteren`, `sinds=5d`, `sinds=all` | Periode (IkWerk: publishedSince; WbO: sitemap lastmod) |

Voorbeelden:

- `@ikwerk-ververs-data ververs data sinds=5d`
- `Haal nieuwe vacatures op sinds=gisteren`
- `@ikwerk-ververs-data` (default: `sinds=5d`)

## Snelle workflow

```bash
cd .cursor/skills/ikwerk-ververs-data/scripts
./run_ververs.sh 5d
# of: ./run_ververs.sh gisteren
# of: ./run_ververs.sh 5d --no-txt   # alleen fetch + merge
```

Stappen die het script uitvoert:

1. Router kiest bron (IkWerk of WbO).
2. Vacaturelijst ophalen + detailpagina's (`#content` innerText).
3. `upload_scrape.py` → MinIO bronze (`scrapes/{run_id}/`).
4. `ingest_run.py` → PostgreSQL silver (vacancies, …).
5. Optioneel: `rag/build_index.py`.

Daarna (aparte skill):

```bash
cd rag && ./run.sh rag_match.py --cv ../examples/cv-voorbeeld.txt
```

## Output

Staging onder `SCRAPE_STAGING_DIR` (default `/tmp/vacature-scrape/{run_id}/`), daarna MinIO + Postgres. Geen lokale `ikwerk-vacatures*` mappen meer in de standaard pipeline.

## Gerelateerde skills

- Match/rematch/motivaties: [ikwerk-vacature-match](../ikwerk-vacature-match/SKILL.md)
- API/filters: [reference.md](reference.md)
