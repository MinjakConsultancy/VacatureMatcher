"""Shared pytest fixtures."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

MIN_PYTHON = (3, 13)


def pytest_configure(config: pytest.Config) -> None:
    if sys.version_info < MIN_PYTHON:
        pytest.exit(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required; running {sys.version}",
            returncode=1,
        )

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLES = REPO_ROOT / "examples"


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def sample_vacancies() -> list[dict]:
    path = FIXTURES / "vacancies.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_sample_cv_text() -> str:
    for path in (FIXTURES / "cv.txt", EXAMPLES / "cv-voorbeeld.txt"):
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "Sample CV not found; expected tests/fixtures/cv.txt or examples/cv-voorbeeld.txt"
    )


@pytest.fixture
def sample_cv_text() -> str:
    return _load_sample_cv_text()


@pytest.fixture
def tmp_rag_index(tmp_path: Path, sample_vacancies: list[dict]):
    """Build a minimal TF-IDF index in a temp directory."""
    from vacature_rag import VacatureRAG

    index_dir = tmp_path / "rag-index"
    rag = VacatureRAG(index_dir=index_dir)
    rag.build(sample_vacancies)
    rag.save()
    loaded = VacatureRAG(index_dir=index_dir)
    loaded.load()
    return loaded
