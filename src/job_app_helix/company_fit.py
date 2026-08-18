"""Company-fit scoring over fresh, provenance-bound target intelligence."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .application_operations import CandidateProfile, load_candidate_profile
from .company_intelligence import CompanyIntelligence, load_company_intelligence
from .opportunity_intelligence import _tokens


@dataclass(frozen=True)
class CompanyFitAssessment:
    schema: str
    company_id: str
    company: str
    score: float
    fresh_signal_count: int
    stale_signal_count: int
    matched_signals: tuple[str, ...]
    unmatched_signals: tuple[str, ...]
    strategic_hooks: tuple[str, ...]
    source_urls: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_company_fit(
    profile: CandidateProfile,
    intelligence: CompanyIntelligence,
    *,
    now: datetime | None = None,
) -> CompanyFitAssessment:
    clock = now or datetime.now(UTC)
    fresh = intelligence.fresh_signals(now=clock)
    stale = intelligence.stale_signals(now=clock)
    evidence_tokens = _tokens(profile.evidence_text())

    matched: list[str] = []
    unmatched: list[str] = []
    hooks: list[str] = []
    for signal in fresh:
        signal_tokens = _tokens(signal.statement)
        overlap = len(signal_tokens & evidence_tokens) / max(1, len(signal_tokens))
        if overlap >= 0.20:
            matched.append(signal.statement)
            hooks.append(f"{signal.kind}: {signal.statement}")
        else:
            unmatched.append(signal.statement)

    score = round(100 * len(matched) / max(1, len(fresh)), 2)
    return CompanyFitAssessment(
        schema="glaciereq.company-fit.v1",
        company_id=intelligence.company_id,
        company=intelligence.company,
        score=score,
        fresh_signal_count=len(fresh),
        stale_signal_count=len(stale),
        matched_signals=tuple(matched),
        unmatched_signals=tuple(unmatched),
        strategic_hooks=tuple(hooks),
        source_urls=tuple(dict.fromkeys(signal.source_url for signal in fresh)),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-company-fit",
        description="Score candidate evidence against fresh sourced company signals.",
    )
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--intelligence", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    assessment = assess_company_fit(
        load_candidate_profile(args.profile),
        load_company_intelligence(args.intelligence),
    )
    rendered = json.dumps(assessment.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if assessment.fresh_signal_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
