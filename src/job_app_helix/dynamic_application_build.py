from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .application_engine import CompanyTarget, RepositoryProof
from .application_operations import (
    CandidateProfile,
    JobOpening,
    ingest_job_opening_url,
    load_candidate_profile,
    load_job_opening,
    project_application,
)
from .candidate_profile_compiler import CandidateProfileCompileError, write_candidate_profile
from .genius_engine import GeniusRun, invent

STOPWORDS = frozenset(
    {
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
        "years",
        "experience",
        "preferred",
        "required",
        "requirements",
        "qualification",
        "qualifications",
    }
)
PUBLIC_STATES = frozenset({"PROMOTED", "REFERENCE_ONLY"})


class DynamicBuildError(RuntimeError):
    """Raised when an opportunity-driven build cannot preserve its runtime contract."""


@dataclass(frozen=True)
class DynamicEvidence:
    system_id: str
    repository: str
    capabilities: tuple[str, ...]
    matched_signals: tuple[str, ...]
    score: float
    level: str
    state: str
    visibility: str
    public_proof: bool
    source: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DynamicBuildResult:
    schema: str
    opening_id: str
    opening_digest: str
    company: str
    role: str
    demand_signals: tuple[str, ...]
    evidence_graph: tuple[DynamicEvidence, ...]
    public_proof_repositories: tuple[str, ...]
    engineering_donor_repositories: tuple[str, ...]
    uncovered_signals: tuple[str, ...]
    build_actions: tuple[Mapping[str, object], ...]
    application_id: str | None
    genius_receipt_sha256: str | None
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "opening_id": self.opening_id,
            "opening_digest": self.opening_digest,
            "company": self.company,
            "role": self.role,
            "demand_signals": list(self.demand_signals),
            "evidence_graph": [row.as_dict() for row in self.evidence_graph],
            "public_proof_repositories": list(self.public_proof_repositories),
            "engineering_donor_repositories": list(self.engineering_donor_repositories),
            "uncovered_signals": list(self.uncovered_signals),
            "build_actions": [dict(row) for row in self.build_actions],
            "application_id": self.application_id,
            "genius_receipt_sha256": self.genius_receipt_sha256,
            "receipt_sha256": self.receipt_sha256,
        }


def _tokens(value: str) -> set[str]:
    raw = re.findall(r"[a-z0-9][a-z0-9+#.-]{1,}", value.casefold())
    return {token for token in raw if token not in STOPWORDS and len(token) > 1}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "target"


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DynamicBuildError(f"invalid {label} at {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise DynamicBuildError(f"{label} must be a JSON object: {path}")
    return payload


def _demand_signals(opening: JobOpening) -> tuple[str, ...]:
    explicit = " ".join((*opening.requirements, *opening.preferred, opening.title))
    signals = _tokens(explicit)
    if not signals:
        signals = _tokens(opening.description)
    return tuple(sorted(signals))


def _systems(bundle: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    registry = bundle.get("system_registry")
    if not isinstance(registry, Mapping):
        raise DynamicBuildError("estate bundle requires system_registry")
    rows = registry.get("systems")
    if not isinstance(rows, list):
        raise DynamicBuildError("estate bundle system_registry requires systems list")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        system_id = str(row.get("system_id") or "").strip()
        repository = str(row.get("source_repository") or "").strip()
        if system_id and repository:
            result[system_id] = row
    if not result:
        raise DynamicBuildError("estate bundle contains no reference systems")
    return result


def _capabilities(bundle: Mapping[str, Any]) -> dict[str, set[str]]:
    registry = bundle.get("capability_donor_registry")
    if not isinstance(registry, Mapping):
        raise DynamicBuildError("estate bundle requires capability_donor_registry")
    rows = registry.get("capabilities")
    if not isinstance(rows, list):
        raise DynamicBuildError("capability donor registry requires capabilities list")
    result: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        capability_id = str(row.get("capability_id") or "").strip()
        donors = row.get("donor_systems")
        if not capability_id or not isinstance(donors, list):
            continue
        for system_id in donors:
            if isinstance(system_id, str) and system_id:
                result[system_id].add(capability_id)
    return result


def _company_projection_rows(
    bundle: Mapping[str, Any],
    company: str,
) -> dict[str, Mapping[str, Any]]:
    registry = bundle.get("company_projection_registry")
    if not isinstance(registry, Mapping):
        return {}
    projections = registry.get("projections")
    if not isinstance(projections, list):
        return {}
    needle = company.casefold().strip()
    for projection in projections:
        if not isinstance(projection, Mapping):
            continue
        names = {
            str(projection.get("company_id") or "").casefold(),
            str(projection.get("display_name") or "").casefold(),
            str(projection.get("company") or "").casefold(),
        }
        if needle not in names and not any(needle and needle in item for item in names):
            continue
        evidence = projection.get("ranked_evidence")
        if not isinstance(evidence, list):
            return {}
        return {
            str(row.get("system_id")): row
            for row in evidence
            if isinstance(row, Mapping) and row.get("system_id")
        }
    return {}


def derive_evidence_graph(
    opening: JobOpening,
    estate_bundle: Mapping[str, Any],
) -> tuple[DynamicEvidence, ...]:
    """Derive the opportunity evidence graph from the full compiled estate at runtime."""
    systems = _systems(estate_bundle)
    capabilities = _capabilities(estate_bundle)
    projection_rows = _company_projection_rows(estate_bundle, opening.company)
    demand = set(_demand_signals(opening))
    rows: list[DynamicEvidence] = []

    for system_id, system in systems.items():
        repo = str(system.get("source_repository") or "")
        system_caps = set(capabilities.get(system_id, set()))
        descriptive = " ".join(
            [
                system_id,
                repo,
                str(system.get("role") or ""),
                str(system.get("evidence") or ""),
                " ".join(sorted(system_caps)),
            ]
        )
        matched = demand & _tokens(descriptive)
        company_row = projection_rows.get(system_id)
        company_bonus = 0.0
        if company_row is not None:
            row_caps = company_row.get("capability_ids")
            if isinstance(row_caps, list):
                system_caps.update(str(value) for value in row_caps if str(value).strip())
                matched |= demand & _tokens(" ".join(system_caps))
            company_bonus = 0.25

        if not matched and company_row is None:
            continue

        coverage = len(matched) / max(1, len(demand))
        transferability = min(0.20, 0.03 * len(system_caps))
        score = round(min(1.0, coverage + company_bonus + transferability), 6)
        level = str(
            (company_row or {}).get("level")
            or system.get("flagship_level")
            or system.get("level")
            or "L0"
        )
        state = str(
            (company_row or {}).get("promotion_state")
            or system.get("flagship_state")
            or system.get("state")
            or "ESTATE_DISCOVERED"
        )
        visibility = str(
            (company_row or {}).get("visibility")
            or system.get("visibility")
            or "private"
        )
        visibility_decision = str((company_row or {}).get("visibility_decision") or "")
        public_proof = (
            visibility == "public"
            and state in PUBLIC_STATES
            and visibility_decision in {"", "PUBLIC_ELIGIBLE"}
        )
        rows.append(
            DynamicEvidence(
                system_id=system_id,
                repository=repo,
                capabilities=tuple(sorted(system_caps)),
                matched_signals=tuple(sorted(matched)),
                score=score,
                level=level,
                state=state,
                visibility=visibility,
                public_proof=public_proof,
                source=(
                    "COMPANY_PROJECTION_RUNTIME_MATCH"
                    if company_row is not None
                    else "FULL_ESTATE_RUNTIME_MATCH"
                ),
            )
        )

    rows.sort(key=lambda row: (-row.score, -len(row.matched_signals), row.repository))
    return tuple(rows)


def _dynamic_target(
    opening: JobOpening,
    evidence: Sequence[DynamicEvidence],
    uncovered: Sequence[str],
) -> CompanyTarget:
    proofs = tuple(
        RepositoryProof(
            repository=row.repository,
            level=row.level,
            state=row.state,
            visibility=row.visibility,
            admission="DYNAMIC_EVIDENCE_MATCH",
            origin=row.source,
        )
        for row in evidence
        if row.public_proof
    )
    thesis = (
        f"Build directly against the live {opening.title} demand at {opening.company} "
        "using the strongest runtime-matched estate capabilities rather than a predeclared packet."
    )
    gap = (
        "Material uncovered demand: " + ", ".join(uncovered)
        if uncovered
        else "No material requirement token remains uncovered by the runtime evidence graph."
    )
    return CompanyTarget(
        company_id=_slug(opening.company),
        display_name=opening.company,
        track_state="DYNAMIC_OPPORTUNITY_BUILD",
        target_roles=(opening.title,),
        recruiter_thesis=thesis,
        gap_or_next_gate=gap,
        non_affiliation=(
            "Independent applicant engineering evidence. No employer affiliation, adoption, "
            "endorsement, or production deployment is implied."
        ),
        repositories=proofs,
    )


def _build_actions(
    evidence: Sequence[DynamicEvidence],
    uncovered: Sequence[str],
) -> tuple[Mapping[str, object], ...]:
    actions: list[Mapping[str, object]] = []
    for row in evidence:
        actions.append(
            {
                "action": "REUSE_PUBLIC_PROOF" if row.public_proof else "COMPOSE_ENGINEERING_DONOR",
                "repository": row.repository,
                "system_id": row.system_id,
                "matched_signals": list(row.matched_signals),
                "capabilities": list(row.capabilities),
                "score": row.score,
            }
        )
    if uncovered:
        actions.append(
            {
                "action": "EVOLVE_OR_INVENT",
                "uncovered_signals": list(uncovered),
                "donor_repositories": [row.repository for row in evidence],
            }
        )
    actions.append(
        {
            "action": "COMPILE_TARGET_APPLICATION",
            "depends_on": [row.repository for row in evidence if row.public_proof],
        }
    )
    return tuple(actions)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _run_genius(
    opening: JobOpening,
    evidence: Sequence[DynamicEvidence],
    uncovered: Sequence[str],
) -> GeniusRun | None:
    if not uncovered:
        return None
    repository = evidence[0].repository if evidence else "GlacierEQ/job-app-helix"
    subject = {
        "repository": repository,
        "company": opening.company,
        "domain": "hire",
        "problem": (
            f"{opening.company} / {opening.title}: runtime build still lacks material demand "
            + ", ".join(uncovered)
            + "."
        ),
        "cause": (
            "The live opportunity requires capability not yet covered by the dynamically "
            "matched estate evidence graph."
        ),
        "description": opening.description[:800],
    }
    return invent(
        subject,
        limit=3,
        include_atlas_seeds=True,
        live_research=False,
        accumulate=False,
        publish_links=False,
    )


def execute_dynamic_build(
    opening: JobOpening,
    profile: CandidateProfile,
    estate_bundle: Mapping[str, Any],
    *,
    output_dir: Path,
    run_genius: bool = True,
) -> DynamicBuildResult:
    """Build a target-specific application surface from the live opportunity itself."""
    evidence = derive_evidence_graph(opening, estate_bundle)
    demand = set(_demand_signals(opening))
    covered = {
        signal
        for row in evidence
        for signal in row.matched_signals
    }
    uncovered = tuple(sorted(demand - covered))
    target = _dynamic_target(opening, evidence, uncovered)
    actions = _build_actions(evidence, uncovered)

    build_dir = output_dir / f"{_slug(opening.company)}--{_slug(opening.title)}--{opening.opening_id}"
    build_dir.mkdir(parents=True, exist_ok=True)

    application_id: str | None = None
    public_proofs = tuple(row.repository for row in evidence if row.public_proof)
    if public_proofs:
        _, match, projection = project_application(opening, target, profile, role=opening.title)
        application_id = projection.application_id
        (build_dir / "RESUME.md").write_text(projection.resume_markdown, encoding="utf-8")
        (build_dir / "COVER_LETTER.md").write_text(
            projection.cover_letter_markdown,
            encoding="utf-8",
        )
        (build_dir / "OUTREACH.md").write_text(
            projection.outreach_markdown,
            encoding="utf-8",
        )
        _write_json(build_dir / "MATCH.json", match.as_dict())

    genius = _run_genius(opening, evidence, uncovered) if run_genius else None
    if genius is not None:
        _write_json(build_dir / "GENIUS_ADVANCE.json", genius.to_dict())

    engineering_donors = tuple(row.repository for row in evidence)
    receipt_body: dict[str, object] = {
        "schema": "glaciereq.dynamic-opportunity-build.v1",
        "opening_id": opening.opening_id,
        "opening_digest": opening.digest,
        "company": opening.company,
        "role": opening.title,
        "demand_signals": sorted(demand),
        "evidence_graph": [row.as_dict() for row in evidence],
        "public_proof_repositories": list(public_proofs),
        "engineering_donor_repositories": list(engineering_donors),
        "uncovered_signals": list(uncovered),
        "build_actions": [dict(row) for row in actions],
        "application_id": application_id,
        "genius_receipt_sha256": genius.receipt_sha256 if genius else None,
    }
    receipt_sha = _digest(receipt_body)
    result = DynamicBuildResult(
        schema=str(receipt_body["schema"]),
        opening_id=opening.opening_id,
        opening_digest=opening.digest,
        company=opening.company,
        role=opening.title,
        demand_signals=tuple(sorted(demand)),
        evidence_graph=evidence,
        public_proof_repositories=public_proofs,
        engineering_donor_repositories=engineering_donors,
        uncovered_signals=uncovered,
        build_actions=actions,
        application_id=application_id,
        genius_receipt_sha256=genius.receipt_sha256 if genius else None,
        receipt_sha256=receipt_sha,
    )
    _write_json(build_dir / "DYNAMIC_BUILD.json", result.as_dict())
    return result


def _resolve_profile(
    *,
    profile_path: Path | None,
    resume_paths: Sequence[Path],
    output_dir: Path,
    profile_id: str | None,
) -> CandidateProfile:
    if profile_path is not None and resume_paths:
        raise DynamicBuildError("use either --profile or --resume, not both")
    if profile_path is not None:
        return load_candidate_profile(profile_path)
    if not resume_paths:
        raise DynamicBuildError("candidate evidence requires --profile or --resume")
    compiled = output_dir / "COMPILED_CANDIDATE_PROFILE.json"
    try:
        write_candidate_profile(resume_paths, compiled, profile_id=profile_id)
    except CandidateProfileCompileError as exc:
        raise DynamicBuildError(f"candidate profile compilation failed: {exc}") from exc
    return load_candidate_profile(compiled)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-dynamic-build",
        description=(
            "Build a company/role application dynamically from one live opening and the "
            "current compiled estate. No predeclared company target manifest is required."
        ),
    )
    opening = parser.add_mutually_exclusive_group(required=True)
    opening.add_argument("--opening", type=Path)
    opening.add_argument("--opening-url")
    candidate = parser.add_mutually_exclusive_group(required=True)
    candidate.add_argument("--profile", type=Path)
    candidate.add_argument("--resume", type=Path, action="append")
    parser.add_argument("--profile-id")
    parser.add_argument("--estate-bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--no-genius", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    opening = (
        load_job_opening(args.opening)
        if args.opening is not None
        else ingest_job_opening_url(str(args.opening_url))
    )
    profile = _resolve_profile(
        profile_path=args.profile,
        resume_paths=tuple(args.resume or ()),
        output_dir=args.output_dir,
        profile_id=args.profile_id,
    )
    estate_bundle = _load_object(args.estate_bundle, "estate bundle")
    result = execute_dynamic_build(
        opening,
        profile,
        estate_bundle,
        output_dir=args.output_dir,
        run_genius=not args.no_genius,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.application_id is not None or result.evidence_graph else 2


if __name__ == "__main__":
    raise SystemExit(main())
