# Reference: IkWerk data verversen

## Credentials

Bestand `{repo-root}/.env` (gitignored):

```
IKWERK_EMAIL=je.rijksmail@voorbeeld.nl
IKWERK_PASSWORD=...
```

Fallback: environment variables `IKWERK_EMAIL` / `IKWERK_PASSWORD`.

Het script leest nooit wachtwoorden uit skill-bestanden of git.

## Scripts

| Script | Doel |
|--------|------|
| `scripts/ververs_data.mjs` | Playwright: login, lijst, details |
| `scripts/run_ververs.sh` | Orchestratie: fetch → merge → MinIO → Postgres → RAG |
| `scripts/merge_after_fetch.py` | Merge + `db/upload_scrape.py` + `db/ingest_run.py` |
| `db/import_json.py` | Eenmalige import `vacatures.json` → Postgres |
| `db/export_json.py` | Postgres → `vacatures.json` (debug/fallback) |

Docker (repo-root): `docker compose up -d` — Postgres op poort **15432**, MinIO API **19000**, console **19001**. Zie `.env.example` voor `DATABASE_URL` en `MINIO_*`.

Playwright-profiel (sessie-cache): `scraper/.playwright-ikwerk-profile/`

## Filters

| Set | Query params |
|-----|----------------|
| Breed | `werkdenkniveau=CWD.04,CWD.08&salarisniveau=12,13,14` |
| Smal ICT | `salarisniveau=12,13&vakgebied=CVG.08&werkdenkniveau=CWD.04` |
| Sinds | `publishedSince=gisteren` / `3d` / `5d` / `7d` / `10d` / `1maand` |

## Lijst-API

```
https://www.ikwerkvoornederland.nl/werkaanbod/vacatures?_hn:type=component-rendering&_hn:ref=r82_r1_r4&pagina={N}&{filters}&publishedSince={sinds}
```

Browser-side logica: `scraper/fetch_list.js` en `scraper/fetch_details_fn.js`.

## Merge

Data gaat via staging → MinIO → Postgres (`merge_after_fetch.py`). Geen lokale `vacatures.json` meer in de standaard pipeline.

## sinds-waarden

| Chat / CLI | URL `publishedSince` |
|------------|----------------------|
| `gisteren`, `1d` | `gisteren` |
| `3d` | `3d` |
| `5d` | `5d` |
| `7d` | `7d` |
| `10d` | `10d` |
| `1maand`, `30d` | `1maand` |

## Foutafhandeling

| Symptoom | Actie |
|----------|-------|
| Redirect naar `/inloggen` | Controleer `IKWERK_EMAIL`/`IKWERK_PASSWORD` in `.env` |
| `not_logged_in` in lijst-fetch | Sessie verlopen; worker logt opnieuw in (xvfb) |
| Detail bevat "Rijksmailadres" | Login-pagina i.p.v. vacature; batch opnieuw |
| Playwright ontbreekt | `cd scraper && npx playwright install chromium --force` |
| `Executable doesn't exist` (chromium_headless_shell) | Zelfde commando; `run_ververs.sh` probeert dit nu automatisch |
