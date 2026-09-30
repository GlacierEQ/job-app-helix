from __future__ import annotations

from pathlib import Path

import pytest

from job_app_helix.ashby_opening_discovery import (
    AshbyOpeningSource,
    discover_ashby_openings,
    execute_ashby_opening_discovery,
)


def _ashby_payload(description: str = "Build production AI infrastructure") -> dict[str, object]:
    return {
        "apiVersion": "1",
        "jobs": [
            {
                "title": "Senior Software Engineer, AI Infrastructure",
                "location": "Remote - US",
                "secondaryLocations": [{"location": "Honolulu, HI"}],
                "department": "Engineering",
                "team": "AI Platform",
                "isListed": True,
                "isRemote": True,
                "workplaceType": "Remote",
                "descriptionPlain": description,
                "publishedAt": "2026-08-19T00:00:00Z",
                "employmentType": "FullTime",
                "jobUrl": "https://jobs.ashbyhq.com/example/ai-infra",
                "applyUrl": "https://jobs.ashbyhq.com/example/ai-infra/application",
                "compensation": {
                    "compensationTierSummary": "$180K - $240K",
                    "scrapeableCompensationSalarySummary": "$180K - $240K",
                },
            },
            {
                "title": "Account Executive",
                "location": "New York, NY",
                "isListed": True,
                "descriptionPlain": "Sell enterprise software",
                "jobUrl": "https://jobs.ashbyhq.com/example/ae",
                "applyUrl": "https://jobs.ashbyhq.com/example/ae/application",
            },
            {
                "title": "Principal Hidden Engineer",
                "location": "Remote - US",
                "isListed": False,
                "descriptionPlain": "Unlisted role",
                "jobUrl": "https://jobs.ashbyhq.com/example/hidden",
                "applyUrl": "https://jobs.ashbyhq.com/example/hidden/application",
            },
        ],
    }


def test_discovers_listed_filtered_ashby_opening_with_provider_metadata() -> None:
    source = AshbyOpeningSource(
        company="Example AI",
        board_key="example",
        include_title_terms=("engineer",),
        include_locations=("remote",),
    )

    openings = discover_ashby_openings(source, transport=lambda _: _ashby_payload())

    assert len(openings) == 1
    opening = openings[0]
    assert opening.company == "Example AI"
    assert opening.title == "Senior Software Engineer, AI Infrastructure"
    assert opening.location == "Remote - US"
    assert opening.source == "ashby-public-api"
    assert opening.source_url == "https://jobs.ashbyhq.com/example/ai-infra"
    assert opening.metadata["provider"] == "ashby"
    assert opening.metadata["apply_url"].endswith("/application")
    assert opening.metadata["secondary_locations"] == ["Honolulu, HI"]
    assert opening.metadata["compensation_summary"] == "$180K - $240K"


def test_ashby_discovery_composes_into_field_sensitive_opening_watch(tmp_path: Path) -> None:
    source = AshbyOpeningSource(
        company="Example AI",
        board_key="example",
        include_title_terms=("engineer",),
    )
    payloads = iter(
        (
            _ashby_payload("Build production AI infrastructure"),
            _ashby_payload("Build production AI infrastructure and inference control planes"),
        )
    )

    first = execute_ashby_opening_discovery(
        (source,), state_dir=tmp_path, transport=lambda _: next(payloads)
    )
    second = execute_ashby_opening_discovery(
        (source,), state_dir=tmp_path, transport=lambda _: next(payloads)
    )

    assert first.watch is not None and first.watch.new_count == 1
    assert second.watch is not None and second.watch.changed_count == 1
    assert second.watch.material_changed_count == 1
    assert second.watch.items[0].material_changed_fields == ("description",)
    assert (tmp_path / "ASHBY_OPENING_DISCOVERY_RECEIPT.json").is_file()


def test_ashby_board_failure_is_isolated_and_healthy_board_advances(tmp_path: Path) -> None:
    sources = (
        AshbyOpeningSource(company="Broken", board_key="broken"),
        AshbyOpeningSource(
            company="Working",
            board_key="working",
            include_title_terms=("engineer",),
        ),
    )

    def transport(url: str):
        if "/broken?" in url:
            raise RuntimeError("board unavailable")
        return _ashby_payload()

    result = execute_ashby_opening_discovery(sources, state_dir=tmp_path, transport=transport)

    assert result.successful_source_count == 1
    assert result.failed_source_count == 1
    assert result.opening_count == 1
    assert result.sources[0].error == "RuntimeError: board unavailable"
    assert result.watch is not None and result.watch.successful_count == 1


def test_duplicate_ashby_board_rejected_before_state_write(tmp_path: Path) -> None:
    sources = (
        AshbyOpeningSource(company="One", board_key="same"),
        AshbyOpeningSource(company="Two", board_key="same"),
    )

    with pytest.raises(ValueError, match="unique by board_key"):
        execute_ashby_opening_discovery(sources, state_dir=tmp_path, transport=lambda _: {})

    assert not list(tmp_path.iterdir())


def test_unknown_ashby_public_api_version_fails_closed() -> None:
    source = AshbyOpeningSource(company="Example", board_key="example")

    with pytest.raises(ValueError, match="unsupported Ashby posting API version"):
        discover_ashby_openings(
            source,
            transport=lambda _: {"apiVersion": "2", "jobs": []},
        )
