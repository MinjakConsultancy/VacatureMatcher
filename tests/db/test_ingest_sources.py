"""Ingest metadata helpers for scrape sources."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "db"))

from ingest_run import _filter_sets_from_meta  # noqa: E402


def test_filter_sets_from_meta_wbo():
    meta = {
        "source": "wbo",
        "filter_set": "wbo",
        "filter_sets": ["wbo"],
        "summaries": [{"filter_set": "wbo", "path": "/tmp/x.json"}],
    }
    assert _filter_sets_from_meta(meta) == ["wbo"]


def test_filter_sets_from_meta_legacy_both():
    meta = {"filter": "both", "summaries": []}
    assert set(_filter_sets_from_meta(meta)) == {"breed", "ict"}
