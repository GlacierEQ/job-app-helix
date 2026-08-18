from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from job_app_helix.application_engine import CompanyTarget, RepositoryProof
from job_app_helix.application_operations import CandidateProfile, JobOpening
from job_app_helix.company_intelligence import CompanyIntelligence, CompanySignal
from job_app_helix.opportunity_queue import (
    build_application_execution_queue,
    score_queue_candidate,
)


NOW = datetime(2026, 8, 18, tzinfo=UTC)


def _proof() -> RepositoryProof:
    return RepositoryProof(
        repository="GlacierEQ/pro-code",
        level="L4",
        state="PROMOTED",
        visibility="public",
        admission="HELIX_ADMITTED",
        origin="test",
    )


def _target(company_id: str = "acme") -> CompanyTarget:
    return CompanyTarget(
        company_id=company_id,
        display_name="Acme",
        track_state="ACTIVE",
        target_roles=("AI Systems Engineer",),
        recruiter_thesis="agent systems reliability observability",
        gap_or_next_gate="none",
        non_affiliation="independent",
        repositories=(_proof(), _proof(), _proof()),
    )


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="casey",
        name="Casey",
        headline="AI systems engineer",
        summary="Builds reliable agent systems with observability and Python automation.",
        skills=("Python", "agent systems", "observability", "distributed systems"),
        experience=("Built production agent orchestration and recovery systems",),
        achievements=("Designed evidence-bound automation with runtime verification",),
        source_digest="profile-sha",
    )


def _opening(
    opening_id: str,
    *,
    requirements: tuple[str, ...],
    preferred: tuple[str, ...] = (),
) -> JobOpening:
    return JobOpening(
        opening_id=opening_id,
        company="Acme",
        title="AI Systems Engineer",
        description="Build reliable agent systems and platform automation.",
        location="Remote",
        source="test",
        source_url="https://example.com/jobs/ai",
        requirements=requirements,
        preferred=preferred,
        digest=f"digest-{opening_id}",
    )


def _intelligence(
    *,
    company_id: str = "acme",
    matched: bool = True,
    stale: bool = False,
) -> CompanyIntelligence:
    observed = NOW - (timedelta(days=90) if stale else timedelta(days=2))
    statement = (
        "Investing in reliable agent systems and observability"
        if matched
        else "Expanding compiler kernels and custom silicon design"
    )
    return CompanyIntelligence(
        schema="glaciereq.company-intelligence.v1",
        company_id=company_id,
        company="Acme",
        collected_at=NOW.isoformat(),
        max_age_days=30,
        signals=(
            CompanySignal(
                kind="engineering",
                statement=statement,
                source_url="https://example.com/company/update",
                observed_at=observed.isoformat(),
            ),
        ),
    )


def test_queue_puts_strong_fresh_company_aligned_opening_first() -> None:
    target = _target()
    profile = _profile()
    strong = _opening(
        "strong",
        requirements=("Python", "agent systems", "observability"),
        preferred=("distributed systems",),
    )
    viable = _opening(
        "viable",
        requirements=("Python", "agent systems", "Kubernetes"),
    )

    queue = build_application_execution_queue(
        (
            (viable, target, None, None),
            (strong, target, _intelligence(), None),
        ),
        profile,
        now=NOW,
    )

    assert queue.candidate_count == 2
    assert queue.items[0].opening_id == "strong"
    assert queue.items[0].lane == "APPLY_NOW"
    assert queue.items[0].company_fit_score == 100.0
    assert queue.items[0].company_freshness == 1.0
    assert queue.items[0].priority_score > queue.items[1].priority_score


def test_major_hard_gaps_cap_score_even_with_company_alignment() -> None:
    target = _target()
    profile = _profile()
    opening = _opening(
        "hard-gap",
        requirements=("Python", "CUDA", "ASIC design", "compiler kernels"),
    )

    score, opportunity, company_fit, reasons = score_queue_candidate(
        opening,
        target,
        profile,
        intelligence=_intelligence(),
        now=NOW,
    )

    assert opportunity.recommendation == "GAPS_TO_CLOSE"
    assert company_fit is not None and company_fit.score == 100.0
    assert score <= 45.0
    assert any(reason == "hard_gap_cap=45" for reason in reasons)


def test_stale_company_signal_contributes_no_freshness_or_fit() -> None:
    target = _target()
    profile = _profile()
    opening = _opening("stale", requirements=("Python", "agent systems"))

    score, opportunity, company_fit, reasons = score_queue_candidate(
        opening,
        target,
        profile,
        intelligence=_intelligence(stale=True),
        now=NOW,
    )

    assert opportunity.recommendation == "APPLY_PRIORITY"
    assert company_fit is not None
    assert company_fit.fresh_signal_count == 0
    assert company_fit.stale_signal_count == 1
    assert company_fit.score == 0.0
    assert "company_freshness=0%" in reasons
    assert score < opportunity.score


def test_wrong_company_intelligence_is_rejected() -> None:
    with pytest.raises(ValueError, match="does not match queue target"):
        score_queue_candidate(
            _opening("wrong-company", requirements=("Python",)),
            _target("acme"),
            _profile(),
            intelligence=_intelligence(company_id="other"),
            now=NOW,
        )
