"""Requirement- and company-aware application strategy over the Helix lifecycle.

The strategy layer composes opportunity intelligence with recruiter projection so
explicit hiring requirements and fresh company direction influence what recruiters
see. Candidate claims remain bounded to supplied profile evidence and admitted
public proof; company signals never become candidate claims by themselves.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from .application_engine import ApplicationKit, CompanyTarget, find_target, load_targets
from .application_operations import (
    ApplicationAdapter,
    ApplicationStore,
    CandidateProfile,
    JobOpening,
    ManualApplicationAdapter,
    MatchResult,
    Projection,
    _reference_digest,
    _tokens,
    load_candidate_profile,
    load_job_opening,
    project_application,
    write_projection,
)
from .company_fit import (
    CompanyFitAssessment,
    assess_company_fit,
    best_company_evidence,
)
from .company_intelligence import CompanyIntelligence, load_company_intelligence
from .opportunity_intelligence import OpportunityAssessment, assess_opportunity


def _evidence_candidates(profile: CandidateProfile) -> tuple[str, ...]:
    return (*profile.skills, *profile.experience, *profile.achievements)


def _best_candidate_evidence(signal: str, profile: CandidateProfile) -> str | None:
    signal_tokens = _tokens(signal)
    if not signal_tokens:
        return None
    ranked: list[tuple[float, int, str]] = []
    for evidence in _evidence_candidates(profile):
        evidence_tokens = _tokens(evidence)
        overlap = len(signal_tokens & evidence_tokens) / len(signal_tokens)
        if overlap >= 0.5:
            ranked.append((overlap, len(signal_tokens & evidence_tokens), evidence))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (row[0], row[1], -len(row[2])), reverse=True)
    return ranked[0][2]


def _alignment_rows(
    assessment: OpportunityAssessment,
    profile: CandidateProfile,
) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for signal in (*assessment.matched_requirements, *assessment.matched_preferred):
        evidence = _best_candidate_evidence(signal, profile)
        if evidence is not None:
            rows.append((signal, evidence))
    return tuple(rows)


def _company_alignment_rows(
    assessment: CompanyFitAssessment,
    profile: CandidateProfile,
) -> tuple[tuple[str, str], ...]:
    """Map only admitted company signals to the exact evidence matcher that admitted them."""
    rows: list[tuple[str, str]] = []
    for signal in assessment.matched_signals:
        alignment, evidence = best_company_evidence(signal, profile)
        if alignment >= 0.45 and evidence is not None:
            rows.append((signal, evidence))
    return tuple(rows)


def _strategy_section(rows: tuple[tuple[str, str], ...]) -> str:
    if not rows:
        return ""
    bullets = "\n".join(f"- **{signal}:** {evidence}" for signal, evidence in rows)
    return "## Role-aligned evidence\n\n" + bullets


def _company_strategy_section(rows: tuple[tuple[str, str], ...]) -> str:
    if not rows:
        return ""
    bullets = "\n".join(f"- **{signal}:** {evidence}" for signal, evidence in rows)
    return "## Current company-direction alignment\n\n" + bullets


def _inject_before_truth_boundary(markdown: str, section: str) -> str:
    if not section:
        return markdown
    marker = "\n\n## Truth boundary"
    if marker in markdown:
        return markdown.replace(marker, f"\n\n{section}{marker}", 1)
    return markdown.rstrip() + "\n\n" + section + "\n"


def _augment_cover_letter(
    markdown: str,
    rows: tuple[tuple[str, str], ...],
    assessment: OpportunityAssessment,
) -> str:
    if not rows:
        return markdown
    strongest = rows[:4]
    evidence = "; ".join(f"{signal}: {value}" for signal, value in strongest)
    paragraph = (
        "Against the role's explicit qualifications, the strongest supplied evidence is "
        f"{evidence}. This mapping is based only on the candidate profile supplied to Helix."
    )
    truth_marker = "\n\nTruth boundary:"
    status = (
        "\n\nApplication priority assessment: "
        f"{assessment.recommendation} ({assessment.score:.1f}/100)."
    )
    if truth_marker in markdown:
        return markdown.replace(truth_marker, f"\n\n{paragraph}{status}{truth_marker}", 1)
    return markdown.rstrip() + f"\n\n{paragraph}{status}\n"


def _augment_company_cover_letter(
    markdown: str,
    rows: tuple[tuple[str, str], ...],
    assessment: CompanyFitAssessment,
) -> str:
    if not rows:
        return markdown
    strongest = rows[:3]
    evidence = "; ".join(f"{signal}: {value}" for signal, value in strongest)
    paragraph = (
        "Current company direction also intersects with supplied experience: "
        f"{evidence}. Company-direction fit is {assessment.score:.1f}/100 across "
        f"{assessment.fresh_signal_count} fresh sourced signals."
    )
    truth_marker = "\n\nTruth boundary:"
    if truth_marker in markdown:
        return markdown.replace(truth_marker, f"\n\n{paragraph}{truth_marker}", 1)
    return markdown.rstrip() + f"\n\n{paragraph}\n"


def _augment_outreach(
    markdown: str,
    rows: tuple[tuple[str, str], ...],
) -> str:
    if not rows:
        return markdown
    strongest = rows[:2]
    evidence = "; ".join(f"{signal} → {value}" for signal, value in strongest)
    paragraphs = markdown.rstrip().split("\n\n")
    insert_at = max(1, len(paragraphs) - 1)
    paragraphs.insert(insert_at, f"Explicit-role evidence: {evidence}.")
    return "\n\n".join(paragraphs).rstrip() + "\n"


def _augment_company_outreach(
    markdown: str,
    rows: tuple[tuple[str, str], ...],
) -> str:
    if not rows:
        return markdown
    strongest = rows[:1]
    evidence = "; ".join(f"{signal} → {value}" for signal, value in strongest)
    paragraphs = markdown.rstrip().split("\n\n")
    insert_at = max(1, len(paragraphs) - 1)
    paragraphs.insert(insert_at, f"Current-company alignment: {evidence}.")
    return "\n\n".join(paragraphs).rstrip() + "\n"


def project_requirement_aware_application(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    *,
    role: str | None = None,
) -> tuple[ApplicationKit, MatchResult, OpportunityAssessment, Projection]:
    """Project recruiter-facing material using requirement-level evidence alignment."""
    kit, match, base_projection = project_application(
        opening,
        target,
        profile,
        role=role,
    )
    assessment = assess_opportunity(
        opening,
        target,
        profile,
        mapped_role=kit.role,
    )
    rows = _alignment_rows(assessment, profile)
    section = _strategy_section(rows)
    resume = _inject_before_truth_boundary(base_projection.resume_markdown, section)
    cover = _augment_cover_letter(base_projection.cover_letter_markdown, rows, assessment)
    outreach = _augment_outreach(base_projection.outreach_markdown, rows)
    claim_sources = tuple(
        dict.fromkeys(
            (
                *base_projection.claim_sources,
                f"job-opening:{opening.digest}",
            )
        )
    )
    body = {
        "base_projection": base_projection.digest,
        "opportunity": assessment.as_dict(),
        "alignment_rows": rows,
        "resume": resume,
        "cover": cover,
        "outreach": outreach,
        "claim_sources": claim_sources,
    }
    digest = _reference_digest(body)
    projection = replace(
        base_projection,
        application_id=f"app-{digest[:16]}",
        resume_markdown=resume,
        cover_letter_markdown=cover,
        outreach_markdown=outreach,
        claim_sources=claim_sources,
        digest=digest,
    )
    return kit, match, assessment, projection


def project_company_aware_application(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    intelligence: CompanyIntelligence,
    *,
    role: str | None = None,
) -> tuple[
    ApplicationKit,
    MatchResult,
    OpportunityAssessment,
    CompanyFitAssessment,
    Projection,
]:
    """Compose role requirements with fresh company direction without claim leakage."""
    kit, match, opportunity, base_projection = project_requirement_aware_application(
        opening,
        target,
        profile,
        role=role,
    )
    if intelligence.company_id != target.company_id:
        raise ValueError(
            "company intelligence does not match target: "
            f"{intelligence.company_id!r} != {target.company_id!r}"
        )
    company_fit = assess_company_fit(profile, intelligence)
    company_rows = _company_alignment_rows(company_fit, profile)
    resume = _inject_before_truth_boundary(
        base_projection.resume_markdown,
        _company_strategy_section(company_rows),
    )
    cover = _augment_company_cover_letter(
        base_projection.cover_letter_markdown,
        company_rows,
        company_fit,
    )
    outreach = _augment_company_outreach(base_projection.outreach_markdown, company_rows)
    body = {
        "base_projection": base_projection.digest,
        "opportunity": opportunity.as_dict(),
        "company_fit": company_fit.as_dict(),
        "company_alignment_rows": company_rows,
        "company_source_urls": company_fit.source_urls,
        "resume": resume,
        "cover": cover,
        "outreach": outreach,
        "claim_sources": base_projection.claim_sources,
    }
    digest = _reference_digest(body)
    projection = replace(
        base_projection,
        application_id=f"app-{digest[:16]}",
        resume_markdown=resume,
        cover_letter_markdown=cover,
        outreach_markdown=outreach,
        digest=digest,
    )
    return kit, match, opportunity, company_fit, projection


def compile_requirement_aware_lifecycle(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    *,
    output_dir: Path,
    store: ApplicationStore,
    role: str | None = None,
    adapter: ApplicationAdapter | None = None,
    company_intelligence: CompanyIntelligence | None = None,
) -> dict[str, object]:
    """Compile a tracked recruiter packet from explicit evidence and fresh direction."""
    store.save_opening(opening)
    company_fit: CompanyFitAssessment | None = None
    if company_intelligence is None:
        kit, match, assessment, projection = project_requirement_aware_application(
            opening,
            target,
            profile,
            role=role,
        )
    else:
        kit, match, assessment, company_fit, projection = project_company_aware_application(
            opening,
            target,
            profile,
            company_intelligence,
            role=role,
        )

    artifacts = dict(write_projection(projection, match, output_dir))
    target_dir = output_dir / projection.application_id
    assessment_path = target_dir / "OPPORTUNITY_ASSESSMENT.json"
    assessment_path.write_text(
        json.dumps(assessment.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if company_fit is not None:
        company_fit_path = target_dir / "COMPANY_FIT_ASSESSMENT.json"
        company_fit_path.write_text(
            json.dumps(company_fit.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        artifacts["company_fit_assessment"] = str(company_fit_path)

    strategy_receipt: dict[str, object] = {
        "schema": "glaciereq.application-strategy-receipt.v2",
        "application_id": projection.application_id,
        "opening_digest": opening.digest,
        "profile_digest": profile.source_digest,
        "projection_digest": projection.digest,
        "opportunity_recommendation": assessment.recommendation,
        "opportunity_score": assessment.score,
        "matched_requirements": list(assessment.matched_requirements),
        "missing_requirements": list(assessment.missing_requirements),
        "claim_sources": list(projection.claim_sources),
    }
    if company_fit is not None:
        strategy_receipt["company_fit_score"] = company_fit.score
        strategy_receipt["company_fresh_signal_count"] = company_fit.fresh_signal_count
        strategy_receipt["company_matched_signals"] = list(company_fit.matched_signals)
        strategy_receipt["company_unmatched_signals"] = list(company_fit.unmatched_signals)
        strategy_receipt["company_source_urls"] = list(company_fit.source_urls)

    receipt_path = target_dir / "STRATEGY_RECEIPT.json"
    receipt_path.write_text(
        json.dumps(strategy_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts["opportunity_assessment"] = str(assessment_path)
    artifacts["strategy_receipt"] = str(receipt_path)

    packet: dict[str, object] = {
        "schema": (
            "glaciereq.company-aware-application-packet.v1"
            if company_fit is not None
            else "glaciereq.requirement-aware-application-packet.v1"
        ),
        "application_id": projection.application_id,
        "opening": opening.as_dict(),
        "kit": kit.as_dict(),
        "match": match.as_dict(),
        "opportunity": assessment.as_dict(),
        "projection_receipt": projection.digest,
        "artifacts": artifacts,
    }
    if company_fit is not None:
        packet["company_fit"] = company_fit.as_dict()

    adapter_impl = adapter if adapter is not None else ManualApplicationAdapter()
    adapter_receipt = adapter_impl.prepare(
        packet,
        target_dir / "submission",
    )
    store.create_application(projection, packet_dir=str(target_dir))
    return {
        **packet,
        "adapter_receipt": dict(adapter_receipt),
        "status": "READY",
        "application_priority": assessment.recommendation,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-strategy",
        description="Build an evidence-bound recruiter packet from role and company intelligence.",
    )
    parser.add_argument("company", help="mapped company id or display name")
    parser.add_argument("--opening", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--role")
    parser.add_argument(
        "--company-intelligence",
        type=Path,
        help="Optional provenance-bound company intelligence manifest.",
    )
    args = parser.parse_args(argv)

    target = find_target(args.company, load_targets())
    opening = load_job_opening(args.opening)
    profile = load_candidate_profile(args.profile)
    intelligence = (
        load_company_intelligence(args.company_intelligence)
        if args.company_intelligence is not None
        else None
    )
    with ApplicationStore(args.database) as store:
        packet = compile_requirement_aware_lifecycle(
            opening,
            target,
            profile,
            output_dir=args.output_dir,
            store=store,
            role=args.role,
            company_intelligence=intelligence,
        )
    print(json.dumps(packet, indent=2, sort_keys=True))
    recommendation = str(packet["application_priority"])
    return 0 if recommendation in {"APPLY_PRIORITY", "APPLY_VIABLE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
