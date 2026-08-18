from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.application_operations import ApplicationStore, CandidateProfile
from job_app_helix.company_intelligence_acquisition import FetchedSource, SourceSpec
from job_app_helix.target_intelligence_cycle import (
    TargetIntelligenceSource,
    execute_target_intelligence_cycle,
    load_target_intelligence_manifest,
)
from job_app_helix.target_opening_discovery import TargetOpeningSource


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="casey",
        name="Casey Barton",
        headline="AI systems engineer",
        summary="Builds reliable agent systems with observability and recovery.",
        skills=("Python", "agent systems", "observability", "distributed systems"),
        experience=("Built agent orchestration and recovery systems",),
        achievements=("Designed evidence-bound automation",),
        source_digest="target-cycle-profile",
    )


def _write_plan(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "glaciereq.company-intelligence-acquisition-plan.v1",
                "company_id": "anthropic",
                "company": "Anthropic",
                "max_age_days": 3650,
                "sources": [
                    {
                        "kind": "engineering",
                        "source_url": "https://www.anthropic.com/engineering/target-cycle",
                        "allowed_domains": ["anthropic.com"],
                        "include_patterns": ["agent systems|observability"],
                        "extractor": "text",
                        "source_title": "Anthropic engineering",
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
        body=b"Anthropic builds reliable agent systems with observability and containment.",
        fetched_at="2026-08-19T06:00:00Z",
        etag='"target-cycle"',
    )


def _greenhouse_payload(description: str) -> dict[str, object]:
    return {
        "jobs": [
            {
                "id": 4242,
                "title": "AI Systems Engineer",
                "absolute_url": "https://boards.example/anthropic/4242",
                "content": description,
                "location": {"name": "Remote - US"},
                "updated_at": "2026-08-19T06:00:00Z",
            }
        ]
    }


def _target(plan: Path) -> TargetIntelligenceSource:
    return TargetIntelligenceSource(
        discovery=TargetOpeningSource(
            company="Anthropic",
            provider="greenhouse",
            board_key="anthropic-test",
            include_title_terms=("engineer",),
        ),
        acquisition_plan_path=plan,
        role="Applied AI Engineer",
    )


def test_discovered_new_opening_runs_full_intelligence_and_packet_cycle(tmp_path: Path) -> None:
    plan = tmp_path / "anthropic-plan.json"
    _write_plan(plan)

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        result = execute_target_intelligence_cycle(
            (_target(plan),),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            discovery_transport=lambda _: _greenhouse_payload(
                "Build reliable agent systems with observability and recovery."
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
    assert result.watch_cycle.cycle.freshness.refreshed_count == 1
    assert (tmp_path / "state" / "TARGET_INTELLIGENCE_CYCLE_RECEIPT.json").is_file()
    assert list((tmp_path / "packets").glob("*/RECRUITER_PACKET.md"))


def test_unchanged_discovered_opening_stays_on_zero_full_cycle_path(tmp_path: Path) -> None:
    plan = tmp_path / "anthropic-plan.json"
    _write_plan(plan)
    payload = _greenhouse_payload("Build reliable agent systems with observability and recovery.")

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        first = execute_target_intelligence_cycle(
            (_target(plan),),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            discovery_transport=lambda _: payload,
            intelligence_transport=_intelligence_transport,
        )
        second = execute_target_intelligence_cycle(
            (_target(plan),),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            discovery_transport=lambda _: payload,
            intelligence_transport=_intelligence_transport,
        )

    assert first.watch_cycle is not None and first.watch_cycle.cycle is not None
    assert second.discovery.delta.retained_urls == ("https://boards.example/anthropic/4242",)
    assert second.watch_cycle is not None
    assert second.watch_cycle.unchanged_count == 1
    assert second.watch_cycle.selected_count == 0
    assert second.watch_cycle.cycle is None


def test_material_discovered_change_refreshes_only_affected_packet_lineage(tmp_path: Path) -> None:
    plan = tmp_path / "anthropic-plan.json"
    _write_plan(plan)
    description = {"value": "Build reliable agent systems with observability and recovery."}

    def discovery_transport(_: str) -> dict[str, object]:
        return _greenhouse_payload(description["value"])

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        execute_target_intelligence_cycle(
            (_target(plan),),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            discovery_transport=discovery_transport,
            intelligence_transport=_intelligence_transport,
        )
        description["value"] = (
            "Build reliable agent systems with observability, recovery, "
            "and inference control planes."
        )
        changed = execute_target_intelligence_cycle(
            (_target(plan),),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            discovery_transport=discovery_transport,
            intelligence_transport=_intelligence_transport,
        )

    assert changed.watch_cycle is not None
    assert changed.watch_cycle.watch.material_changed_count == 1
    assert changed.watch_cycle.selected_count == 1
    assert changed.watch_cycle.cycle is not None
    assert changed.watch_cycle.cycle.freshness.refreshed_count == 1
    decision = changed.watch_cycle.cycle.freshness.decisions[0]
    assert decision.action == "REFRESH_SUPERSEDED"
    assert decision.quarantine_path is not None
    assert Path(decision.quarantine_path).is_dir()


def test_manifest_requires_company_intelligence_plan_before_execution(tmp_path: Path) -> None:
    manifest = tmp_path / "targets.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "company": "Anthropic",
                        "provider": "greenhouse",
                        "board_key": "anthropic",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires acquisition_plan"):
        load_target_intelligence_manifest(manifest)
