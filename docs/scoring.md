# RAG-score vs keyword-score

Zie ook de uitlegpagina in de web-app: `/match/uitleg`.

## Ranking

Resultaten worden gesorteerd op `(rag_score, keyword_score)` — RAG is primair, keywords zijn tiebreaker.

## RAG-score

1. CV wordt omgezet naar een query (`Profiel` + `Werkervaring`, max ~6000 tekens) via `rag/match_service.py::cv_text_to_query`.
2. Vacatures zitten in de TF-IDF-index als chunks (`rag/vacature_rag.py`).
3. Cosine similarity tussen query en elke chunk; per vacature-slug wordt de **max** score gehouden.
4. Typische waarden: 0,06–0,12 voor goede matches (schaal 0–1).

## Keyword-score

1. Vacaturetekst (titel, org, locatie, summary, detail) wordt doorzocht op configureerbare termen.
2. Positieve hits tellen op; 25% bonus als dezelfde term ook in het CV staat.
3. Negatieve termen verlagen de score.
4. Optionele bonussen via `config/keywords.yaml` (zie `config/keywords.example.yaml`).

## LLM-uitleg

De knop “Uitleg” op vacaturedetail of match-resultaten roept `rag/llm_service.py` aan. Dit is narratief en beïnvloedt scores niet.

## Configuratie

| Variabele | Betekenis |
|-----------|-----------|
| `KEYWORDS_CONFIG` | Pad naar YAML met positive/negative/bonuses |
| `CV_PATH` | Default CV voor CLI-tools (`examples/cv-voorbeeld.txt`) |
