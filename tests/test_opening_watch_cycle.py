from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.application_operations import (
    ApplicationStore,
    CandidateProfile,
    JobOpening,
)
from job_app_helix.company_intelligence_acquisition import FetchedSource, SourceSpec
from job_app_helix.intelligence_cycle import IntelligenceCycleCandidate
from job_app_helix.opening_watch_cycle import execute_opening_watch_cycle


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="casey",
        name="Casey Barton",
        headline="AI systems engineer",
        summary="Builds reliable agent systems with observability and recovery.",
        skills=("Python", "agent systems", "observability", "distributed systems"),
        experience=("Built agent orchestration and recovery systems",),
        achievements=("Designed evidence-bound automation",),
        source_digest="watch-cycle-profile",
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
                        "source_url": "https://www.anthropic.com/engineering/watch-cycle",
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


def _transport(spec: SourceSpec) -> FetchedSource:
    return FetchedSource(
        requested_url=spec.source_url,
        final_url=spec.source_url,
        status=200,
        content_type="text/plain; charset=utf-8",
        body=b"Anthropic builds reliable agent systems with observability and containment.",
        fetched_at="2026-08-18T16:45:00Z",
        etag='"watch-cycle"',
    )


def _opening(url: str, title: str) -> JobOpening:
    return JobOpening(
        opening_id="anthropic-watch-live",
        company="Anthropic",
        title=title,
        description="Build reliable agent systems with observability and recovery.",
        location="Remote",
        requirements=("Python", "agent systems", "observability"),
        preferred=("distributed systems",),
        source="url",
        source_url=url,
        metadata={"source_kind": "job-posting"},
        digest=f"watch:{title}",
    )


def test_unchanged_opening_skips_expensive_cycle_and_uses_one_fetch_per_watch(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "plan.json"
    _write_plan(plan)
    url = "https://www.anthropic.com/careers/jobs/watch-cycle"
    candidate = IntelligenceCycleCandidate(
        company="Anthropic",
        acquisition_plan_path=plan,
        opening_url=url,
    )
    calls: list[str] = []

    def fetch(source: str) -> JobOpening:
        calls.append(source)
        return _opening(source, "AI Systems Engineer")

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        first = execute_opening_watch_cycle(
            (candidate,),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            opening_fetcher=fetch,
            transport=_transport,
        )
        second = execute_opening_watch_cycle(
            (candidate,),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            opening_fetcher=fetch,
            transport=_transport,
        )

    assert first.watch.new_count == 1
    assert first.selected_count == 1
    assert first.cycle is not None
    assert second.watch.unchanged_count == 1
    assert second.selected_count == 0
    assert second.unchanged_count == 1
    assert second.cycle is None
    assert calls == [url, url]


def test_changed_opening_runs_only_affected_cycle_and_quarantines_old_packet(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "plan.json"
    _write_plan(plan)
    url = "https://www.anthropic.com/careers/jobs/watch-cycle"
    candidate = IntelligenceCycleCandidate(
        company="Anthropic",
        acquisition_plan_path=plan,
        opening_url=url,
    )
    title = {"value": "AI Systems Engineer"}

    def fetch(source: str) -> JobOpening:
        return _opening(source, title["value"])

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        first = execute_opening_watch_cycle(
            (candidate,),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            opening_fetcher=fetch,
            transport=_transport,
        )
        title["value"] = "Senior AI Systems Engineer"
        changed = execute_opening_watch_cycle(
            (candidate,),
            _profile(),
            state_dir=tmp_path / "state",
            output_dir=tmp_path / "packets",
            store=store,
            opening_fetcher=fetch,
            transport=_transport,
        )

    assert first.cycle is not None
    assert changed.watch.changed_count == 1
    assert changed.selected_urls == (url,)
    assert changed.cycle is not None
    assert changed.cycle.companies[0].opening_status == "CHANGED"
    assert changed.cycle.freshness.refreshed_count == 1
    decision = changed.cycle.freshness.decisions[0]
    assert decision.action == "REFRESH_SUPERSEDED"
    assert decision.quarantine_path is not None
    assert Path(decision.quarantine_path).is_dir()
