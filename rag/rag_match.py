#!/usr/bin/env python3
"""CLI: match vacatures tegen CV via RAG + keyword-scores."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from vacature_rag import DEFAULT_INDEX_DIR, REPO_ROOT, VacatureRAG, ensure_deps_on_path, load_all_vacancies, rebuild_index

from match_service import rank_vacancies_for_cv

ensure_deps_on_path()

DEFAULT_CV = Path(os.environ.get("CV_PATH", str(REPO_ROOT / "examples" / "cv-voorbeeld.txt")))
DEFAULT_OUT = REPO_ROOT / "examples" / "match-rapport-rag.md"


def write_match_report(
    path: Path,
    *,
    cv_path: Path,
    ranked: list,
    filter_desc: str,
    top_n: int = 30,
) -> None:
    lines = [
        "# Match-rapport (RAG)",
        "",
        f"Filters: {filter_desc}",
        f"CV-bron: `{cv_path.name}`",
        "Methode: TF-IDF RAG (max chunk-similarity per vacature) + keyword-score ter referentie",
        f"Datum: {date.today().isoformat()}",
        "",
        f"## Top {top_n} matches (RAG primair, keywords tiebreaker)",
        "",
        "| Rang | RAG | Keywords | Vacature | Organisatie | Standplaats |",
        "|------|-----|----------|----------|-------------|-------------|",
    ]
    for i, r in enumerate(ranked[:top_n], 1):
        title = r.title.replace("|", "/")
        org = r.organisation.replace("|", "/")
        loc = r.location.replace("|", "/")
        lines.append(
            f"| {i} | {r.rag_score:.3f} | {r.keyword_score:.1f} | {title} | {org} | {loc} |"
        )

    lines.extend(["", "## Detail per vacature", ""])
    for i, r in enumerate(ranked[:top_n], 1):
        lines.append(
            f"### {i}. {r.title} — RAG {r.rag_score:.3f} | keywords {r.keyword_score:.1f}"
        )
        lines.append(f"- Organisatie: {r.organisation}")
        lines.append(f"- Standplaats: {r.location}")
        lines.append(f"- URL: {r.url}")
        lines.append(f"- Beste RAG-sectie: {r.section}")
        lines.append(f"- Snippet: {r.snippet}…")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG-match vacatures tegen CV.")
    parser.add_argument("--cv", type=Path, default=DEFAULT_CV, help="Pad naar CV (.txt)")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--rebuild", action="store_true", help="Index eerst herbouwen")
    parser.add_argument("--location", default="", help="Filter op standplaats (deelstring)")
    parser.add_argument("--open-only", action="store_true", help="Alleen open vacatures")
    args = parser.parse_args()

    if not args.cv.exists():
        print(f"CV niet gevonden: {args.cv}", file=sys.stderr)
        return 1

    if args.rebuild:
        code = rebuild_index(args.index_dir)
        if code != 0:
            return code

    rag = VacatureRAG(index_dir=args.index_dir)
    try:
        rag.load()
    except FileNotFoundError:
        print("Index ontbreekt; herbouwen...", file=sys.stderr)
        rebuild_index(args.index_dir)
        rag.load()

    cv_text = args.cv.read_text(encoding="utf-8")
    vacancies = load_all_vacancies()
    ranked = rank_vacancies_for_cv(
        cv_text,
        vacancies=vacancies,
        rag=rag,
        location_filter=args.location,
        open_only=args.open_only,
        top_n=max(args.top, 1),
    )

    write_match_report(
        args.out,
        cv_path=args.cv,
        ranked=ranked,
        filter_desc=f"alle vacatures in DB ({len(vacancies)}); open_only={args.open_only}",
        top_n=args.top,
    )
    print(f"Rapport: {args.out} ({len(ranked)} resultaten)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
