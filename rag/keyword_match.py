"""Keyword-scoring voor CV-match (gedeeld door web API en CLI)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_POSITIVE: dict[str, float] = {
    "python": 3.0,
    "java": 2.5,
    "typescript": 2.5,
    "react": 2.0,
    "sql": 2.5,
    "api": 2.0,
    "rest": 1.5,
    "kubernetes": 2.5,
    "docker": 2.0,
    "azure": 2.5,
    "aws": 2.0,
    "devops": 3.0,
    "ci/cd": 2.5,
    "gitlab": 2.0,
    "jenkins": 1.5,
    "data engineer": 3.0,
    "data-engineer": 3.0,
    "data platform": 2.5,
    "machine learning": 2.5,
    "ai": 2.0,
    "spark": 2.0,
    "dbt": 2.0,
    "elasticsearch": 1.5,
    "kafka": 1.5,
    "software engineer": 3.0,
    "techlead": 2.5,
    "tech lead": 2.5,
    "technical lead": 2.5,
    "architect": 2.0,
    "scrum master": 2.0,
    "product owner": 1.5,
    "integratie": 2.0,
    "integration": 2.0,
    "platform engineer": 2.5,
    "security": 2.0,
    "cyber": 2.0,
    "overheid": 1.0,
    "agile": 1.5,
    "scrum": 1.5,
    "rag": 2.0,
    "retrieval augmented": 2.0,
    "agentic": 2.0,
    "keycloak": 2.0,
    "dagster": 2.0,
    "gitops": 2.0,
    "airflow": 1.5,
    "helm": 1.5,
    "databricks": 2.0,
}

DEFAULT_NEGATIVE: dict[str, float] = {
    "sap": -2.0,
    "abap": -3.0,
    "juridisch": -1.5,
    "juridische": -1.5,
    "beleidsmedewerker": -1.0,
    "trainee": -2.0,
    "junior": -2.0,
    "medior": -0.5,
}

DEFAULT_BONUSES: list[dict[str, Any]] = [
    {
        "id": "tech_title",
        "when": "title_contains_any",
        "terms": [
            "engineer",
            "developer",
            "ontwikkelaar",
            "data",
            "devops",
            "architect",
            "scrum",
            "platform",
        ],
        "weight": 2.0,
    },
]


@dataclass(frozen=True)
class KeywordConfig:
    positive: dict[str, float]
    negative: dict[str, float]
    bonuses: list[dict[str, Any]]


def _parse_weight_map(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for key, val in raw.items():
        try:
            out[str(key).lower()] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        text = path.read_text(encoding="utf-8")
        return _parse_minimal_yaml(text)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Fallback zonder PyYAML: alleen positive/negative maps."""
    result: dict[str, Any] = {"positive": {}, "negative": {}, "bonuses": []}
    section: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(":") and not stripped.startswith("-"):
            key = stripped[:-1].strip()
            if key in ("positive", "negative", "bonuses"):
                section = key
            continue
        if section in ("positive", "negative") and ":" in stripped:
            k, _, v = stripped.partition(":")
            try:
                result[section][k.strip()] = float(v.strip())
            except ValueError:
                pass
    return result


def load_keyword_config(path: Path | None = None) -> KeywordConfig:
    env_path = os.environ.get("KEYWORDS_CONFIG", "").strip()
    config_path = path or (Path(env_path) if env_path else REPO_ROOT / "config" / "keywords.yaml")
    if not config_path.exists():
        example = REPO_ROOT / "config" / "keywords.example.yaml"
        if example.exists() and not env_path:
            config_path = example
        else:
            return KeywordConfig(
                positive=dict(DEFAULT_POSITIVE),
                negative=dict(DEFAULT_NEGATIVE),
                bonuses=list(DEFAULT_BONUSES),
            )
    data = _load_yaml(config_path)
    positive = _parse_weight_map(data.get("positive")) or dict(DEFAULT_POSITIVE)
    negative = _parse_weight_map(data.get("negative")) or dict(DEFAULT_NEGATIVE)
    bonuses_raw = data.get("bonuses")
    bonuses = list(bonuses_raw) if isinstance(bonuses_raw, list) else list(DEFAULT_BONUSES)
    return KeywordConfig(positive=positive, negative=negative, bonuses=bonuses)


def _apply_bonuses(
    vacancy: dict,
    blob: str,
    bonuses: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    score = 0.0
    hits: list[str] = []
    title = vacancy.get("title", "").lower()
    organisation = vacancy.get("organisation", "").lower()

    for bonus in bonuses:
        if not isinstance(bonus, dict):
            continue
        weight = float(bonus.get("weight", 0))
        if not weight:
            continue
        when = bonus.get("when", "")
        label = str(bonus.get("id", when))

        if when == "title_contains_any":
            terms = [str(t).lower() for t in bonus.get("terms", [])]
            if any(t in title for t in terms):
                score += weight
                hits.append(f"+{weight:.1f} {label}")
        elif when == "blob_contains":
            term = str(bonus.get("term", "")).lower()
            if term and term in blob:
                score += weight
                hits.append(f"+{weight:.1f} {label}")
        elif when == "organisation_contains":
            term = str(bonus.get("term", "")).lower()
            if term and term in organisation:
                score += weight
                hits.append(f"+{weight:.1f} {label}")

    return score, hits


def score_vacancy(
    vacancy: dict,
    cv_text: str,
    *,
    config: KeywordConfig | None = None,
) -> tuple[float, list[str]]:
    cfg = config or load_keyword_config()
    cv_lower = cv_text.lower()
    blob = " ".join(
        str(vacancy.get(k, ""))
        for k in ("title", "organisation", "location", "scale", "summary", "detail_text")
    ).lower()

    score = 0.0
    hits: list[str] = []

    for kw, weight in cfg.positive.items():
        if kw in blob:
            bonus = weight * 0.25 if kw in cv_lower else 0.0
            total = weight + bonus
            score += total
            hits.append(f"+{total:.1f} {kw}" + (" (cv+vac)" if bonus else ""))

    for kw, weight in cfg.negative.items():
        if kw in blob:
            score += weight
            hits.append(f"{weight:.1f} {kw}")

    bonus_score, bonus_hits = _apply_bonuses(vacancy, blob, cfg.bonuses)
    score += bonus_score
    hits.extend(bonus_hits)

    return round(score, 1), hits


# Backwards compatibility for imports
CV_KEYWORDS = DEFAULT_POSITIVE
NEGATIVE_KEYWORDS = DEFAULT_NEGATIVE
