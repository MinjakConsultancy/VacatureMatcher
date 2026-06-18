#!/usr/bin/env python3
"""Genereer motivatiebrief via Ollama + RAG-briefing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from llm_service import DEFAULT_CV_KERN, generate_motivatie
from vacature_rag import DEFAULT_INDEX_DIR, ensure_deps_on_path

ensure_deps_on_path()


def main() -> int:
    parser = argparse.ArgumentParser(description="Motivatiebrief genereren met Ollama.")
    parser.add_argument("slug", help="Vacature-slug")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--cv-kern", type=Path, default=DEFAULT_CV_KERN)
    parser.add_argument("--no-cv-kern", action="store_true")
    parser.add_argument("--model", help="Ollama-model (default: OLLAMA_MODEL of eerste beschikbare)")
    parser.add_argument("-o", "--output", type=Path, help="Schrijf naar bestand")
    args = parser.parse_args()

    try:
        result = generate_motivatie(
            args.slug,
            cv_kern_path=None if args.no_cv_kern else args.cv_kern,
            index_dir=args.index_dir,
            model=args.model,
        )
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1

    out = result["text"]
    if args.output:
        args.output.write_text(out, encoding="utf-8")
        print(f"Motivatie geschreven: {args.output} (model: {result['model']}, slug: {result['slug']})")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
