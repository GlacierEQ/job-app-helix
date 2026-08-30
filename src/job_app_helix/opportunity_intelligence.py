"""Requirement-aware job opportunity intelligence for application prioritization.

This module deliberately separates explicit hiring requirements from noisy job-posting
prose. It produces an explainable assessment that can be used to decide which opening
should receive application effort first without inventing candidate evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .application_engine import CompanyTarget, find_target, load_targets
from .application_operations import (
    CandidateProfile,
    JobOpening,
    load_candidate_profile,
    load_job_opening,
)

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
    "will",
    "role",
    "team",
    "work",
    "using",
    "years",
    "experience",
    "preferred",
    "required",
    "requirements",
    "qualification",
    "qualifications",
}


def _tokens(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9+#.-]{1,}", value.casefold())
    return {token for token in tokens if token not in _STOPWORDS and len(token) > 1}


def _coverage(
    signals: Sequence[str],
    evidence_tokens: set[str],
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    """Score declared signals independently so long prose cannot dilute requirements."""
    matched: list[str] = []
    missing: list[str] = []
    if not signals:
        return 1.0, (), ()

    for signal in signals:
        signal_tokens = _tokens(signal)
        if not signal_tokens:
            continue
        overlap = len(signal_tokens & evidence_tokens) / len(signal_tokens)
        if overlap >= 0.5:
            matched.append(signal)
        else:
            missing.append(signal)

    considered = len(matched) + len(missing)
    score = len(matched) / considered if considered else 1.0
    return score, tuple(matched), tuple(missing)


@dataclass(frozen=True)
class OpportunityAssessment:
    schema: str
    opening_id: str
    company_id: str
    company: str
    role: str
    score: float
    recommendation: str
    role_alignment: float
    required_coverage: float
    preferred_coverage: float
    description_signal: float
    strategic_alignment: float
    proof_strength: float
    matched_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    matched_preferred: tuple[str, ...]
    missing_preferred: tuple[str, ...]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_opportunity(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    *,
    mapped_role: str | None = None,
) -> OpportunityAssessment:
    """Produce an evidence-bound, requirement-aware application priority assessment.

    Explicit requirements dominate the score. Preferred qualifications add leverage,
    while free-form description overlap is intentionally capped so marketing prose and
    boilerplate cannot swamp the hiring signals. Missing explicit requirements also cap
    the recommendation, making the result useful for application sequencing.
    """
    role = mapped_role or target.target_roles[0]
    evidence_tokens = _tokens(profile.evidence_text())

    role_tokens = _tokens(role)
    title_tokens = _tokens(opening.title)
    role_alignment = len(role_tokens & title_tokens) / max(
        1,
        len(role_tokens | title_tokens),
    )

    required_coverage, matched_required, missing_required = _coverage(
        opening.requirements,
        evidence_tokens,
    )
    preferred_coverage, matched_preferred, missing_preferred = _coverage(
        opening.preferred,
        evidence_tokens,
    )

    description_tokens = _tokens(opening.description)
    description_signal = len(description_tokens & evidence_tokens) / max(
        1,
        len(description_tokens),
    )

    strategy_tokens = _tokens(" ".join((target.recruiter_thesis, role)))
    strategic_alignment = len(strategy_tokens & evidence_tokens) / max(
        1,
        len(strategy_tokens),
    )

    proof_strength = min(1.0, len(target.recruiter_proofs) / 3.0)

    score = round(
        100
        * (
            0.20 * role_alignment
            + 0.45 * required_coverage
            + 0.12 * preferred_coverage
            + 0.08 * description_signal
            + 0.10 * strategic_alignment
            + 0.05 * proof_strength
        ),
        2,
    )

    explicit_requirements = len(opening.requirements)
    critical_gap_ratio = (
        len(missing_required) / explicit_requirements if explicit_requirements else 0.0
    )

    if not target.recruiter_proofs:
        recommendation = "BLOCKED_NO_PUBLIC_PROOF"
    elif critical_gap_ratio > 0.50:
        recommendation = "GAPS_TO_CLOSE"
    elif score >= 72 and required_coverage >= 0.75:
        recommendation = "APPLY_PRIORITY"
    elif score >= 55 and required_coverage >= 0.50:
        recommendation = "APPLY_VIABLE"
    else:
        recommendation = "DEFER"

    reasons = [
        (
            "explicit requirements matched: "
            f"{len(matched_required)}/{max(1, explicit_requirements)}"
        ),
        f"public recruiter proofs available: {len(target.recruiter_proofs)}",
        f"role alignment: {role_alignment:.0%}",
    ]
    if missing_required:
        reasons.append("missing explicit requirements: " + "; ".join(missing_required))
    elif opening.requirements:
        reasons.append(
            "no explicit requirement gaps detected from supplied candidate evidence"
        )
    if matched_preferred:
        reasons.append("preferred leverage: " + "; ".join(matched_preferred))

    return OpportunityAssessment(
        schema="glaciereq.opportunity-intelligence.v1",
        opening_id=opening.opening_id,
        company_id=target.company_id,
        company=opening.company,
        role=role,
        score=score,
        recommendation=recommendation,
        role_alignment=round(role_alignment, 6),
        required_coverage=round(required_coverage, 6),
        preferred_coverage=round(preferred_coverage, 6),
        description_signal=round(description_signal, 6),
        strategic_alignment=round(strategic_alignment, 6),
        proof_strength=round(proof_strength, 6),
        matched_requirements=matched_required,
        missing_requirements=missing_required,
        matched_preferred=matched_preferred,
        missing_preferred=missing_preferred,
        reasons=tuple(reasons),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-opportunity",
        description=(
            "Rank a real job opening using explicit requirements, candidate evidence, "
            "and recruiter proof."
        ),
    )
    parser.add_argument("company", help="mapped company id or display name")
    parser.add_argument(
        "--opening",
        type=Path,
        required=True,
        help="normalized job opening JSON",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="evidence-only candidate profile JSON",
    )
    parser.add_argument("--role", help="mapped target role")
    parser.add_argument("--output", type=Path, help="optional JSON receipt path")
    args = parser.parse_args(argv)

    target = find_target(args.company, load_targets())
    opening = load_job_opening(args.opening)
    profile = load_candidate_profile(args.profile)
    assessment = assess_opportunity(opening, target, profile, mapped_role=args.role)
    rendered = json.dumps(assessment.as_dict(), indent=2, sort_keys=True) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if assessment.recommendation in {"APPLY_PRIORITY", "APPLY_VIABLE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
