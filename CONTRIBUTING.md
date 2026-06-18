# Contributing

Bedankt voor je interesse in Vacature Explorer.

## Setup

1. Fork en clone de repo.
2. `cp .env.example .env` — vul credentials alleen lokaal in.
3. `docker compose up -d --build` of zie [README.md](README.md) voor losse dev-stappen.

## Tests

Vereist **Python 3.13+** en **Node 22+** (lokaal of via CI).

```bash
pip install -r web/backend/requirements.txt -r db/requirements.txt -r rag/requirements.txt -r requirements-dev.txt
pytest

cd web/frontend && npm ci && npm test
```

CI draait op GitHub Actions (`.github/workflows/test.yml`).

## Richtlijnen

- Geen persoonlijke data, CV's of wachtwoorden in commits.
- Gebruik `examples/` voor fixtures en documentatie.
- Houd wijzigingen gefocust; volg bestaande code-stijl in `rag/`, `db/` en `web/`.

## Vragen

Open een issue voor bugs of feature-voorstellen.
