"""Gedeelde match-logica voor CLI en web API."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from sklearn.metrics.pairwise import cosine_similarity

from keyword_match import score_vacancy
from vacature_beschikbaar import is_beschikbaar
from vacature_rag import VacatureRAG, load_all_vacancies, ensure_deps_on_path
from vacancy_flags import get_dismissed_slugs

ensure_deps_on_path()


@dataclass
class MatchResult:
    slug: str
    title: str
    organisation: str
    location: str
    url: str
    rag_score: float
    keyword_score: float
    section: str
    snippet: str
    solliciteer_deadline: str | None


def cv_text_to_query(text: str) -> str:
    raw = text.strip()
    if not raw:
        return ""
    parts: list[str] = []
    profiel = re.search(r"Profiel:\s*(.+?)(?=\n\s*Opleidingen:)", raw, re.DOTALL | re.IGNORECASE)
    if profiel:
        parts.append(profiel.group(1).strip())
    ervaring = re.search(r"Werkervaring:\s*(.+)", raw, re.DOTALL | re.IGNORECASE)
    if ervaring:
        parts.append(ervaring.group(1).strip()[:6000])
    if not parts:
        return raw[:8000]
    return "\n\n".join(parts)


def _keyword_scores(vacancies: list[dict], cv_lower: str) -> dict[str, float]:
    return {v["slug"]: score_vacancy(v, cv_lower)[0] for v in vacancies if v.get("slug")}


def _rag_scores(rag: VacatureRAG, cv_query: str) -> dict[str, tuple[float, str, str]]:
    if rag.vectorizer is None or rag.matrix is None:
        raise RuntimeError("RAG-index niet geladen")
    q_vec = rag.vectorizer.transform([cv_query])
    sims = cosine_similarity(q_vec, rag.matrix).ravel()
    best: dict[str, tuple[float, str, str]] = {}
    for idx, score in enumerate(sims):
        chunk = rag.chunks[idx]
        prev = best.get(chunk.slug)
        if prev is None or score > prev[0]:
            snippet = re.sub(r"\s+", " ", chunk.text)[:200]
            best[chunk.slug] = (float(score), chunk.section, snippet)
    return best


def rank_vacancies_for_cv(
    cv_text: str,
    *,
    rag: VacatureRAG | None = None,
    vacancies: list[dict] | None = None,
    location: str | None = None,
    open_only: bool = True,
    top_n: int = 50,
    ref: date | None = None,
    exclude_dismissed: bool = True,
) -> list[MatchResult]:
    ref = ref or date.today()
    vacancies = vacancies if vacancies is not None else load_all_vacancies()
    dismissed = get_dismissed_slugs() if exclude_dismissed else set()
    cv_query = cv_text_to_query(cv_text)
    cv_lower = cv_text.lower()

    if rag is None:
        rag = VacatureRAG()
        rag.load()

    rag_map = _rag_scores(rag, cv_query)
    kw_map = _keyword_scores(vacancies, cv_lower)

    results: list[MatchResult] = []
    for v in vacancies:
        slug = v.get("slug", "")
        if not slug or slug in dismissed:
            continue
        if open_only and not is_beschikbaar(v, ref=ref)[0]:
            continue
        loc = (v.get("location") or "").lower()
        if location and location.lower() not in loc:
            continue
        rag_s, section, snippet = rag_map.get(slug, (0.0, "-", ""))
        kw_s = kw_map.get(slug, 0.0)
        deadline = v.get("solliciteer_deadline")
        if hasattr(deadline, "isoformat"):
            deadline = deadline.isoformat()
        results.append(
            MatchResult(
                slug=slug,
                title=v.get("title", ""),
                organisation=v.get("organisation", ""),
                location=v.get("location", ""),
                url=v.get("url", ""),
                rag_score=rag_s,
                keyword_score=kw_s,
                section=section,
                snippet=snippet,
                solliciteer_deadline=deadline,
            )
        )

    results.sort(key=lambda r: (r.rag_score, r.keyword_score), reverse=True)
    return results[:top_n]
