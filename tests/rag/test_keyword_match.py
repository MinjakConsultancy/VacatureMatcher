"""Tests for rag/keyword_match.py."""

from __future__ import annotations

from keyword_match import KeywordConfig, score_vacancy


def test_data_engineer_scores_higher_than_sap_junior(sample_vacancies, sample_cv_text):
    cfg = KeywordConfig(
        positive={"python": 3.0, "data engineer": 3.0, "kubernetes": 2.5},
        negative={"sap": -2.0, "junior": -2.0},
        bonuses=[],
    )
    data_eng = sample_vacancies[0]
    sap_junior = sample_vacancies[2]
    s1, _ = score_vacancy(data_eng, sample_cv_text, config=cfg)
    s2, _ = score_vacancy(sap_junior, sample_cv_text, config=cfg)
    assert s1 > s2


def test_cv_bonus_increases_score(sample_vacancies):
    cfg = KeywordConfig(positive={"python": 4.0}, negative={}, bonuses=[])
    vac = {**sample_vacancies[0], "detail_text": "python python python"}
    without_cv, _ = score_vacancy(vac, "geen overlap", config=cfg)
    with_cv, hits = score_vacancy(vac, "ervaring met python", config=cfg)
    assert with_cv > without_cv
    assert any("cv+vac" in h for h in hits)
