from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import StatsOut, VacancyDetail, VacancyDismissRequest, VacancyListResponse
from app.services.vacancies import get_dismissed_slugs, get_stats, get_vacancy, list_vacancies, set_vacancy_dismissed

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])


@router.get("", response_model=VacancyListResponse)
def vacancies_list(
    q: str | None = None,
    location: str | None = None,
    vakgebied: str | None = None,
    open_only: bool = False,
    filter_set: str | None = None,
    exclude_dismissed: bool = True,
    sort: str = "title",
    page: int = 1,
    limit: int = 30,
):
    return list_vacancies(
        q=q,
        location=location,
        vakgebied=vakgebied,
        open_only=open_only,
        filter_set=filter_set,
        exclude_dismissed=exclude_dismissed,
        sort=sort,
        page=page,
        limit=limit,
    )


@router.get("/stats/summary", response_model=StatsOut)
def stats():
    return get_stats()


@router.get("/dismissed")
def dismissed_slugs():
    return {"slugs": sorted(get_dismissed_slugs())}


@router.patch("/{slug}/dismiss", response_model=VacancyDetail)
def dismiss_vacancy(slug: str, body: VacancyDismissRequest):
    if not set_vacancy_dismissed(slug, body.dismissed):
        raise HTTPException(status_code=404, detail="Vacature niet gevonden")
    item = get_vacancy(slug)
    if not item:
        raise HTTPException(status_code=404, detail="Vacature niet gevonden")
    return item


@router.get("/{slug}", response_model=VacancyDetail)
def vacancy_detail(slug: str):
    item = get_vacancy(slug)
    if not item:
        raise HTTPException(status_code=404, detail="Vacature niet gevonden")
    return item
