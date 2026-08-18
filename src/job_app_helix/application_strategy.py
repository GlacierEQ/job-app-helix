"""Requirement-aware application strategy built on the existing Helix lifecycle.

The strategy layer composes opportunity intelligence with projection generation so
explicit hiring requirements influence what the recruiter actually sees. Candidate
claims remain bounded to supplied profile evidence and admitted public proof.
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
    _canonical_digest,
    _tokens,
    load_candidate_profile,
    load_job_opening,
    project_application,
    write_projection,
)
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


def _strategy_section(rows: tuple[tuple[str, str], ...]) -> str:
    if not rows:
        return ""
    bullets = "\n".join(f"- **{signal}:** {evidence}" for signal, evidence in rows)
    return "## Role-aligned evidence\n\n" + bullets


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
    digest = _canonical_digest(body)
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


def compile_requirement_aware_lifecycle(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    *,
    output_dir: Path,
    store: ApplicationStore,
    role: str | None = None,
    adapter: ApplicationAdapter | None = None,
) -> dict[str, object]:
    """Compile a tracked packet whose recruiter copy follows explicit requirement evidence."""
    store.save_opening(opening)
    kit, match, assessment, projection = project_requirement_aware_application(
        opening,
        target,
        profile,
        role=role,
    )
    artifacts = dict(write_projection(projection, match, output_dir))
    target_dir = output_dir / projection.application_id
    assessment_path = target_dir / "OPPORTUNITY_ASSESSMENT.json"
    assessment_path.write_text(
        json.dumps(assessment.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    strategy_receipt = {
        "schema": "glaciereq.application-strategy-receipt.v1",
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
    receipt_path = target_dir / "STRATEGY_RECEIPT.json"
    receipt_path.write_text(
        json.dumps(strategy_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts["opportunity_assessment"] = str(assessment_path)
    artifacts["strategy_receipt"] = str(receipt_path)

    packet: dict[str, object] = {
        "schema": "glaciereq.requirement-aware-application-packet.v1",
        "application_id": projection.application_id,
        "opening": opening.as_dict(),
        "kit": kit.as_dict(),
        "match": match.as_dict(),
        "opportunity": assessment.as_dict(),
        "projection_receipt": projection.digest,
        "artifacts": artifacts,
    }
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
        description="Build a requirement-aware recruiter packet from supplied evidence.",
    )
    parser.add_argument("company", help="mapped company id or display name")
    parser.add_argument("--opening", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--role")
    args = parser.parse_args(argv)

    target = find_target(args.company, load_targets())
    opening = load_job_opening(args.opening)
    profile = load_candidate_profile(args.profile)
    with ApplicationStore(args.database) as store:
        packet = compile_requirement_aware_lifecycle(
            opening,
            target,
            profile,
            output_dir=args.output_dir,
            store=store,
            role=args.role,
        )
    print(json.dumps(packet, indent=2, sort_keys=True))
    recommendation = str(packet["application_priority"])
    return 0 if recommendation in {"APPLY_PRIORITY", "APPLY_VIABLE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
