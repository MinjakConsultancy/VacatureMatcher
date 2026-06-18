"""Tests for Postgres fallback when slug missing from RAG index."""

from __future__ import annotations

from vacature_rag import VacatureRAG, load_vacancy_by_slug


def test_resolve_slug_falls_back_without_index_chunks():
    rag = VacatureRAG()
    rag.chunks = []
    assert rag.resolve_slug("niet-in-index-xyz") is None


def test_vacancy_briefing_raises_when_not_in_db():
    rag = VacatureRAG()
    rag.chunks = []
    try:
        rag.vacancy_briefing("definitief-onbestaande-slug-12345")
        assert False, "expected KeyError"
    except KeyError as e:
        assert "definitief-onbestaande-slug" in str(e)
