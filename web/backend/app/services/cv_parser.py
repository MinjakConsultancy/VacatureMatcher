from __future__ import annotations

import io
from pathlib import Path

from docx import Document


def parse_cv_bytes(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        lines: list[str] = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                if any(cells):
                    lines.append("\t".join(cells))
        return "\n".join(lines)
    raise ValueError("Alleen .docx of .txt toegestaan")
