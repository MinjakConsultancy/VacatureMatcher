from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ContactOut(BaseModel):
    contact_type: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class SectionOut(BaseModel):
    section_type: str
    text: str
    sort_order: int = 0


class VacancyListItem(BaseModel):
    slug: str
    url: str
    title: str
    organisation: str | None = None
    location: str | None = None
    scale: str | None = None
    hours: str | None = None
    solliciteer_deadline: date | None = None
    status: str | None = None
    dismissed: bool = False
    vakgebieden: list[str] = Field(default_factory=list)


class VacancyDetail(VacancyListItem):
    education: str | None = None
    kenmerk: str | None = None
    plaatsingsdatum: date | None = None
    summary: str | None = None
    contacts: list[ContactOut] = Field(default_factory=list)
    sections: list[SectionOut] = Field(default_factory=list)


class VacancyListResponse(BaseModel):
    items: list[VacancyListItem]
    total: int
    page: int
    limit: int


class StatsOut(BaseModel):
    total: int
    open_count: int
    closed_count: int
    last_scrape: datetime | None = None


class JobCreateVervers(BaseModel):
    sinds: str = "5d"
    rebuild_index: bool = True


class VacancyDismissRequest(BaseModel):
    dismissed: bool = True


class MotivatieStijlStatusOut(BaseModel):
    has_motivatie: bool
    filename: str | None = None
    uploaded_at: str | None = None


class JobCreateMatch(BaseModel):
    rebuild_index: bool = True


class JobOut(BaseModel):
    id: str
    job_type: str
    status: str
    params: dict[str, Any] | None = None
    log_tail: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime
    finished_at: datetime | None = None
    queue_position: int | None = None


class LlmJobOut(BaseModel):
    job_id: str
    job_type: str
    status: str
    queue_position: int | None = None
    slug: str | None = None
    model: str | None = None
    text: str | None = None
    storage_key: str | None = None
    text_preview: str | None = None
    log_tail: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None


class LlmLatestOut(BaseModel):
    slug: str
    model: str
    text: str
    job_id: str
    created_at: str | None = None
    storage_key: str | None = None


class MatchResultOut(BaseModel):
    slug: str
    title: str
    organisation: str
    location: str
    url: str
    rag_score: float
    keyword_score: float
    section: str
    snippet: str
    solliciteer_deadline: str | None = None


class CvMatchResultOut(BaseModel):
    job_id: str
    status: str
    results: list[MatchResultOut] = Field(default_factory=list)


class LlmStatusOut(BaseModel):
    available: bool
    provider: str | None = None
    base_url: str
    model: str | None = None
    models: list[str] = Field(default_factory=list)


class LlmTextOut(BaseModel):
    slug: str
    text: str
    model: str


class MotivatieRequest(BaseModel):
    cv_kern: str = ""


class CvStatusOut(BaseModel):
    has_cv: bool
    filename: str | None = None
    uploaded_at: str | None = None


class ExplainMatchRequest(BaseModel):
    cv_text: str = ""
