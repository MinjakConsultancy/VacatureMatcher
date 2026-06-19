"""LLM-diensten bovenop RAG-briefings en (optioneel) Ollama/OpenAI-compatible."""

from __future__ import annotations

import os
from pathlib import Path

from vacature_rag import DEFAULT_INDEX_DIR, VacatureRAG, ensure_deps_on_path

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").strip().lower() or "ollama"
_OPENAI_PROVIDERS = {"openai", "openai_compatible", "tocode"}

if LLM_PROVIDER in _OPENAI_PROVIDERS:
    from openai_compatible_client import (  # type: ignore
        DEFAULT_BASE_URL,
        DEFAULT_MODEL,
        chat,
        is_available,
        list_models,
        resolve_model,
    )
else:
    from ollama_client import (  # type: ignore
        DEFAULT_BASE_URL,
        DEFAULT_MODEL,
        chat,
        is_available,
        list_models,
        resolve_model,
    )

ensure_deps_on_path()

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
DEFAULT_CV_KERN = Path(
    os.environ.get("CV_PATH", str(REPO_ROOT / "examples" / "cv-voorbeeld.txt"))
)


def _load_rules() -> str:
    path = PROMPTS_DIR / "motivatie-regels.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "Schrijf formeel Nederlands. Geen standplaats als motivatie."


def build_briefing(
    slug: str,
    *,
    cv_kern: str = "",
    cv_uploaded: bool = False,
    index_dir: Path = DEFAULT_INDEX_DIR,
) -> tuple[str, str]:
    rag = VacatureRAG(index_dir=index_dir)
    rag.load()
    resolved = rag.resolve_slug(slug)
    if not resolved:
        raise KeyError(f"Vacature niet gevonden: {slug}")
    briefing = rag.vacancy_briefing(resolved, cv_kern=cv_kern, cv_uploaded=cv_uploaded)
    return resolved, briefing


def _load_example() -> str:
    try:
        from motivatie_stijl_loader import load_active_motivatie_stijl_text

        uploaded = load_active_motivatie_stijl_text()
        if uploaded and uploaded.strip():
            return uploaded.strip()
    except Exception:
        pass
    path = PROMPTS_DIR / "motivatie-voorbeeld-odi.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _truncate_cv(text: str, limit: int = 8000) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[… CV ingekort …]"


def _truncate_briefing(text: str, limit: int = 14000) -> str:
    """Beperk vacaturetekst; behoud kop, CV en instructies."""
    text = text.strip()
    if len(text) <= limit:
        return text
    marker = "## Vacaturetekst"
    idx = text.find(marker)
    if idx == -1:
        return text[:limit] + "\n\n[… briefing ingekort …]"
    head = text[:idx].rstrip()
    tail_budget = limit - len(head) - 40
    if tail_budget < 1500:
        return text[:limit] + "\n\n[… briefing ingekort …]"
    vac_part = text[idx:]
    if len(vac_part) <= tail_budget:
        return text
    return head + "\n\n" + vac_part[:tail_budget] + "\n\n[… vacaturetekst ingekort …]"


def _llm_unavailable_message() -> str:
    if LLM_PROVIDER in _OPENAI_PROVIDERS:
        return (
            f"OpenAI-compatible LLM niet bereikbaar op {DEFAULT_BASE_URL} "
            f"(LLM_PROVIDER={LLM_PROVIDER}). "
            "Controleer OPENAI_BASE_URL, OPENAI_API_KEY en netwerk/VPN."
        )
    return (
        f"Ollama niet bereikbaar op {DEFAULT_BASE_URL} (LLM_PROVIDER={LLM_PROVIDER}). "
        "Start Ollama op de host (ollama serve) en controleer OLLAMA_BASE_URL "
        "(Docker: http://host.docker.internal:11434)."
    )


def _require_llm_available() -> None:
    if not is_available():
        raise RuntimeError(_llm_unavailable_message())


def generate_motivatie(
    slug: str,
    *,
    cv_kern: str = "",
    cv_kern_path: Path | None = None,
    cv_uploaded: bool = False,
    index_dir: Path = DEFAULT_INDEX_DIR,
    model: str | None = None,
    require_cv: bool = False,
) -> dict[str, str]:
    _require_llm_available()

    kern = cv_kern
    if not kern and cv_kern_path and cv_kern_path.exists():
        kern = cv_kern_path.read_text(encoding="utf-8")
    elif not kern and not require_cv and DEFAULT_CV_KERN.exists():
        kern = DEFAULT_CV_KERN.read_text(encoding="utf-8")
    elif not kern and require_cv:
        raise ValueError("Geen actief CV geüpload. Upload eerst een CV op de Match-pagina.")

    if kern:
        kern = _truncate_cv(kern)

    resolved, briefing = build_briefing(
        slug,
        cv_kern=kern,
        cv_uploaded=cv_uploaded,
        index_dir=index_dir,
    )
    briefing = _truncate_briefing(briefing)
    rules = _load_rules()
    example = _load_example()
    used_model = resolve_model(model=model)

    system_parts = [
        "Je schrijft motivatiebrieven voor Nederlandse overheidsvacatures (IkWerk).",
        "Volg de regels strikt. Schrijf alleen de brief, geen uitleg of metadata.",
        "Gebruik vergelijkbare toon, alinea-opbouw en lengte als het stijlvoorbeeld (~300-400 woorden).",
        "",
        rules,
    ]
    if example:
        system_parts.extend(["", "## Stijlvoorbeeld", "", example])

    messages = [
        {
            "role": "system",
            "content": "\n".join(system_parts),
        },
        {
            "role": "user",
            "content": (
                "Schrijf een motivatiebrief (ca. 250-400 woorden) op basis van onderstaande briefing. "
                "Koppel concrete CV-ervaring aan eisen uit de vacature.\n\n"
                f"{briefing}"
            ),
        },
    ]
    text = chat(messages, model=used_model)
    return {"slug": resolved, "text": text, "model": used_model}


def explain_match(
    slug: str,
    cv_text: str,
    *,
    index_dir: Path = DEFAULT_INDEX_DIR,
    model: str | None = None,
) -> dict[str, str]:
    _require_llm_available()

    resolved, briefing = build_briefing(slug, index_dir=index_dir)
    used_model = resolve_model(model=model)
    preview = cv_text[:4000]

    messages = [
        {
            "role": "system",
            "content": "Je bent een carrière-adviseur. Antwoord in het Nederlands, kort en concreet (max 200 woorden).",
        },
        {
            "role": "user",
            "content": (
                f"Leg uit waarom deze vacature wel of niet past bij dit CV. "
                f"Noem 3 sterke punten en 2 aandachtspunten.\n\n"
                f"## Vacature\n{briefing[:6000]}\n\n## CV (fragment)\n{preview}"
            ),
        },
    ]
    text = chat(messages, model=used_model, temperature=0.3)
    return {"slug": resolved, "text": text, "model": used_model}


def status() -> dict:
    ok = is_available()
    models = list_models() if ok else []
    return {
        "provider": LLM_PROVIDER,
        "available": ok,
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL or (models[0] if models else None),
        "models": models,
    }
