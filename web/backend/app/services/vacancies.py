from __future__ import annotations

from datetime import date, datetime, timezone

from app.deps import get_conn
from app.models import (
    ContactOut,
    SectionOut,
    StatsOut,
    VacancyDetail,
    VacancyListItem,
    VacancyListResponse,
)


def get_dismissed_slugs() -> set[str]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT vacancy_slug FROM vacancy_user_flags WHERE dismissed = TRUE"
            )
            return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()
    finally:
        conn.close()


def list_vacancies(
    *,
    q: str | None = None,
    location: str | None = None,
    vakgebied: str | None = None,
    open_only: bool = False,
    filter_set: str | None = None,
    exclude_dismissed: bool = True,
    sort: str = "title",
    page: int = 1,
    limit: int = 30,
) -> VacancyListResponse:
    conditions: list[str] = []
    params: list[object] = []

    if q:
        conditions.append(
            "(v.title ILIKE %s OR v.organisation ILIKE %s OR v.location ILIKE %s)"
        )
        like = f"%{q}%"
        params.extend([like, like, like])
    if location:
        conditions.append("v.location ILIKE %s")
        params.append(f"%{location}%")
    if vakgebied:
        conditions.append(
            "EXISTS (SELECT 1 FROM vacancy_vakgebieden vv WHERE vv.vacancy_slug = v.slug AND vv.vakgebied ILIKE %s)"
        )
        params.append(f"%{vakgebied}%")
    if open_only:
        conditions.append(
            "(v.solliciteer_deadline IS NULL OR CURRENT_DATE < v.solliciteer_deadline)"
        )
        conditions.append("v.status = 'open'")
    if filter_set:
        conditions.append(
            "EXISTS (SELECT 1 FROM vacancy_filters vf WHERE vf.vacancy_slug = v.slug AND vf.filter_set = %s)"
        )
        params.append(filter_set)
    if exclude_dismissed:
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM vacancy_user_flags f WHERE f.vacancy_slug = v.slug AND f.dismissed = TRUE)"
        )

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order_map = {
        "title": "v.title ASC",
        "deadline": "v.solliciteer_deadline ASC NULLS LAST",
        "deadline_desc": "v.solliciteer_deadline DESC NULLS LAST",
    }
    order = order_map.get(sort, "v.title ASC")
    offset = (max(page, 1) - 1) * limit

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM vacancies v {where}", params)
            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT v.slug, v.url, v.title, v.organisation, v.location,
                       v.scale, v.hours, v.solliciteer_deadline, v.status,
                       COALESCE(f.dismissed, FALSE)
                FROM vacancies v
                LEFT JOIN vacancy_user_flags f ON f.vacancy_slug = v.slug
                {where}
                ORDER BY {order}
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )
            rows = cur.fetchall()
            items: list[VacancyListItem] = []
            for row in rows:
                slug = row[0]
                cur.execute(
                    "SELECT vakgebied FROM vacancy_vakgebieden WHERE vacancy_slug = %s ORDER BY sort_order",
                    (slug,),
                )
                tags = [r[0] for r in cur.fetchall()]
                items.append(
                    VacancyListItem(
                        slug=row[0],
                        url=row[1],
                        title=row[2],
                        organisation=row[3],
                        location=row[4],
                        scale=row[5],
                        hours=row[6],
                        solliciteer_deadline=row[7],
                        status=row[8],
                        dismissed=bool(row[9]),
                        vakgebieden=tags,
                    )
                )
    finally:
        conn.close()

    return VacancyListResponse(items=items, total=total, page=page, limit=limit)


def get_vacancy(slug: str) -> VacancyDetail | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.*, COALESCE(f.dismissed, FALSE)
                FROM vacancies v
                LEFT JOIN vacancy_user_flags f ON f.vacancy_slug = v.slug
                WHERE v.slug = %s
                """,
                (slug,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
            data = dict(zip(cols, row))
            dismissed = bool(data.pop("dismissed", False))

            cur.execute(
                "SELECT vakgebied FROM vacancy_vakgebieden WHERE vacancy_slug = %s ORDER BY sort_order",
                (slug,),
            )
            tags = [r[0] for r in cur.fetchall()]

            cur.execute(
                """
                SELECT contact_type, name, email, phone
                FROM vacancy_contacts WHERE vacancy_slug = %s ORDER BY sort_order
                """,
                (slug,),
            )
            contacts = [
                ContactOut(contact_type=r[0], name=r[1], email=r[2], phone=r[3])
                for r in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT section_type, text, sort_order
                FROM vacancy_sections WHERE vacancy_slug = %s ORDER BY sort_order
                """,
                (slug,),
            )
            sections = [
                SectionOut(section_type=r[0], text=r[1], sort_order=r[2])
                for r in cur.fetchall()
            ]
    finally:
        conn.close()

    return VacancyDetail(
        slug=data["slug"],
        url=data["url"],
        title=data["title"],
        organisation=data.get("organisation"),
        location=data.get("location"),
        scale=data.get("scale"),
        hours=data.get("hours"),
        education=data.get("education"),
        kenmerk=data.get("kenmerk"),
        plaatsingsdatum=data.get("plaatsingsdatum"),
        solliciteer_deadline=data.get("solliciteer_deadline"),
        status=data.get("status"),
        dismissed=dismissed,
        summary=data.get("summary"),
        vakgebieden=tags,
        contacts=contacts,
        sections=sections,
    )


def set_vacancy_dismissed(slug: str, dismissed: bool) -> bool:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM vacancies WHERE slug = %s", (slug,))
                if not cur.fetchone():
                    return False
                if dismissed:
                    cur.execute(
                        """
                        INSERT INTO vacancy_user_flags (vacancy_slug, dismissed, dismissed_at)
                        VALUES (%s, TRUE, %s)
                        ON CONFLICT (vacancy_slug) DO UPDATE SET
                            dismissed = TRUE,
                            dismissed_at = EXCLUDED.dismissed_at
                        """,
                        (slug, datetime.now(timezone.utc)),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO vacancy_user_flags (vacancy_slug, dismissed, dismissed_at)
                        VALUES (%s, FALSE, NULL)
                        ON CONFLICT (vacancy_slug) DO UPDATE SET
                            dismissed = FALSE,
                            dismissed_at = NULL
                        """,
                        (slug,),
                    )
    finally:
        conn.close()
    return True


def get_stats() -> StatsOut:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM vacancies")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*) FROM vacancies
                WHERE status = 'open'
                  AND (solliciteer_deadline IS NULL OR CURRENT_DATE < solliciteer_deadline)
                """
            )
            open_count = cur.fetchone()[0]
            cur.execute(
                "SELECT MAX(finished_at) FROM scrape_runs WHERE status = 'done'"
            )
            last = cur.fetchone()[0]
    finally:
        conn.close()

    return StatsOut(
        total=total,
        open_count=open_count,
        closed_count=total - open_count,
        last_scrape=last,
    )
