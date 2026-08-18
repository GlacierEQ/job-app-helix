from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.target_opening_discovery import (
    TargetOpeningSource,
    execute_target_opening_discovery,
)


def _greenhouse_payload(description: str = "Build distributed AI systems") -> dict[str, object]:
    return {
        "jobs": [
            {
                "id": 101,
                "title": "Senior Software Engineer, AI Infrastructure",
                "absolute_url": "https://boards.example/jobs/101",
                "content": description,
                "location": {"name": "Remote - US"},
                "updated_at": "2026-08-19T00:00:00Z",
            },
            {
                "id": 102,
                "title": "Account Executive",
                "absolute_url": "https://boards.example/jobs/102",
                "content": "Sell enterprise software",
                "location": {"name": "New York, NY"},
            },
        ]
    }


def _lever_payload() -> list[dict[str, object]]:
    return [
        {
            "id": "lever-1",
            "text": "Staff Platform Engineer",
            "hostedUrl": "https://jobs.example/lever-1",
            "descriptionPlain": "Own reliable platform systems",
            "categories": {"location": "Remote"},
            "workplaceType": "remote",
        }
    ]


def test_discovers_filters_and_watches_greenhouse_inventory(tmp_path: Path) -> None:
    source = TargetOpeningSource(
        company="Example AI",
        provider="greenhouse",
        board_key="example",
        include_title_terms=("engineer",),
        include_locations=("remote",),
    )

    result = execute_target_opening_discovery(
        (source,),
        state_dir=tmp_path,
        transport=lambda _: _greenhouse_payload(),
    )

    assert result.opening_count == 1
    assert result.delta.added_urls == ("https://boards.example/jobs/101",)
    assert result.watch is not None
    assert result.watch.new_count == 1
    assert result.watch.failed_count == 0
    assert result.sources[0].openings[0].source == "greenhouse-api"
    assert result.sources[0].openings[0].company == "Example AI"
    assert (tmp_path / "TARGET_OPENING_INVENTORY.json").is_file()
    assert (tmp_path / "TARGET_OPENING_DISCOVERY_RECEIPT.json").is_file()


def test_retained_url_with_material_content_change_reuses_inventory_identity(tmp_path: Path) -> None:
    source = TargetOpeningSource(
        company="Example AI",
        provider="greenhouse",
        board_key="example",
        include_title_terms=("engineer",),
    )
    payloads = iter(
        (
            _greenhouse_payload("Build distributed AI systems"),
            _greenhouse_payload("Build distributed AI systems and inference control planes"),
        )
    )

    first = execute_target_opening_discovery(
        (source,),
        state_dir=tmp_path,
        transport=lambda _: next(payloads),
    )
    second = execute_target_opening_discovery(
        (source,),
        state_dir=tmp_path,
        transport=lambda _: next(payloads),
    )

    assert first.watch is not None and first.watch.new_count == 1
    assert second.delta.added_urls == ()
    assert second.delta.retained_urls == ("https://boards.example/jobs/101",)
    assert second.watch is not None
    assert second.watch.changed_count == 1
    assert second.watch.material_changed_count == 1
    assert second.watch.items[0].material_changed_fields == ("description",)


def test_removed_opening_is_reported_without_destroying_prior_watch_state(tmp_path: Path) -> None:
    source = TargetOpeningSource(
        company="Example AI",
        provider="greenhouse",
        board_key="example",
        include_title_terms=("engineer",),
    )
    execute_target_opening_discovery(
        (source,),
        state_dir=tmp_path,
        transport=lambda _: _greenhouse_payload(),
    )

    result = execute_target_opening_discovery(
        (source,),
        state_dir=tmp_path,
        transport=lambda _: {"jobs": []},
    )

    assert result.opening_count == 0
    assert result.delta.removed_urls == ("https://boards.example/jobs/101",)
    assert result.watch is None
    prior_watch_dirs = list((tmp_path / "opening-watch" / "openings").iterdir())
    assert len(prior_watch_dirs) == 1


def test_lever_source_normalizes_into_opening_watch(tmp_path: Path) -> None:
    source = TargetOpeningSource(
        company="Lever Company",
        provider="lever",
        board_key="lever-company",
        include_title_terms=("platform",),
    )

    result = execute_target_opening_discovery(
        (source,),
        state_dir=tmp_path,
        transport=lambda _: _lever_payload(),
    )

    assert result.opening_count == 1
    opening = result.sources[0].openings[0]
    assert opening.title == "Staff Platform Engineer"
    assert opening.location == "Remote"
    assert opening.source == "lever-api"
    assert result.watch is not None and result.watch.successful_count == 1


def test_source_failure_is_isolated_and_other_company_advances(tmp_path: Path) -> None:
    sources = (
        TargetOpeningSource(company="Broken", provider="greenhouse", board_key="broken"),
        TargetOpeningSource(company="Working", provider="lever", board_key="working"),
    )

    def transport(url: str):
        if "greenhouse" in url:
            raise RuntimeError("provider unavailable")
        return _lever_payload()

    result = execute_target_opening_discovery(
        sources,
        state_dir=tmp_path,
        transport=transport,
    )

    assert result.successful_source_count == 1
    assert result.failed_source_count == 1
    assert result.opening_count == 1
    assert result.sources[0].error == "RuntimeError: provider unavailable"
    assert result.watch is not None and result.watch.successful_count == 1


def test_duplicate_provider_board_identity_rejected_before_state_write(tmp_path: Path) -> None:
    sources = (
        TargetOpeningSource(company="One", provider="greenhouse", board_key="same"),
        TargetOpeningSource(company="Two", provider="greenhouse", board_key="same"),
    )

    with pytest.raises(ValueError, match="unique by provider/board_key"):
        execute_target_opening_discovery(sources, state_dir=tmp_path, transport=lambda _: {})

    assert not list(tmp_path.iterdir())


def test_manifest_contract_rejects_bad_provider(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"company": "Example", "provider": "unknown", "board_key": "example"}
                ]
            }
        ),
        encoding="utf-8",
    )

    from job_app_helix.target_opening_discovery import load_sources

    with pytest.raises(ValueError, match="unsupported target opening provider"):
        load_sources(manifest)
