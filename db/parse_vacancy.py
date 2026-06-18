"""Extract gestructureerde velden uit IkWerk list- en detaildata."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "rag"))

from sinds_dates import DUTCH_MONTHS, extract_plaatsingsdatum  # noqa: E402
from vacature_beschikbaar import CLOSED_PHRASES, parse_sollicitatie_deadline  # noqa: E402

SECTION_MARKERS = (
    "Dit ga je doen",
    "Dit krijg je",
    "Dit bieden we nog meer",
    "Dit vragen wij",
    "Hier kom je te werken",
    "Bijzonderheden",
    "Over de functiegroep",
)


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_detail_text(detail_text: str) -> str:
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
    cleaned = _clean_detail_text(detail_text)
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

KENMERK_RE = re.compile(r"Kenmerk:\s*([^,\n]+)", re.IGNORECASE)
VAKGEBIED_BLOCK_RE = re.compile(r"\(bruto\)\s*(.*?)\s*Solliciteren", re.DOTALL | re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
PHONE_RE = re.compile(r"(?:\+31|0)[\d\s\-]{8,14}\d")
OBFUSCATED_EMAIL = "[email protected]"

CONTACT_SUBSECTIONS = (
    ("Meer informatie over deze vacature", "vacature_info"),
    ("Meer informatie over de sollicitatieprocedure", "sollicitatie_procedure"),
)

SKIP_VAKGEBIED = frozenset(
    {
        "",
        "route",
        "solliciteren",
        "bewaar vacature",
        "deel vacature per email",
        "print",
        "op deze pagina",
    }
)


@dataclass
class VacancyContact:
    contact_type: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    sort_order: int = 0


@dataclass
class ParsedVacancy:
    slug: str
    url: str
    title: str
    organisation: str | None = None
    location: str | None = None
    scale: str | None = None
    hours: str | None = None
    education: str | None = None
    kenmerk: str | None = None
    plaatsingsdatum: date | None = None
    solliciteer_deadline: date | None = None
    status: str = "open"
    summary: str | None = None
    detail_text: str | None = None
    vakgebieden: list[str] = field(default_factory=list)
    contacts: list[VacancyContact] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)


def _normalize_location(raw: str | None) -> str | None:
    if not raw:
        return None
    loc = raw.strip()
    loc = re.sub(r"\s*-\s*route\s*$", "", loc, flags=re.IGNORECASE).strip()
    if loc.lower() == "route":
        return None
    return loc or None


def _clean_vakgebied_line(line: str) -> str | None:
    tag = line.strip().strip(",").strip()
    if not tag:
        return None
    low = tag.lower()
    if low in SKIP_VAKGEBIED:
        return None
    if low.startswith("schaal"):
        return None
    if low.startswith("€"):
        return None
    if re.fullmatch(r"\d+\s*-\s*\d+\s*uur", low):
        return None
    if re.fullmatch(r"wo|hbo|mbo|wo bachelor|universitair master", low):
        return None
    return tag


def extract_vakgebieden(detail_text: str) -> list[str]:
    if not detail_text:
        return []
    m = VAKGEBIED_BLOCK_RE.search(detail_text)
    if not m:
        return []
    block = m.group(1)
    tags: list[str] = []
    seen: set[str] = set()
    for line in block.splitlines():
        cleaned = _clean_vakgebied_line(line)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(cleaned)
    return tags


def extract_kenmerk(detail_text: str) -> str | None:
    if not detail_text:
        return None
    m = KENMERK_RE.search(detail_text)
    return m.group(1).strip() if m else None


def _is_name_line(line: str) -> bool:
    if not line or len(line) < 3:
        return False
    low = line.lower()
    if low in {h.lower() for h, _ in CONTACT_SUBSECTIONS}:
        return False
    if EMAIL_RE.search(line) or PHONE_RE.search(line):
        return False
    if OBFUSCATED_EMAIL in line:
        return False
    if line.startswith("http"):
        return False
    if re.fullmatch(r"[\d\s\-+()]+", line):
        return False
    return bool(re.search(r"[A-Za-zÀ-ÿ]", line))


def _parse_contact_block(block: str, contact_type: str, base_order: int) -> list[VacancyContact]:
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    contacts: list[VacancyContact] = []
    current: VacancyContact | None = None
    order = base_order

    for line in lines:
        if OBFUSCATED_EMAIL in line or EMAIL_RE.search(line):
            if current is None:
                current = VacancyContact(contact_type=contact_type, sort_order=order)
            current.email = OBFUSCATED_EMAIL if OBFUSCATED_EMAIL in line else EMAIL_RE.search(line).group(0)
            continue
        phone_m = PHONE_RE.search(line.replace(" ", ""))
        if phone_m or (line.replace(" ", "").startswith("06") and re.search(r"\d{8}", line)):
            if current is None:
                current = VacancyContact(contact_type=contact_type, sort_order=order)
            current.phone = re.sub(r"\s+", "", line) if line.startswith("06") else phone_m.group(0)
            contacts.append(current)
            current = None
            order += 1
            continue
        if _is_name_line(line):
            if current and current.name:
                contacts.append(current)
                order += 1
            current = VacancyContact(contact_type=contact_type, name=line, sort_order=order)

    if current and (current.name or current.email or current.phone):
        contacts.append(current)
    return contacts


def extract_contacts(detail_text: str) -> list[VacancyContact]:
    if not detail_text:
        return []
    idx = detail_text.find("Stel gerust je vraag")
    if idx < 0:
        return []
    tail = detail_text[idx:]
    for stop in ("Relevante vacatures", "Bekijk bewaarde vacatures", "Scroll naar de top"):
        stop_idx = tail.find(stop)
        if stop_idx > 0:
            tail = tail[:stop_idx]

    contacts: list[VacancyContact] = []
    for heading, contact_type in CONTACT_SUBSECTIONS:
        h_idx = tail.find(heading)
        if h_idx < 0:
            continue
        start = h_idx + len(heading)
        end = len(tail)
        for other_heading, _ in CONTACT_SUBSECTIONS:
            if other_heading == heading:
                continue
            other_idx = tail.find(other_heading, start)
            if other_idx > 0:
                end = min(end, other_idx)
        block = tail[start:end]
        contacts.extend(_parse_contact_block(block, contact_type, len(contacts)))
    return contacts


def vacancy_status(detail_text: str) -> str:
    low = (detail_text or "").lower()
    for phrase in CLOSED_PHRASES:
        if phrase in low:
            return "closed"
    return "open"


def parse_vacancy(raw: dict[str, Any]) -> ParsedVacancy:
    """Parse list-record + detail_text naar gestructureerd model."""
    detail_text = str(raw.get("detail_text") or "")
    slug = str(raw.get("slug") or "")
    placed = extract_plaatsingsdatum(raw)
    deadline = parse_sollicitatie_deadline(detail_text)

    return ParsedVacancy(
        slug=slug,
        url=str(raw.get("url") or ""),
        title=str(raw.get("title") or ""),
        organisation=raw.get("organisation") or None,
        location=_normalize_location(raw.get("location")),
        scale=raw.get("scale") or None,
        hours=raw.get("hours") or None,
        education=raw.get("education") or None,
        kenmerk=extract_kenmerk(detail_text),
        plaatsingsdatum=placed,
        solliciteer_deadline=deadline,
        status=vacancy_status(detail_text),
        summary=raw.get("summary") or None,
        detail_text=detail_text or None,
        vakgebieden=extract_vakgebieden(detail_text),
        contacts=extract_contacts(detail_text),
        sections=extract_sections(detail_text),
    )


def section_sort_order(section_type: str) -> int:
    if section_type == "intro":
        return 0
    if section_type in SECTION_MARKERS:
        return SECTION_MARKERS.index(section_type) + 1
    if section_type == "Stel gerust je vraag":
        return 100
    return 50
