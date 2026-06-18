"""Datum-parsing voor IkWerk-vacatures."""

from __future__ import annotations

import re
from typing import Any

DUTCH_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}


def extract_plaatsingsdatum(vacancy: dict[str, Any]):
    from datetime import date

    text = str(vacancy.get("detail_text", ""))
    m = re.search(
        r"Plaatsingsdatum:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    day = int(m.group(1))
    month = DUTCH_MONTHS.get(m.group(2).lower())
    year = int(m.group(3))
    if not month:
        return None
    return date(year, month, day)
