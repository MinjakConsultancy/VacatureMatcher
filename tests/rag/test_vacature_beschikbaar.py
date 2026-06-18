"""Tests for rag/vacature_beschikbaar.py."""

from __future__ import annotations

from datetime import date

from vacature_beschikbaar import is_beschikbaar, parse_sollicitatie_deadline


def test_open_vacancy_by_deadline_field():
    v = {"solliciteer_deadline": "2026-12-01", "detail_text": ""}
    ok, _ = is_beschikbaar(v, ref=date(2026, 6, 1))
    assert ok


def test_closed_vacancy_by_deadline_field():
    v = {"solliciteer_deadline": "2026-01-01", "detail_text": ""}
    ok, reason = is_beschikbaar(v, ref=date(2026, 6, 1))
    assert not ok
    assert "verstreken" in reason


def test_parse_dutch_deadline_from_text():
    text = "Solliciteer voor 15 juli 2026 via IkWerk."
    d = parse_sollicitatie_deadline(text)
    assert d == date(2026, 7, 15)
