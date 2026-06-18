"""Tests for rag/sinds_dates.py."""

from __future__ import annotations

from datetime import date

from sinds_dates import extract_plaatsingsdatum


def test_extract_plaatsingsdatum():
    v = {"detail_text": "Plaatsingsdatum: 3 juni 2026\nOverige tekst."}
    assert extract_plaatsingsdatum(v) == date(2026, 6, 3)
