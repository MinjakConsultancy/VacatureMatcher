"""Tests for job queue constants."""

from __future__ import annotations

from app.services.jobs import LLM_JOB_TYPES


def test_llm_job_types():
    assert "llm_motivatie" in LLM_JOB_TYPES
    assert "llm_explain" in LLM_JOB_TYPES
    assert "cv_match" not in LLM_JOB_TYPES
