from __future__ import annotations

from pathlib import Path

import pytest

from job_app_helix.smartrecruiters_opening_discovery import (
    SmartRecruitersOpeningSource,
    discover_smartrecruiters_openings,
)
from job_app_helix.target_opening_discovery import (
    TargetOpeningSource,
    execute_target_opening_discovery,
)


def _list_payload(*, include_sales: bool = True) -> dict[str, object]:
    content: list[dict[str, object]] = [
        {
            "id": "eng-1",
            "uuid": "uuid-eng-1",
            "name": "Staff AI Platform Engineer",
            "releasedDate": "2026-08-19T00:00:00Z",
            "location": {
                "city": "San Francisco",
                "region": "CA",
                "country": "US",
                "remote": True,
            },
        }
    ]
    if include_sales:
        content.append(
            {
                "id": "sales-1",
                "uuid": "uuid-sales-1",
                "name": "Enterprise Account Executive",
                "location": {"city": "New York", "region": "NY", "country": "US"},
            }
        )
    return {"totalFound": len(content), "content": content}


def _detail_payload(*, active: bool = True) -> dict[str, object]:
    return {
        "id": "eng-1",
        "uuid": "uuid-eng-1",
        "name": "Staff AI Platform Engineer",
        "active": active,
        "releasedDate": "2026-08-19T00:00:00Z",
        "postingUrl": "https://jobs.smartrecruiters.com/example/eng-1",
        "applyUrl": "https://jobs.smartrecruiters.com/example/eng-1/apply",
        "location": {
            "city": "San Francisco",
            "region": "CA",
            "country": "US",
            "remote": True,
        },
        "department": {"label": "Engineering"},
        "function": {"label": "Software Engineering"},
        "experienceLevel": {"label": "Mid-Senior Level"},
        "typeOfEmployment": {"label": "Full-time"},
        "jobAd": {
            "sections": {
                "jobDescription": {"text": "Build reliable distributed AI platforms."},
                "qualifications": {"text": "Python, systems design, production reliability."},
                "additionalInformation": {"text": "Own critical platform outcomes."},
            }
        },
    }


def test_discovers_detail_bound_opening_and_preserves_recruiter_metadata() -> None:
    calls: list[str] = []

    def transport(url: str):
        calls.append(url)
        if "?destination=PUBLIC" in url:
            return _list_payload()
        if url.endswith("/eng-1"):
            return _detail_payload()
        raise AssertionError(f"unexpected URL {url}")

    result = discover_smartrecruiters_openings(
        SmartRecruitersOpeningSource(
            company="Example AI",
            company_identifier="ExampleAI",
            include_title_terms=("engineer",),
            include_locations=("remote",),
        ),
        transport=transport,
    )

    assert len(result) == 1
    opening = result[0]
    assert opening.opening_id == "uuid-eng-1"
    assert opening.source == "smartrecruiters-api"
    assert opening.source_url == "https://jobs.smartrecruiters.com/example/eng-1"
    assert opening.location == "Remote | San Francisco, CA, US"
    assert opening.requirements == (
        "Python, systems design, production reliability.",
    )
    assert opening.metadata["apply_url"] == (
        "https://jobs.smartrecruiters.com/example/eng-1/apply"
    )
    assert opening.metadata["department"] == "Engineering"
    assert opening.metadata["function"] == "Software Engineering"
    assert opening.metadata["experience_level"] == "Mid-Senior Level"
    assert opening.metadata["employment_type"] == "Full-time"
    assert opening.metadata["remote"] is True
    assert not any(url.endswith("/sales-1") for url in calls)


def test_inactive_detail_is_not_promoted_to_live_inventory() -> None:
    def transport(url: str):
        if "?destination=PUBLIC" in url:
            return _list_payload(include_sales=False)
        return _detail_payload(active=False)

    result = discover_smartrecruiters_openings(
        SmartRecruitersOpeningSource(
            company="Example AI",
            company_identifier="ExampleAI",
        ),
        transport=transport,
    )

    assert result == ()


def test_paginates_using_total_found() -> None:
    first = {
        "totalFound": 2,
        "content": [
            {
                "id": "eng-1",
                "name": "Staff AI Platform Engineer",
                "location": {"country": "US"},
            }
        ],
    }
    second = {
        "totalFound": 2,
        "content": [
            {
                "id": "eng-2",
                "name": "Senior AI Platform Engineer",
                "location": {"country": "US"},
            }
        ],
    }

    def detail(posting_id: str) -> dict[str, object]:
        payload = _detail_payload()
        payload["id"] = posting_id
        payload["uuid"] = f"uuid-{posting_id}"
        payload["name"] = (
            "Staff AI Platform Engineer"
            if posting_id == "eng-1"
            else "Senior AI Platform Engineer"
        )
        payload["postingUrl"] = f"https://jobs.smartrecruiters.com/example/{posting_id}"
        return payload

    def transport(url: str):
        if "?destination=PUBLIC" in url and "offset=0" in url:
            return first
        if "?destination=PUBLIC" in url and "offset=1" in url:
            return second
        return detail(url.rsplit("/", 1)[-1])

    result = discover_smartrecruiters_openings(
        SmartRecruitersOpeningSource(
            company="Example AI",
            company_identifier="ExampleAI",
        ),
        transport=transport,
    )

    assert [opening.opening_id for opening in result] == ["uuid-eng-2", "uuid-eng-1"]


def test_unified_target_discovery_routes_smartrecruiters_into_opening_watch(
    tmp_path: Path,
) -> None:
    source = TargetOpeningSource(
        company="Example AI",
        provider="smartrecruiters",
        board_key="ExampleAI",
        include_title_terms=("engineer",),
    )

    def transport(url: str):
        if "?destination=PUBLIC" in url:
            return _list_payload(include_sales=False)
        return _detail_payload()

    result = execute_target_opening_discovery(
        (source,),
        state_dir=tmp_path,
        transport=transport,
    )

    assert result.opening_count == 1
    assert result.successful_source_count == 1
    assert result.sources[0].provider == "smartrecruiters"
    assert result.sources[0].openings[0].source == "smartrecruiters-api"
    assert result.watch is not None
    assert result.watch.new_count == 1
    assert result.watch.failed_count == 0


def test_smartrecruiters_failure_is_isolated_from_healthy_provider(tmp_path: Path) -> None:
    sources = (
        TargetOpeningSource(
            company="Broken SR",
            provider="smartrecruiters",
            board_key="BrokenCompany",
        ),
        TargetOpeningSource(
            company="Healthy Lever",
            provider="lever",
            board_key="healthy",
        ),
    )

    def transport(url: str):
        if "smartrecruiters" in url:
            raise RuntimeError("SmartRecruiters unavailable")
        return [
            {
                "id": "lever-1",
                "text": "Platform Engineer",
                "hostedUrl": "https://jobs.example/lever-1",
                "descriptionPlain": "Build reliable platforms",
                "categories": {"location": "Remote"},
            }
        ]

    result = execute_target_opening_discovery(
        sources,
        state_dir=tmp_path,
        transport=transport,
    )

    assert result.failed_source_count == 1
    assert result.successful_source_count == 1
    assert result.opening_count == 1
    assert result.sources[0].error == "RuntimeError: SmartRecruiters unavailable"
    assert result.watch is not None and result.watch.successful_count == 1


def test_missing_detail_job_ad_fails_closed() -> None:
    def transport(url: str):
        if "?destination=PUBLIC" in url:
            return _list_payload(include_sales=False)
        payload = _detail_payload()
        payload["jobAd"] = {"sections": {}}
        return payload

    with pytest.raises(ValueError, match="no job-ad content"):
        discover_smartrecruiters_openings(
            SmartRecruitersOpeningSource(
                company="Example AI",
                company_identifier="ExampleAI",
            ),
            transport=transport,
        )
