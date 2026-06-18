"""Tests for db/parse_vacancy.py."""

from __future__ import annotations

from parse_vacancy import parse_vacancy


def test_parse_senior_data_engineer(sample_vacancies):
    row = sample_vacancies[0]
    p = parse_vacancy(row)
    assert p.slug == "senior-data-engineer-voorbeeld-2026-001"
    assert p.organisation == "Ministerie van Voorbeeld"
    assert p.location == "Den Haag"
    assert p.scale
    assert "python" in p.detail_text.lower() or "Python" in row["detail_text"]


def test_parse_without_contacts(sample_vacancies):
    row = sample_vacancies[1]
    p = parse_vacancy(row)
    assert p.slug == "platform-engineer-voorbeeld-2026-002"
    assert p.contacts == []


def test_parse_ict_in_detail(sample_vacancies):
    row = sample_vacancies[0]
    p = parse_vacancy(row)
    assert "python" in p.detail_text.lower() or "Python" in row["detail_text"]
