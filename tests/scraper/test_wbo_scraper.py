"""Run Node scraper unit tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = Path(__file__).parent


def test_wbo_sitemap_node():
    r = subprocess.run(
        ["node", "--test", str(TESTS / "test_wbo_sitemap.mjs")],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_wbo_parse_summary_node():
    r = subprocess.run(
        ["node", "--test", str(TESTS / "test_wbo_parse_summary.mjs")],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
