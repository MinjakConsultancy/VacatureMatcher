"""Tests for rag/match_service.py."""

from __future__ import annotations

from datetime import date

from match_service import cv_text_to_query, rank_vacancies_for_cv


def test_cv_text_to_query_extracts_profiel(sample_cv_text):
    q = cv_text_to_query(sample_cv_text)
    assert "data-engineer" in q.lower() or "data engineer" in q.lower()
    assert "Opleidingen" not in q


def test_rank_sorts_by_rag_then_keywords(sample_vacancies, sample_cv_text, tmp_rag_index):
    results = rank_vacancies_for_cv(
        sample_cv_text,
        vacancies=sample_vacancies,
        rag=tmp_rag_index,
        open_only=False,
        top_n=10,
        ref=date(2026, 1, 1),
        exclude_dismissed=False,
    )
    assert len(results) >= 2
    for a, b in zip(results, results[1:]):
        assert (a.rag_score, a.keyword_score) >= (b.rag_score, b.keyword_score)


def test_location_filter(sample_vacancies, sample_cv_text, tmp_rag_index):
    results = rank_vacancies_for_cv(
        sample_cv_text,
        vacancies=sample_vacancies,
        rag=tmp_rag_index,
        location="Utrecht",
        open_only=False,
        exclude_dismissed=False,
    )
    assert all("utrecht" in r.location.lower() for r in results)
