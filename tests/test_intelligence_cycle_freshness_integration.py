from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.application_operations import ApplicationStore, CandidateProfile, JobOpening
from job_app_helix.company_intelligence_acquisition import FetchedSource, SourceSpec
from job_app_helix.intelligence_cycle import IntelligenceCycleCandidate, execute_intelligence_cycle


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="casey",
        name="Casey Barton",
        headline="AI systems engineer",
        summary="Builds reliable agent systems with observability and recovery.",
        skills=("Python", "agent systems", "observability", "distributed systems"),
        experience=("Built agent orchestration and recovery systems",),
        achievements=("Designed evidence-bound automation",),
        source_digest="fresh-cycle-profile",
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
                        "source_url": "https://www.anthropic.com/engineering/fresh-cycle",
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
        fetched_at="2026-08-18T16:40:00Z",
        etag='"fresh-cycle"',
    )


def _opening(url: str, *, title: str) -> JobOpening:
    return JobOpening(
        opening_id="anthropic-live-freshness",
        company="Anthropic",
        title=title,
        description="Build reliable agent systems with observability and recovery.",
        location="Remote",
        requirements=("Python", "agent systems", "observability"),
        preferred=("distributed systems",),
        source="url",
        source_url=url,
        metadata={"source_kind": "job-posting"},
        digest=f"freshness:{title}",
    )


def test_cycle_writes_opening_input_receipt_and_reuses_unchanged_packet(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "plan.json"
    _write_plan(plan)
    url = "https://www.anthropic.com/careers/jobs/freshness"
    candidate = IntelligenceCycleCandidate(
        company="Anthropic",
        acquisition_plan_path=plan,
        opening_url=url,
    )
    packets = tmp_path / "packets"
    state = tmp_path / "state"

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        first = execute_intelligence_cycle(
            (candidate,),
            _profile(),
            output_dir=packets,
            state_dir=state,
            store=store,
            opening_fetcher=lambda source: _opening(source, title="AI Systems Engineer"),
            transport=_transport,
        )
        second = execute_intelligence_cycle(
            (candidate,),
            _profile(),
            output_dir=packets,
            state_dir=state,
            store=store,
            opening_fetcher=lambda source: _opening(source, title="AI Systems Engineer"),
            transport=_transport,
        )

    assert first.schema == "glaciereq.job-intelligence-cycle.v3"
    assert first.freshness.refreshed_count == 0
    assert second.companies[0].opening_status == "UNCHANGED"
    assert second.freshness.reused_count == 1
    packet = Path(second.batch.packets[0].packet_dir)
    receipt = json.loads((packet / "OPENING_INPUT_RECEIPT.json").read_text())
    assert receipt["opening_id"] == "anthropic-live-freshness"
    assert receipt["opening_digest"] == "freshness:AI Systems Engineer"


def test_cycle_changed_opening_quarantines_superseded_packet_lineage(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    _write_plan(plan)
    url = "https://www.anthropic.com/careers/jobs/freshness"
    candidate = IntelligenceCycleCandidate(
        company="Anthropic",
        acquisition_plan_path=plan,
        opening_url=url,
    )
    packets = tmp_path / "packets"
    state = tmp_path / "state"

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        first = execute_intelligence_cycle(
            (candidate,),
            _profile(),
            output_dir=packets,
            state_dir=state,
            store=store,
            opening_fetcher=lambda source: _opening(source, title="AI Systems Engineer"),
            transport=_transport,
        )
        second = execute_intelligence_cycle(
            (candidate,),
            _profile(),
            output_dir=packets,
            state_dir=state,
            store=store,
            opening_fetcher=lambda source: _opening(source, title="Senior AI Systems Engineer"),
            transport=_transport,
        )

    assert second.companies[0].opening_status == "CHANGED"
    assert second.freshness.refreshed_count == 1
    decision = second.freshness.decisions[0]
    assert decision.action == "REFRESH_SUPERSEDED"
    assert decision.quarantine_path is not None
    stale = Path(decision.quarantine_path)
    assert stale.is_dir()
    assert (stale / "OPENING_INPUT_RECEIPT.json").is_file()
    fresh = Path(second.batch.packets[0].packet_dir)
    assert fresh != Path(first.batch.packets[0].packet_dir)
    assert (fresh / "OPENING_INPUT_RECEIPT.json").is_file()
