from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.application_operations import ApplicationStore, CandidateProfile
from job_app_helix.company_intelligence_acquisition import FetchedSource, SourceSpec
from job_app_helix.intelligence_cycle import (
    IntelligenceCycleCandidate,
    execute_intelligence_cycle,
)


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="casey",
        name="Casey Barton",
        headline="AI systems engineer",
        summary=(
            "Builds reliable agent systems with observability, containment, recovery, "
            "and Python automation."
        ),
        skills=("Python", "agent systems", "observability", "containment", "distributed systems"),
        experience=("Built production agent orchestration and recovery systems",),
        achievements=("Designed evidence-bound automation with runtime verification",),
        source_digest="cycle-profile",
    )


def _write_opening(path: Path, opening_id: str = "anthropic-cycle") -> None:
    path.write_text(
        json.dumps(
            {
                "opening_id": opening_id,
                "company": "Anthropic",
                "title": "AI Systems Engineer",
                "description": (
                    "Build reliable agent systems with observability, containment, "
                    "recovery, and platform automation."
                ),
                "location": "Remote",
                "requirements": ["Python", "agent systems", "observability"],
                "preferred": ["distributed systems"],
            }
        ),
        encoding="utf-8",
    )


def _write_plan(path: Path, *, url: str = "https://www.anthropic.com/engineering/cycle") -> None:
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
                        "source_url": url,
                        "allowed_domains": ["anthropic.com"],
                        "include_patterns": ["agent systems|observability|containment"],
                        "extractor": "text",
                        "source_title": "Anthropic engineering",
                        "max_statements": 3,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _transport(statement: str):
    def fetch(spec: SourceSpec) -> FetchedSource:
        return FetchedSource(
            requested_url=spec.source_url,
            final_url=spec.source_url,
            status=200,
            content_type="text/plain; charset=utf-8",
            body=statement.encode("utf-8"),
            fetched_at="2026-08-18T11:45:00Z",
            etag='"cycle-v1"',
        )

    return fetch


def _candidate(
    tmp_path: Path,
    *,
    opening_id: str = "anthropic-cycle",
) -> IntelligenceCycleCandidate:
    opening = tmp_path / f"{opening_id}.json"
    plan = tmp_path / f"{opening_id}-plan.json"
    _write_opening(opening, opening_id)
    _write_plan(plan)
    return IntelligenceCycleCandidate(
        company="Anthropic",
        opening_path=opening,
        acquisition_plan_path=plan,
    )


def test_cycle_acquires_bootstraps_calibrates_and_compiles_packet(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    state = tmp_path / "state"
    packets = tmp_path / "packets"

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        result = execute_intelligence_cycle(
            (candidate,),
            _profile(),
            output_dir=packets,
            state_dir=state,
            store=store,
            transport=_transport(
                "Anthropic engineering builds reliable agent systems with observability "
                "and containment for production deployments."
            ),
        )

        assert result.schema == "glaciereq.job-intelligence-cycle.v1"
        assert result.successful_company_count == 1
        assert result.failed_company_count == 0
        assert result.companies[0].status == "INITIALIZED"
        assert result.companies[0].company_fit_score == 100.0
        assert result.calibration.status == "INSUFFICIENT_OUTCOMES"
        assert len(result.calibration_sha256) == 64
        assert result.batch.selected_count == 1
        assert result.batch.compiled_count == 1
        packet = Path(result.batch.packets[0].packet_dir)
        assert (packet / "RESUME.md").is_file()
        assert (packet / "COMPANY_FIT_ASSESSMENT.json").is_file()
        assert (packet / "PRIORITY_RECEIPT.json").is_file()
        priority = json.loads((packet / "PRIORITY_RECEIPT.json").read_text(encoding="utf-8"))
        assert priority["calibration_sha256"] == result.batch.calibration_sha256
        assert len(priority["receipt_sha256"]) == 64

    company_state = state / "companies" / "anthropic"
    assert (company_state / "ACTIVE_INTELLIGENCE.json").is_file()
    assert (company_state / "ACQUISITION_RECEIPT.json").is_file()
    assert (company_state / "REFRESH_RECEIPT.json").is_file()
    assert (company_state / "COMPANY_FIT.json").is_file()
    assert (state / "OUTCOME_CALIBRATION.json").is_file()
    assert (state / "INTELLIGENCE_CYCLE_RECEIPT.json").is_file()


def test_second_cycle_refreshes_and_retires_superseded_signal(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    state = tmp_path / "state"
    database = tmp_path / "applications.sqlite3"

    with ApplicationStore(database) as store:
        first = execute_intelligence_cycle(
            (candidate,),
            _profile(),
            output_dir=tmp_path / "packets",
            state_dir=state,
            store=store,
            transport=_transport(
                "Anthropic engineering builds agent systems with observability and containment."
            ),
        )
        assert first.companies[0].status == "INITIALIZED"

        second = execute_intelligence_cycle(
            (candidate,),
            _profile(),
            output_dir=tmp_path / "packets",
            state_dir=state,
            store=store,
            transport=_transport(
                "Anthropic engineering expands reliable agent systems with stronger observability "
                "and containment across production environments."
            ),
        )
        assert second.companies[0].status == "REFRESHED"
        assert second.batch.selected_count == 1

    history = state / "companies" / "anthropic" / "INTELLIGENCE_HISTORY.jsonl"
    rows = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["reason"] == "SUPERSEDED"
    assert rows[0]["replacement_fingerprint"]


def test_company_failure_is_isolated_while_other_candidate_compiles(tmp_path: Path) -> None:
    good = _candidate(tmp_path, opening_id="good")
    bad = _candidate(tmp_path, opening_id="bad")
    bad_plan = tmp_path / "bad-plan.json"
    _write_plan(bad_plan, url="https://www.anthropic.com/engineering/fail")
    bad = IntelligenceCycleCandidate(
        company=bad.company,
        opening_path=bad.opening_path,
        acquisition_plan_path=bad_plan,
    )

    def transport(spec: SourceSpec) -> FetchedSource:
        if spec.source_url.endswith("/fail"):
            raise RuntimeError("synthetic source outage")
        return _transport(
            "Anthropic engineering builds reliable agent systems with observability "
            "and containment."
        )(spec)

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        result = execute_intelligence_cycle(
            (bad, good),
            _profile(),
            output_dir=tmp_path / "packets",
            state_dir=tmp_path / "state",
            store=store,
            transport=transport,
        )

    assert result.candidate_count == 2
    assert result.successful_company_count == 1
    assert result.failed_company_count == 1
    failed = next(row for row in result.companies if row.status == "FAILED_ISOLATED")
    assert "synthetic source outage" in (failed.error or "")
    assert result.batch.selected_count == 1
    assert result.batch.compiled_count == 1


def test_cycle_fail_fast_preserves_error_for_callers(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)

    def broken(_: SourceSpec) -> FetchedSource:
        raise RuntimeError("source unavailable")

    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        try:
            execute_intelligence_cycle(
                (candidate,),
                _profile(),
                output_dir=tmp_path / "packets",
                state_dir=tmp_path / "state",
                store=store,
                transport=broken,
                continue_on_company_error=False,
            )
        except RuntimeError as exc:
            assert str(exc) == "source unavailable"
        else:
            raise AssertionError("fail-fast cycle should propagate company acquisition errors")
