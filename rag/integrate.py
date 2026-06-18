"""Koppeling tussen vacature-match workflow en RAG-index."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = Path(__file__).resolve().parent


def should_rebuild_rag(argv: list[str]) -> bool:
    if "--no-rag" in argv:
        return False
    if "--rebuild-rag" in argv:
        return True
    return "--report-only" not in argv


def rebuild_rag_subprocess() -> int:
    """Herbouw index via run.sh (eigen PYTHONPATH/deps)."""
    run_sh = RAG_DIR / "run.sh"
    build_py = RAG_DIR / "build_index.py"
    if not run_sh.exists():
        print(f"RAG run.sh ontbreekt: {run_sh}", file=sys.stderr)
        return 1
    result = subprocess.run(
        [str(run_sh), str(build_py)],
        cwd=str(RAG_DIR),
        check=False,
    )
    return int(result.returncode)


def maybe_rebuild_rag(argv: list[str]) -> None:
    if not should_rebuild_rag(argv):
        return
    print("RAG-index herbouwen...")
    code = rebuild_rag_subprocess()
    if code != 0:
        print("RAG-herbouw mislukt (vacature-match is wel afgerond)", file=sys.stderr)
