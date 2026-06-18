#!/usr/bin/env python3
"""Genereer motivatiebrief-briefing uit RAG + optionele CV-kern."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from vacature_rag import DEFAULT_INDEX_DIR, REPO_ROOT, VacatureRAG, ensure_deps_on_path

ensure_deps_on_path()

DEFAULT_CV_KERN = Path(os.environ.get("CV_PATH", str(REPO_ROOT / "examples" / "cv-voorbeeld.txt")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Motivatiebrief-briefing uit RAG-index.")
    parser.add_argument("slug", help="Vacature-slug of deel daarvan (bijv. senior-data-engineer-IND-2026-3570)")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument(
        "--cv-kern",
        type=Path,
        default=DEFAULT_CV_KERN,
        help=f"Pad naar cv-kern markdown (default: {DEFAULT_CV_KERN.name})",
    )
    parser.add_argument("--no-cv-kern", action="store_true", help="Geen CV-kern opnemen")
    parser.add_argument("-o", "--output", type=Path, help="Schrijf briefing naar bestand")
    args = parser.parse_args()

    rag = VacatureRAG(index_dir=args.index_dir)
    try:
        rag.load()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        print("Tip: draai eerst `./run.sh build_index.py`.", file=sys.stderr)
        return 1

    slug = rag.resolve_slug(args.slug)
    if not slug:
        print(f"Geen vacature gevonden voor: {args.slug}", file=sys.stderr)
        return 1

    cv_text = ""
    if not args.no_cv_kern:
        if args.cv_kern.exists():
            cv_text = args.cv_kern.read_text(encoding="utf-8")
        else:
            print(f"CV-kern niet gevonden: {args.cv_kern}", file=sys.stderr)

    briefing = rag.vacancy_briefing(slug, cv_kern=cv_text)

    if args.output:
        args.output.write_text(briefing, encoding="utf-8")
        print(f"Briefing geschreven: {args.output} (slug: {slug})")
    else:
        print(briefing)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
