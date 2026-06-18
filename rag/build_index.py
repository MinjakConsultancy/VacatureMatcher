#!/usr/bin/env python3
"""Bouw de RAG-index uit alle vacatures.json bronnen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vacature_rag import DEFAULT_INDEX_DIR, VacatureRAG, ensure_deps_on_path, load_all_vacancies

ensure_deps_on_path()


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexeer alle IkWerk-vacatureteksten voor RAG.")
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help=f"Uitvoermap voor index (default: {DEFAULT_INDEX_DIR})",
    )
    args = parser.parse_args()

    vacancies = load_all_vacancies()
    if not vacancies:
        print("Geen vacatures gevonden.", file=sys.stderr)
        return 1

    rag = VacatureRAG(index_dir=args.index_dir)
    chunk_count = rag.build(vacancies)
    rag.save()

    unique = len({v.get("slug") for v in vacancies})
    print(f"Geïndexeerd: {unique} vacatures, {chunk_count} chunks -> {args.index_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
