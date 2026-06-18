"""Upsert parsed vacancies naar PostgreSQL."""

from __future__ import annotations

from typing import Any

from parse_vacancy import ParsedVacancy, section_sort_order


def upsert_vacancy(
    conn,
    parsed: ParsedVacancy,
    *,
    filter_set: str | None = None,
    detail_minio_key: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO vacancies (
                slug, url, title, organisation, location, scale, hours, education,
                kenmerk, plaatsingsdatum, solliciteer_deadline, status, summary,
                detail_text, detail_minio_key, last_seen_at
            ) VALUES (
                %(slug)s, %(url)s, %(title)s, %(organisation)s, %(location)s,
                %(scale)s, %(hours)s, %(education)s, %(kenmerk)s, %(plaatsingsdatum)s,
                %(solliciteer_deadline)s, %(status)s, %(summary)s, %(detail_text)s,
                %(detail_minio_key)s, NOW()
            )
            ON CONFLICT (slug) DO UPDATE SET
                url = EXCLUDED.url,
                title = EXCLUDED.title,
                organisation = COALESCE(EXCLUDED.organisation, vacancies.organisation),
                location = COALESCE(EXCLUDED.location, vacancies.location),
                scale = COALESCE(EXCLUDED.scale, vacancies.scale),
                hours = COALESCE(EXCLUDED.hours, vacancies.hours),
                education = COALESCE(EXCLUDED.education, vacancies.education),
                kenmerk = COALESCE(EXCLUDED.kenmerk, vacancies.kenmerk),
                plaatsingsdatum = COALESCE(EXCLUDED.plaatsingsdatum, vacancies.plaatsingsdatum),
                solliciteer_deadline = COALESCE(EXCLUDED.solliciteer_deadline, vacancies.solliciteer_deadline),
                status = EXCLUDED.status,
                summary = COALESCE(EXCLUDED.summary, vacancies.summary),
                detail_text = COALESCE(EXCLUDED.detail_text, vacancies.detail_text),
                detail_minio_key = COALESCE(EXCLUDED.detail_minio_key, vacancies.detail_minio_key),
                last_seen_at = NOW()
            """,
            {
                "slug": parsed.slug,
                "url": parsed.url,
                "title": parsed.title,
                "organisation": parsed.organisation,
                "location": parsed.location,
                "scale": parsed.scale,
                "hours": parsed.hours,
                "education": parsed.education,
                "kenmerk": parsed.kenmerk,
                "plaatsingsdatum": parsed.plaatsingsdatum,
                "solliciteer_deadline": parsed.solliciteer_deadline,
                "status": parsed.status,
                "summary": parsed.summary,
                "detail_text": parsed.detail_text,
                "detail_minio_key": detail_minio_key,
            },
        )

        if filter_set:
            cur.execute(
                """
                INSERT INTO vacancy_filters (vacancy_slug, filter_set)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (parsed.slug, filter_set),
            )

        cur.execute("DELETE FROM vacancy_vakgebieden WHERE vacancy_slug = %s", (parsed.slug,))
        for i, tag in enumerate(parsed.vakgebieden):
            cur.execute(
                """
                INSERT INTO vacancy_vakgebieden (vacancy_slug, vakgebied, sort_order)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (parsed.slug, tag, i),
            )

        cur.execute("DELETE FROM vacancy_contacts WHERE vacancy_slug = %s", (parsed.slug,))
        for contact in parsed.contacts:
            cur.execute(
                """
                INSERT INTO vacancy_contacts
                    (vacancy_slug, contact_type, name, email, phone, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    parsed.slug,
                    contact.contact_type,
                    contact.name,
                    contact.email,
                    contact.phone,
                    contact.sort_order,
                ),
            )

        cur.execute("DELETE FROM vacancy_sections WHERE vacancy_slug = %s", (parsed.slug,))
        for section_type, text in parsed.sections.items():
            cur.execute(
                """
                INSERT INTO vacancy_sections (vacancy_slug, section_type, text, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                (parsed.slug, section_type, text, section_sort_order(section_type)),
            )


def vacancy_row_to_dict(row: dict[str, Any], sections: list[dict], vakgebieden: list[str], contacts: list[dict]) -> dict[str, Any]:
    item = dict(row)
    item["detail_text"] = item.get("detail_text") or ""
    item["vakgebieden"] = vakgebieden
    item["contacts"] = contacts
    item["_sections"] = {s["section_type"]: s["text"] for s in sections}
    return item
