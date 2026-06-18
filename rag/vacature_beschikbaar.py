"""Beschikbaarheid vacatures: deadline uit detailtekst (Solliciteer voor …)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from sinds_dates import DUTCH_MONTHS

DEADLINE_RE = re.compile(
    r"Solliciteer voor (\d{1,2})\s+(" + "|".join(DUTCH_MONTHS.keys()) + r")\s+(\d{4})",
    re.IGNORECASE,
)

CLOSED_PHRASES = (
    "niet meer beschikbaar",
    "niet langer beschikbaar",
    "vacature is gesloten",
    "vacature is vervallen",
    "niet meer te solliciteren",
    "deze vacature is niet meer",
    "ingetrokken",
)


def parse_sollicitatie_deadline(text: str) -> date | None:
    deadlines: list[date] = []
    for day_s, month_s, year_s in DEADLINE_RE.findall(text):
        month = DUTCH_MONTHS.get(month_s.lower())
        if not month:
            continue
        try:
            deadlines.append(date(int(year_s), month, int(day_s)))
        except ValueError:
            continue
    return min(deadlines) if deadlines else None


def is_beschikbaar(
    vacancy: dict[str, Any],
    *,
    ref: date | None = None,
) -> tuple[bool, str]:
    ref = ref or date.today()
    deadline_field = vacancy.get("solliciteer_deadline")
    if deadline_field is not None:
        if hasattr(deadline_field, "isoformat"):
            d = deadline_field
        else:
            try:
                d = date.fromisoformat(str(deadline_field)[:10])
            except ValueError:
                d = None
        if d is not None:
            if d <= ref:
                return False, f"deadline verstreken (voor {d.isoformat()})"
            return True, f"open tot {d.isoformat()} (exclusief)"

    text = str(vacancy.get("detail_text", ""))
    low = text.lower()

    for phrase in CLOSED_PHRASES:
        if phrase in low:
            return False, phrase

    if "solliciteren" not in low and text.strip():
        return False, "geen solliciteermogelijkheid in tekst"

    deadline = parse_sollicitatie_deadline(text)
    if deadline is None:
        return True, "geen deadline gevonden"

    if deadline <= ref:
        return False, f"deadline verstreken (voor {deadline.isoformat()})"

    return True, f"open tot {deadline.isoformat()} (exclusief)"
