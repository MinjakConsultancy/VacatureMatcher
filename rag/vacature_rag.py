"""RAG-index voor IkWerk-vacatureteksten: laden, chunken, indexeren en zoeken."""

from __future__ import annotations

import os
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix, load_npz, save_npz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX_DIR = Path(
    os.environ.get("RAG_INDEX_DIR", str(Path(__file__).resolve().parent / "index"))
)

VACATURE_SOURCES: list[Path] = []

SECTION_MARKERS = (
    "Dit ga je doen",
    "Dit krijg je",
    "Dit bieden we nog meer",
    "Dit vragen wij",
    "Hier kom je te werken",
    "Bijzonderheden",
    "Over de functiegroep",
)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


@dataclass
class Chunk:
    chunk_id: int
    slug: str
    title: str
    organisation: str
    location: str
    url: str
    source: str
    section: str
    chunk_idx: int
    text: str

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "slug": self.slug,
            "title": self.title,
            "organisation": self.organisation,
            "location": self.location,
            "url": self.url,
            "source": self.source,
            "section": self.section,
            "chunk_idx": self.chunk_idx,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Chunk:
        return cls(**data)


@dataclass
class SearchResult:
    score: float
    chunk: Chunk

    def snippet(self, max_len: int = 280) -> str:
        text = re.sub(r"\s+", " ", self.chunk.text).strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_detail_text(detail_text: str) -> str:
    """Haal UI-ruis weg en behoud inhoudelijke secties."""
    if not detail_text:
        return ""

    text = detail_text
    for marker in (
        "Naar overzicht",
        "Bewaar vacature",
        "Deel vacature per email",
        "Print",
        "Op deze pagina",
        "Solliciteren",
        "Relevante vacatures",
        "Bekijk bewaarde vacatures",
        "Scroll naar de top",
        "Stel gerust je vraag",
        "Meer informatie over deze vacature",
        "Meer informatie over de sollicitatieprocedure",
        "[email protected]",
    ):
        text = text.replace(marker, " ")

    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _normalize_ws(text)


def extract_sections(detail_text: str) -> dict[str, str]:
    """Splits vacaturetekst op standaard IkWerk-koppen."""
    cleaned = clean_detail_text(detail_text)
    if not cleaned:
        return {}

    pattern = "|".join(re.escape(m) for m in SECTION_MARKERS)
    parts = re.split(rf"(?=(?:{pattern}))", cleaned)
    sections: dict[str, str] = {}
    current = "intro"
    buffer: list[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        matched = next((m for m in SECTION_MARKERS if part.startswith(m)), None)
        if matched:
            if buffer:
                sections[current] = _normalize_ws(" ".join(buffer))
            current = matched
            buffer = [part[len(matched) :].strip()]
        else:
            buffer.append(part)

    if buffer:
        sections[current] = _normalize_ws(" ".join(buffer))

    return {k: v for k, v in sections.items() if len(v) > 40}


def sliding_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = _normalize_ws(text)
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def vacancy_header(v: dict) -> str:
    return _normalize_ws(
        " | ".join(
            filter(
                None,
                [
                    v.get("title", ""),
                    v.get("organisation", ""),
                    v.get("location", ""),
                    v.get("scale", ""),
                    v.get("hours", ""),
                ],
            )
        )
    )


def _enrich_vacancy_row(cur, item: dict) -> dict:
    """Voeg secties, vakgebieden en contacten toe aan een vacancies-rij."""
    slug = item["slug"]
    cur.execute(
        """
        SELECT section_type, text FROM vacancy_sections
        WHERE vacancy_slug = %s ORDER BY sort_order
        """,
        (slug,),
    )
    sections = [{"section_type": r[0], "text": r[1]} for r in cur.fetchall()]
    cur.execute(
        """
        SELECT vakgebied FROM vacancy_vakgebieden
        WHERE vacancy_slug = %s ORDER BY sort_order
        """,
        (slug,),
    )
    vakgebieden = [r[0] for r in cur.fetchall()]
    cur.execute(
        """
        SELECT contact_type, name, email, phone
        FROM vacancy_contacts WHERE vacancy_slug = %s ORDER BY sort_order
        """,
        (slug,),
    )
    contacts = [
        {"contact_type": r[0], "name": r[1], "email": r[2], "phone": r[3]}
        for r in cur.fetchall()
    ]
    cur.execute(
        "SELECT filter_set FROM vacancy_filters WHERE vacancy_slug = %s LIMIT 1",
        (slug,),
    )
    fs = cur.fetchone()
    source = fs[0] if fs else "postgres"
    return {
        "slug": slug,
        "url": item.get("url") or "",
        "title": item.get("title") or "",
        "organisation": item.get("organisation") or "",
        "location": item.get("location") or "",
        "scale": item.get("scale") or "",
        "hours": item.get("hours") or "",
        "education": item.get("education") or "",
        "summary": item.get("summary") or "",
        "detail_text": item.get("detail_text") or "",
        "vakgebieden": vakgebieden,
        "contacts": contacts,
        "_source": source,
        "_sections": {s["section_type"]: s["text"] for s in sections},
    }


def load_vacancy_by_slug(slug_or_query: str) -> dict | None:
    """Laad één vacature uit Postgres (exacte slug, deelslug of titel)."""
    needle = slug_or_query.lower().strip()
    if not needle:
        return None
    try:
        db_dir = REPO_ROOT / "db"
        if str(db_dir) not in sys.path:
            sys.path.insert(0, str(db_dir))
        from db import connect  # noqa: WPS433

        conn = connect()
    except Exception:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM vacancies WHERE lower(slug) = %s", (needle,))
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    SELECT * FROM vacancies
                    WHERE lower(slug) LIKE %s
                    ORDER BY length(slug)
                    LIMIT 1
                    """,
                    (f"%{needle}%",),
                )
                row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    SELECT * FROM vacancies
                    WHERE lower(title) LIKE %s
                    LIMIT 1
                    """,
                    (f"%{needle}%",),
                )
                row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
            item = dict(zip(cols, row))
            return _enrich_vacancy_row(cur, item)
    except Exception:
        return None
    finally:
        conn.close()


def load_vacancies_from_postgres() -> list[dict] | None:
    """Laad vacatures uit PostgreSQL; None bij geen DB."""
    try:
        db_dir = REPO_ROOT / "db"
        if str(db_dir) not in sys.path:
            sys.path.insert(0, str(db_dir))
        from db import connect  # noqa: WPS433

        conn = connect()
    except Exception:
        return None

    merged: list[dict] = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM vacancies ORDER BY title")
            cols = [d.name for d in cur.description]
            for row in cur.fetchall():
                item = dict(zip(cols, row))
                merged.append(_enrich_vacancy_row(cur, item))
    except Exception:
        return None
    finally:
        conn.close()

    return merged if merged else None


def load_all_vacancies() -> list[dict]:
    """Laad vacatures uit PostgreSQL (silver layer)."""
    from_pg = load_vacancies_from_postgres()
    if from_pg:
        return from_pg
    raise RuntimeError(
        "Geen vacatures in PostgreSQL. Draai eerst een ververs-job (Beheer → Data verversen)."
    )


def build_chunks(vacancies: list[dict]) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_id = 0

    for v in vacancies:
        slug = v.get("slug", "")
        meta = {
            "slug": slug,
            "title": v.get("title", ""),
            "organisation": v.get("organisation", ""),
            "location": v.get("location", ""),
            "url": v.get("url", ""),
            "source": v.get("_source", ""),
        }

        header = vacancy_header(v)
        summary = _normalize_ws(v.get("summary", ""))
        vakgebieden = v.get("vakgebieden") or []
        if vakgebieden:
            header = _normalize_ws(f"{header} | Vakgebied: {', '.join(vakgebieden)}")
        if header or summary:
            intro = _normalize_ws(f"{header}. {summary}")
            for i, piece in enumerate(sliding_chunks(intro, size=400, overlap=50)):
                chunks.append(Chunk(chunk_id=chunk_id, section="metadata", chunk_idx=i, text=piece, **meta))
                chunk_id += 1

        sections = v.get("_sections") or extract_sections(v.get("detail_text", ""))
        if sections:
            for section_name, section_text in sections.items():
                for i, piece in enumerate(sliding_chunks(section_text)):
                    chunks.append(
                        Chunk(
                            chunk_id=chunk_id,
                            section=section_name,
                            chunk_idx=i,
                            text=piece,
                            **meta,
                        )
                    )
                    chunk_id += 1
        else:
            fallback = clean_detail_text(v.get("detail_text", ""))
            if fallback:
                for i, piece in enumerate(sliding_chunks(fallback)):
                    chunks.append(
                        Chunk(chunk_id=chunk_id, section="volledige_tekst", chunk_idx=i, text=piece, **meta)
                    )
                    chunk_id += 1

    return chunks


class VacatureRAG:
    def __init__(self, index_dir: Path = DEFAULT_INDEX_DIR) -> None:
        self.index_dir = Path(index_dir)
        self.chunks: list[Chunk] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix: csr_matrix | None = None

    def build(self, vacancies: list[dict] | None = None) -> int:
        vacancies = vacancies if vacancies is not None else load_all_vacancies()
        self.chunks = build_chunks(vacancies)
        if not self.chunks:
            raise ValueError("Geen chunks om te indexeren")

        texts = [c.text for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        self.matrix = self.vectorizer.fit_transform(texts)
        return len(self.chunks)

    def save(self) -> None:
        if self.vectorizer is None or self.matrix is None:
            raise RuntimeError("Index niet gebouwd; roep eerst build() aan")

        self.index_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "chunk_count": len(self.chunks),
            "vacancy_count": len({c.slug for c in self.chunks}),
            "sources": [str(p) for p in VACATURE_SOURCES if p.exists()],
        }
        (self.index_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.index_dir / "chunks.json").write_text(
            json.dumps([c.to_dict() for c in self.chunks], ensure_ascii=False),
            encoding="utf-8",
        )
        joblib.dump(self.vectorizer, self.index_dir / "vectorizer.joblib")
        save_npz(self.index_dir / "matrix.npz", self.matrix)

    def load(self) -> None:
        chunks_path = self.index_dir / "chunks.json"
        vectorizer_path = self.index_dir / "vectorizer.joblib"
        matrix_path = self.index_dir / "matrix.npz"

        if not all(p.exists() for p in (chunks_path, vectorizer_path, matrix_path)):
            raise FileNotFoundError(f"Index ontbreekt in {self.index_dir}; draai build_index.py")

        raw = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.chunks = [Chunk.from_dict(row) for row in raw]
        self.vectorizer = joblib.load(vectorizer_path)
        self.matrix = load_npz(matrix_path)

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        location: str | None = None,
        source: str | None = None,
        min_score: float = 0.05,
    ) -> list[SearchResult]:
        if self.vectorizer is None or self.matrix is None:
            raise RuntimeError("Index niet geladen")

        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix).ravel()

        candidates: list[SearchResult] = []
        for idx, score in enumerate(scores):
            if score < min_score:
                continue
            chunk = self.chunks[idx]
            if location and location.lower() not in chunk.location.lower():
                continue
            if source and source not in chunk.source:
                continue
            candidates.append(SearchResult(score=float(score), chunk=chunk))

        candidates.sort(key=lambda r: r.score, reverse=True)

        # Maximaal één chunk per vacature in top resultaten, daarna aanvullen
        seen_slugs: set[str] = set()
        diverse: list[SearchResult] = []
        for result in candidates:
            if result.chunk.slug in seen_slugs:
                continue
            seen_slugs.add(result.chunk.slug)
            diverse.append(result)
            if len(diverse) >= top_k:
                break

        if len(diverse) < top_k:
            for result in candidates:
                if result in diverse:
                    continue
                diverse.append(result)
                if len(diverse) >= top_k:
                    break

        return diverse[:top_k]

    def format_context(self, results: list[SearchResult]) -> str:
        blocks: list[str] = []
        for i, result in enumerate(results, 1):
            c = result.chunk
            blocks.append(
                "\n".join(
                    [
                        f"[{i}] {c.title} ({c.organisation}, {c.location})",
                        f"Sectie: {c.section} | Relevantie: {result.score:.3f}",
                        f"URL: {c.url}",
                        c.text,
                    ]
                )
            )
        return "\n\n---\n\n".join(blocks)

    def resolve_slug(self, slug_or_query: str) -> str | None:
        """Zoek slug op exacte slug, slug-deel of titel (index, daarna Postgres)."""
        needle = slug_or_query.lower().strip()
        by_lower = {c.slug.lower(): c.slug for c in self.chunks}
        if needle in by_lower:
            return by_lower[needle]
        partial = [orig for low, orig in by_lower.items() if needle in low]
        if partial:
            partial.sort(key=len)
            return partial[0]
        for chunk in self.chunks:
            if needle in chunk.title.lower():
                return chunk.slug
        vac = load_vacancy_by_slug(slug_or_query)
        if vac:
            return vac["slug"]
        return None

    def chunks_for_slug(self, slug: str) -> list[Chunk]:
        slug_low = slug.lower()
        rows = [c for c in self.chunks if c.slug.lower() == slug_low]
        section_order = {name: i for i, name in enumerate(SECTION_MARKERS)}
        rows.sort(
            key=lambda c: (
                0 if c.section == "metadata" else 1,
                section_order.get(c.section, 99),
                c.chunk_idx,
            )
        )
        return rows

    def _contacts_for_slug(self, slug: str) -> list[dict]:
        try:
            db_dir = REPO_ROOT / "db"
            if str(db_dir) not in sys.path:
                sys.path.insert(0, str(db_dir))
            from db import connect  # noqa: WPS433

            conn = connect()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT contact_type, name, email, phone
                    FROM vacancy_contacts WHERE vacancy_slug = %s ORDER BY sort_order
                    """,
                    (slug,),
                )
                rows = [
                    {"contact_type": r[0], "name": r[1], "email": r[2], "phone": r[3]}
                    for r in cur.fetchall()
                ]
            conn.close()
            return rows
        except Exception:
            return []

    def _briefing_lines(
        self,
        *,
        slug: str,
        title: str,
        organisation: str,
        location: str,
        url: str,
        sections: dict[str, str],
        detail_text: str,
        contacts: list[dict],
        cv_kern: str,
        cv_uploaded: bool,
        from_index: bool,
    ) -> list[str]:
        lines = [
            "# Motivatiebrief-briefing",
            "",
            f"**Vacature:** {title}",
            f"**Organisatie:** {organisation}",
            f"**Standplaats:** {location}",
            f"**URL:** {url}",
            "",
        ]
        if contacts:
            lines.append("## Contactpersonen")
            lines.append("")
            for c in contacts:
                parts = [p for p in (c.get("name"), c.get("email"), c.get("phone")) if p]
                label = c.get("contact_type", "contact").replace("_", " ")
                lines.append(f"- **{label}:** {' | '.join(parts)}")
            lines.append("")
        if cv_kern.strip():
            cv_heading = "## CV (geupload)" if cv_uploaded else "## CV-kern"
            lines.extend([cv_heading, "", cv_kern.strip(), ""])

        source_label = "uit RAG-index" if from_index else "uit database"
        lines.extend([f"## Vacaturetekst ({source_label})", ""])
        if sections:
            for section_name, section_text in sections.items():
                lines.append(f"### {section_name}")
                lines.append("")
                lines.append(section_text)
                lines.append("")
        else:
            fallback = clean_detail_text(detail_text)
            if fallback:
                lines.append(fallback)
                lines.append("")

        lines.extend(
            [
                "## Instructie voor schrijven",
                "",
                "- Formeel Nederlands, openingszin: «… solliciteer ik naar de functie <titel> …»",
                "- Geen woonplaats/standplaats als argument; geen em-dashes",
                "- Koppel concrete CV-ervaring aan eisen uit «Dit vragen wij»",
                "- Zie `.cursor/skills/ikwerk-vacature-match/motivatie-regels.md` voor volledige regels",
            ]
        )
        return lines

    def vacancy_briefing(self, slug: str, *, cv_kern: str = "", cv_uploaded: bool = False) -> str:
        chunks = self.chunks_for_slug(slug)
        if chunks:
            head = chunks[0]
            sections: dict[str, str] = {}
            current = ""
            for chunk in chunks:
                if chunk.section == "metadata":
                    continue
                if chunk.section not in sections:
                    sections[chunk.section] = chunk.text
                else:
                    sections[chunk.section] += " " + chunk.text
            contacts = self._contacts_for_slug(slug)
            lines = self._briefing_lines(
                slug=slug,
                title=head.title,
                organisation=head.organisation,
                location=head.location,
                url=head.url,
                sections=sections,
                detail_text="",
                contacts=contacts,
                cv_kern=cv_kern,
                cv_uploaded=cv_uploaded,
                from_index=True,
            )
            return "\n".join(lines)

        vac = load_vacancy_by_slug(slug)
        if not vac:
            raise KeyError(f"Geen vacature gevonden voor slug: {slug}")

        sections = vac.get("_sections") or extract_sections(vac.get("detail_text", ""))
        contacts = vac.get("contacts") or self._contacts_for_slug(vac["slug"])
        lines = self._briefing_lines(
            slug=vac["slug"],
            title=vac.get("title", ""),
            organisation=vac.get("organisation", ""),
            location=vac.get("location", ""),
            url=vac.get("url", ""),
            sections=sections,
            detail_text=vac.get("detail_text", ""),
            contacts=contacts,
            cv_kern=cv_kern,
            cv_uploaded=cv_uploaded,
            from_index=False,
        )
        return "\n".join(lines)


def rebuild_index(index_dir: Path = DEFAULT_INDEX_DIR) -> int:
    """Herbouw de volledige RAG-index (alle bronnen)."""
    rag = VacatureRAG(index_dir=index_dir)
    vacancies = load_all_vacancies()
    if not vacancies:
        return 1
    rag.build(vacancies)
    rag.save()
    n = len(rag.chunks)
    print(f"RAG: {len(vacancies)} vacatures, {n} chunks -> {index_dir}")
    return n


def ensure_deps_on_path() -> None:
    deps = Path(__file__).resolve().parent / "deps"
    if deps.is_dir() and str(deps) not in sys.path:
        sys.path.insert(0, str(deps))
