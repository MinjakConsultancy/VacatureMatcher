# Reference: vacature-match

## Web-app (aanbevolen)

- CV upload: `/match`
- Score-uitleg: `/match/uitleg`
- CLI: `cd rag && ./run.sh rag_match.py --cv ../examples/cv-voorbeeld.txt`

## Matching

Keyword-weights: `config/keywords.example.yaml` → kopieer naar `config/keywords.yaml` of `KEYWORDS_CONFIG`.

RAG-ranking: `rag/match_service.py` — sorteert op `(rag_score, keyword_score)`.

## Modules (canonical)

| Module | Pad |
|--------|-----|
| Match | `rag/match_service.py` |
| Keywords | `rag/keyword_match.py` |
| RAG index | `rag/vacature_rag.py` |
| Beschikbaar | `rag/vacature_beschikbaar.py` |
| Sinds-filter | `rag/sinds_dates.py` |

## Data verversen

Zie [ikwerk-ververs-data](../ikwerk-ververs-data/SKILL.md).
