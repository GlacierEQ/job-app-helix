from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.application_operations import ApplicationStore, CandidateProfile
from job_app_helix.company_intelligence_acquisition import FetchedSource, SourceSpec
from job_app_helix.target_intelligence_cycle import (
    TargetIntelligenceSource,
    execute_target_intelligence_cycle,
)
from job_app_helix.target_opening_discovery import (
    TargetOpeningSource,
    execute_target_opening_discovery,
)


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="unified-ashby",
        name="Casey Barton",
        headline="AI systems engineer",
        summary="Builds reliable agent systems with observability and recovery.",
        skills=("Python", "agent systems", "observability", "distributed systems"),
        experience=("Built agent orchestration and recovery systems",),
        achievements=("Designed evidence-bound automation",),
        source_digest="unified-ashby-profile",
    )


def _write_plan(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "glaciereq.company-intelligence-acquisition-plan.v1",
                "company_id": "example-ai",
                "company": "Example AI",
                "max_age_days": 3650,
                "sources": [
                    {
                        "kind": "engineering",
                        "source_url": "https://example.ai/engineering/platform",
                        "allowed_domains": ["example.ai"],
                        "include_patterns": ["agent systems|observability"],
                        "extractor": "text",
                        "source_title": "Example AI engineering",
                        "max_statements": 3,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _intelligence_transport(spec: SourceSpec) -> FetchedSource:
    return FetchedSource(
        requested_url=spec.source_url,
        final_url=spec.source_url,
        status=200,
        content_type="text/plain; charset=utf-8",
        body=b"Example AI builds reliable agent systems with observability and containment.",
        fetched_at="2026-08-19T00:00:00Z",
        etag='"unified-ashby"',
    )


def _ashby_payload(description: str = "Build reliable distributed agent systems") -> dict[str, object]:
    return {
        "apiVersion": "1",
        "jobs": [
            {
                "title": "Staff AI Platform Engineer",
                "location": "Remote - US",
                "jobUrl": "https://jobs.ashbyhq.com/example/abc123",
                "applyUrl": "https://jobs.ashbyhq.com/example/abc123/application",
                "descriptionPlain": description,
                "publishedAt": "2026-08-18T20:00:00Z",
                "employmentType": "FullTime",
                "workplaceType": "Remote",
                "isRemote": True,
                "department": "Engineering",
                "team": "AI Platform",
                "secondaryLocations": [{"location": "Honolulu, HI"}],
                "compensation": {
                    "compensationTierSummary": "$190k - $250k",
                },
                "isListed": True,
            },
            {
                "title": "Hidden Engineer",
                "location": "Remote",
                "jobUrl": "https://jobs.ashbyhq.com/example/hidden",
                "descriptionPlain": "Must never enter the maintained live inventory",
                "isListed": False,
            },
        ],
    }


def _ashby_target(plan: Path) -> TargetIntelligenceSource:
    return TargetIntelligenceSource(
        discovery=TargetOpeningSource(
            company="Example AI",
            provider="ashby",
            board_key="example",
            include_title_terms=("platform",),
            include_locations=("remote",),
        ),
        acquisition_plan_path=plan,
        role="Staff AI Platform Engineer",
    )


def test_unified_discovery_preserves_ashby_recruiter_metadata_and_watch(tmp_path: Path) -> None:
    result = execute_target_opening_discovery(
        (_ashby_target(tmp_path / "unused.json").discovery,),
        state_dir=tmp_path / "state",
        transport=lambda _: _ashby_payload(),
    )

    assert result.schema == "glaciereq.target-opening-discovery.v2"
    assert result.opening_count == 1
    assert result.sources[0].provider == "ashby"
    opening = result.sources[0].openings[0]
    assert opening.source == "ashby-public-api"
    assert opening.metadata["apply_url"].endswith("/application")
    assert opening.metadata["compensation_summary"] == "$190k - $250k"
    assert opening.metadata["secondary_locations"] == ["Honolulu, HI"]
    assert result.watch is not None and result.watch.new_count == 1


def test_ashby_runs_through_unified_target_intelligence_packet_cycle(tmp_path: Path) -> None:
    plan = tmp_path / "example-plan.json"
    _write_plan(plan)

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        result = execute_target_intelligence_cycle(
            (_ashby_target(plan),),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            discovery_transport=lambda _: _ashby_payload(
                "Build reliable distributed agent systems with observability and recovery."
            ),
            intelligence_transport=_intelligence_transport,
        )

    assert result.discovery.opening_count == 1
    assert result.candidate_count == 1
    assert result.watch_cycle is not None
    assert result.watch_cycle.selected_count == 1
    assert result.watch_cycle.cycle is not None
    assert result.watch_cycle.cycle.successful_company_count == 1
    assert result.watch_cycle.cycle.batch.selected_count == 1
    packet = result.watch_cycle.cycle.batch.packets[0]
    packet_dir = Path(packet.packet_dir)
    assert packet_dir.is_dir()
    assert (packet_dir / "OPENING_INPUT_RECEIPT.json").is_file()
    assert (tmp_path / "state" / "TARGET_INTELLIGENCE_CYCLE_RECEIPT.json").is_file()


def test_mixed_provider_failure_isolation_keeps_ashby_live(tmp_path: Path) -> None:
    sources = (
        TargetOpeningSource(company="Broken", provider="greenhouse", board_key="broken"),
        TargetOpeningSource(company="Example AI", provider="ashby", board_key="example"),
    )

    def transport(url: str):
        if "greenhouse" in url:
            raise RuntimeError("greenhouse unavailable")
        return _ashby_payload()

    result = execute_target_opening_discovery(
        sources,
        state_dir=tmp_path,
        transport=transport,
    )

    assert result.successful_source_count == 1
    assert result.failed_source_count == 1
    assert result.opening_count == 1
    assert result.sources[0].error == "RuntimeError: greenhouse unavailable"
    assert result.sources[1].provider == "ashby"
    assert result.watch is not None and result.watch.successful_count == 1
