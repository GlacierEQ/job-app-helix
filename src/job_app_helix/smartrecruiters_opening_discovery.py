"""Discover public SmartRecruiters postings and normalize them into Helix openings.

SmartRecruiters exposes active public postings by company identifier. The list endpoint
provides inventory identity while the detail endpoint carries recruiter-relevant job-ad
content and apply URLs. This runtime deliberately binds each normalized opening to the
posting detail response so downstream materiality checks react to real job-ad changes,
not only list metadata.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from .application_operations import JobOpening, ingest_job_opening

JsonTransport = Callable[[str], Any]


@dataclass(frozen=True)
class SmartRecruitersOpeningSource:
    company: str
    company_identifier: str
    include_title_terms: tuple[str, ...] = ()
    exclude_title_terms: tuple[str, ...] = ()
    include_locations: tuple[str, ...] = ()
    max_openings: int | None = None

    def __post_init__(self) -> None:
        if not self.company.strip():
            raise ValueError("SmartRecruiters source requires company")
        if not self.company_identifier.strip():
            raise ValueError("SmartRecruiters source requires company_identifier")
        if self.max_openings is not None and self.max_openings <= 0:
            raise ValueError("max_openings must be positive when supplied")


def _text(value: object) -> str:
    return str(value or "").strip()


def _label(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    label = _text(value.get("label"))
    return label or None


def _location(value: object) -> str:
    if not isinstance(value, Mapping):
        return _text(value)
    parts = [_text(value.get(key)) for key in ("city", "region", "country")]
    location = ", ".join(part for part in parts if part)
    if bool(value.get("remote")):
        return f"Remote | {location}" if location else "Remote"
    return location


def _section_text(sections: object, name: str) -> str:
    if not isinstance(sections, Mapping):
        return ""
    section = sections.get(name)
    if isinstance(section, Mapping):
        return _text(section.get("text"))
    return _text(section)


def _job_ad_sections(detail: Mapping[str, Any]) -> Mapping[str, Any]:
    job_ad = detail.get("jobAd")
    if not isinstance(job_ad, Mapping):
        return {}
    sections = job_ad.get("sections")
    return sections if isinstance(sections, Mapping) else job_ad


def _matches(source: SmartRecruitersOpeningSource, title: str, location: str) -> bool:
    normalized_title = title.casefold()
    normalized_location = location.casefold()
    if source.include_title_terms and not any(
        term.casefold() in normalized_title for term in source.include_title_terms
    ):
        return False
    if any(term.casefold() in normalized_title for term in source.exclude_title_terms):
        return False
    return not source.include_locations or any(
        term.casefold() in normalized_location for term in source.include_locations
    )


def _list_url(company_identifier: str, *, offset: int) -> str:
    identifier = quote(company_identifier.strip(), safe="")
    return (
        f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings"
        f"?destination=PUBLIC&limit=100&offset={offset}"
    )


def _detail_url(company_identifier: str, posting_id: str) -> str:
    identifier = quote(company_identifier.strip(), safe="")
    posting = quote(posting_id.strip(), safe="")
    return f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings/{posting}"


def _posting_rows(
    source: SmartRecruitersOpeningSource,
    transport: JsonTransport,
) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    offset = 0
    while True:
        payload = transport(_list_url(source.company_identifier, offset=offset))
        if not isinstance(payload, Mapping):
            raise ValueError("SmartRecruiters postings response must be an object")
        content = payload.get("content")
        if not isinstance(content, list):
            raise ValueError("SmartRecruiters postings response requires content list")
        page = tuple(row for row in content if isinstance(row, Mapping))
        rows.extend(page)
        total = payload.get("totalFound")
        if not isinstance(total, int) or total < 0:
            raise ValueError("SmartRecruiters postings response requires totalFound integer")
        offset += len(content)
        if offset >= total or not content:
            break
    return tuple(rows)


def discover_smartrecruiters_openings(
    source: SmartRecruitersOpeningSource,
    *,
    transport: JsonTransport,
) -> tuple[JobOpening, ...]:
    """Discover filtered public postings with exact detail-level recruiter metadata."""
    openings: list[JobOpening] = []
    for summary in _posting_rows(source, transport):
        title = _text(summary.get("name"))
        location = _location(summary.get("location"))
        if not title or not _matches(source, title, location):
            continue

        posting_id = _text(summary.get("id") or summary.get("uuid"))
        if not posting_id:
            raise ValueError("SmartRecruiters posting is missing id/uuid")
        detail = transport(_detail_url(source.company_identifier, posting_id))
        if not isinstance(detail, Mapping):
            raise ValueError(f"SmartRecruiters posting detail must be an object: {posting_id}")
        if detail.get("active") is False:
            continue

        detail_title = _text(detail.get("name")) or title
        detail_location = _location(detail.get("location")) or location
        if not _matches(source, detail_title, detail_location):
            continue
        sections = _job_ad_sections(detail)
        job_description = _section_text(sections, "jobDescription")
        qualifications = _section_text(sections, "qualifications")
        additional = _section_text(sections, "additionalInformation")
        description = "\n\n".join(
            part for part in (job_description, qualifications, additional) if part
        ).strip()
        if not description:
            raise ValueError(f"SmartRecruiters posting has no job-ad content: {posting_id}")

        posting_url = _text(detail.get("postingUrl") or summary.get("postingUrl"))
        apply_url = _text(detail.get("applyUrl"))
        source_url = posting_url or apply_url
        if not source_url:
            raise ValueError(f"SmartRecruiters posting has no public URL: {posting_id}")

        requirements = (qualifications,) if qualifications else ()
        openings.append(
            ingest_job_opening(
                {
                    "id": _text(detail.get("uuid") or detail.get("id") or posting_id),
                    "company": source.company,
                    "title": detail_title,
                    "description": description,
                    "location": detail_location,
                    "requirements": requirements,
                    "metadata": {
                        "provider": "smartrecruiters",
                        "company_identifier": source.company_identifier,
                        "provider_id": _text(detail.get("id") or posting_id),
                        "provider_uuid": _text(detail.get("uuid")) or None,
                        "apply_url": apply_url or None,
                        "released_date": detail.get("releasedDate") or summary.get("releasedDate"),
                        "department": _label(detail.get("department")),
                        "function": _label(detail.get("function")),
                        "experience_level": _label(detail.get("experienceLevel")),
                        "employment_type": _label(detail.get("typeOfEmployment")),
                        "remote": (
                            bool(detail["location"].get("remote"))
                            if isinstance(detail.get("location"), Mapping)
                            else None
                        ),
                    },
                },
                source="smartrecruiters-api",
                source_url=source_url,
            )
        )
        if source.max_openings is not None and len(openings) >= source.max_openings:
            break

    return tuple(
        sorted(openings, key=lambda row: (row.title.casefold(), row.source_url or ""))
    )
