#!/usr/bin/env python3
"""Zoek vacatures via de RAG-index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vacature_rag import DEFAULT_INDEX_DIR, VacatureRAG, ensure_deps_on_path

ensure_deps_on_path()


def main() -> int:
    parser = argparse.ArgumentParser(description="Zoek in geïndexeerde vacatureteksten.")
    parser.add_argument("query", help="Zoekvraag in natuurlijke taal")
    parser.add_argument("-k", "--top-k", type=int, default=8, help="Aantal resultaten")
    parser.add_argument("--location", help="Filter op standplaats (deelstring)")
    parser.add_argument("--source", help="Filter op bron/filter_set label")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument(
        "--format",
        choices=["text", "json", "context"],
        default="text",
        help="Uitvoer: text (menselijk), json, context (voor LLM-prompt)",
    )
    args = parser.parse_args()

    rag = VacatureRAG(index_dir=args.index_dir)
    try:
        rag.load()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        print("Tip: draai eerst `python3 build_index.py` in de rag-map.", file=sys.stderr)
        return 1

    results = rag.search(
        args.query,
        top_k=args.top_k,
        location=args.location,
        source=args.source,
    )

    if args.format == "json":
        payload = [
            {
                "score": round(r.score, 4),
                "title": r.chunk.title,
                "organisation": r.chunk.organisation,
                "location": r.chunk.location,
                "url": r.chunk.url,
                "section": r.chunk.section,
                "source": r.chunk.source,
                "snippet": r.snippet(),
            }
            for r in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.format == "context":
        if not results:
            print("Geen relevante vacatures gevonden.")
            return 0
        print(f"# Context voor: {args.query}\n")
        print(rag.format_context(results))
        return 0

    if not results:
        print("Geen relevante vacatures gevonden.")
        return 0

    for i, result in enumerate(results, 1):
        c = result.chunk
        print(f"{i}. [{result.score:.3f}] {c.title}")
        print(f"   {c.organisation} | {c.location} | {c.section}")
        print(f"   {c.url}")
        print(f"   {result.snippet()}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
