"""Tests for rag/vacature_rag.py index build/load."""

from __future__ import annotations

from vacature_rag import VacatureRAG, build_chunks


def test_build_chunks_creates_metadata(sample_vacancies):
    chunks = build_chunks(sample_vacancies)
    assert len(chunks) > 0
    slugs = {c.slug for c in chunks}
    assert "senior-data-engineer-voorbeeld-2026-001" in slugs


def test_index_round_trip(tmp_path, sample_vacancies):
    index_dir = tmp_path / "idx"
    rag = VacatureRAG(index_dir=index_dir)
    n = rag.build(sample_vacancies)
    assert n > 0
    rag.save()
    rag2 = VacatureRAG(index_dir=index_dir)
    rag2.load()
    assert rag2.matrix is not None
    assert len(rag2.chunks) == n
