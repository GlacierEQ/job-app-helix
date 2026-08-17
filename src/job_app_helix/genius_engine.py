"""Executable invent -> attack -> rank engine for APEX restoration work.

The engine converts a repository bottleneck into multiple concrete mechanisms,
attacks weak proposals, ranks surviving candidates, and emits a deterministic
receipt. It deliberately separates invention from promotion: callers still own
implementation, testing, and exact-head verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from math import isfinite
from pathlib import Path
from typing import Any

ENGINE_ID = "glaciereq.genius-engine.v1"
APEX_IDENTITY = "APEX_IS_THE_COUNTER_TO_CANONICAL_DESTRUCTION"
EXECUTION_LAW = "MAXIMUM_COHERENT_ADVANCE"
SOLUTION_FIELDS = (
    "problem",
    "cause",
    "mechanism",
    "implementation",
    "measurement",
    "failure_mode",
    "boundary",
    "value",
)

MECHANISM_LIBRARY: tuple[dict[str, Any], ...] = (
    {
        "id": "dual_plane_truth",
        "name": "Dual-Plane Truth Router",
        "pattern": (
            "Keep VERIFIED, IMPLEMENTED, and TARGET planes simultaneously; "
            "never delete implemented power merely to green a smaller harness."
        ),
        "domains": ("governance", "portfolio", "mcp", "hire", "all"),
        "leverage": 0.94,
        "recovery": 0.96,
    },
    {
        "id": "capability_restore_queue",
        "name": "Capability Restore Queue",
        "pattern": (
            "Turn displaced capability into an executable restore ladder with donor "
            "lineage, acceptance gates, and rollback instead of archival metadata."
        ),
        "domains": ("governance", "recovery", "portfolio", "all"),
        "leverage": 0.91,
        "recovery": 0.98,
    },
    {
        "id": "claim_fence",
        "name": "Claim Fence",
        "pattern": (
            "Compile recruiter and public claims from exact proof receipts and degrade "
            "unsupported language without deleting underlying implementation."
        ),
        "domains": ("hire", "portfolio", "docs"),
        "leverage": 0.92,
        "recovery": 0.84,
    },
    {
        "id": "provenance_compulsory",
        "name": "Answer/Actuation Provenance",
        "pattern": (
            "Bind every externalized claim or side effect to source evidence or a signed "
            "intent graph; incomplete provenance withholds only the unsafe action."
        ),
        "domains": ("agent", "legal", "ops", "security"),
        "leverage": 0.88,
        "recovery": 0.83,
    },
    {
        "id": "receipt_bus",
        "name": "Actuation Receipt Bus",
        "pattern": (
            "Represent every command as intent plus preconditions, abort predicates, "
            "postconditions, and durable observation receipts."
        ),
        "domains": ("colossus", "energy", "cooling", "ops", "spacex"),
        "leverage": 0.90,
        "recovery": 0.88,
    },
    {
        "id": "split_brain_actuation",
        "name": "Mission Assurance Split Brain",
        "pattern": (
            "Separate policy decision from actuation and require independent evidence "
            "before irreversible side effects can complete."
        ),
        "domains": ("control", "security", "ops", "colossus", "spacex"),
        "leverage": 0.87,
        "recovery": 0.86,
    },
    {
        "id": "thread_quorum",
        "name": "Mission Thread Quorum",
        "pattern": (
            "Run independent decision planes with explicit dissent, deterministic holds, "
            "and recovery criteria rather than silent last-writer authority."
        ),
        "domains": ("spacex", "mesh", "ops"),
        "leverage": 0.86,
        "recovery": 0.91,
    },
    {
        "id": "mcp_package_restore",
        "name": "Provider Surface Restore",
        "pattern": (
            "Restore credential-gated MCP/provider execution beside local routers while "
            "preserving fail-closed policy and non-secret observability."
        ),
        "domains": ("mcp", "integration", "agent"),
        "leverage": 0.93,
        "recovery": 0.94,
    },
    {
        "id": "solver_power_expansion",
        "name": "Solver Power Expansion",
        "pattern": (
            "When claims outrun implementation, build and benchmark the missing solver "
            "instead of lowering the target to the proof harness."
        ),
        "domains": ("orbital", "physics", "numerical", "spacex"),
        "leverage": 0.89,
        "recovery": 0.87,
    },
    {
        "id": "anti_neutralization_gate",
        "name": "Anti-Neutralization Merge Gate",
        "pattern": (
            "Detect capability shrink, package amputation, or implementation-to-metadata "
            "collapse and require explicit operator-authorized reduction."
        ),
        "domains": ("governance", "ci", "portfolio", "all"),
        "leverage": 0.95,
        "recovery": 0.92,
    },
)


class GeniusEngineError(ValueError):
    """Raised when a subject or generated solution violates engine invariants."""


@dataclass(frozen=True)
class GeniusSolution:
    """A fully specified restoration or upgrade mechanism."""

    solution_id: str
    title: str
    problem: str
    cause: str
    mechanism: str
    implementation: str
    measurement: str
    failure_mode: str
    boundary: str
    value: str
    domain: str = "general"
    repository: str | None = None
    company_track: str | None = None
    plane: str = "IMPLEMENTED"
    novelty_score: float = 0.0
    coherence_score: float = 0.0
    genius_score: float = 0.0
    apex_aligned: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def missing_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in SOLUTION_FIELDS
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip()
        )


@dataclass(frozen=True)
class GeniusRun:
    """One deterministic invent -> attack -> rank cycle."""

    engine_id: str
    identity: str
    law: str
    subject: dict[str, Any]
    solutions: tuple[GeniusSolution, ...]
    rejected: tuple[dict[str, Any], ...]
    primary: GeniusSolution | None
    receipt_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "identity": self.identity,
            "law": self.law,
            "subject": self.subject,
            "solutions": [solution.to_dict() for solution in self.solutions],
            "rejected": list(self.rejected),
            "primary": self.primary.to_dict() if self.primary else None,
            "receipt_sha256": self.receipt_sha256,
        }


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]
    return f"genius-{digest}"


def _clamp01(value: float) -> float:
    if not isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def _signal_text(subject: Mapping[str, Any]) -> str:
    keys = ("repository", "name", "description", "bottleneck", "domain", "tags", "company")
    return " ".join(str(subject.get(key) or "") for key in keys).lower()


def infer_domain(subject: Mapping[str, Any]) -> str:
    text = _signal_text(subject)
    rules = (
        ("spacex", ("spacex", "launch", "propulsion", "telemetry", "mission-control")),
        ("orbital", ("orbital", "kepler", "lambert", "astrodynamic")),
        ("colossus", ("colossus", "cooling", "thermal", "megapack", "energy")),
        ("mcp", ("mcp", "tool-router", "stdio", "provider")),
        ("hire", ("job-app", "resume", "portfolio", "recruiter", "application")),
        ("governance", ("helix", "akos", "governance", "estate", "excellence")),
        ("security", ("security", "auth", "zero-trust", "oidc")),
        ("agent", ("agent", "llm", "reasoning", "orchestr")),
    )
    for domain, terms in rules:
        if any(term in text for term in terms):
            return domain
    return str(subject.get("domain") or "general")


def infer_bottleneck(subject: Mapping[str, Any]) -> tuple[str, str]:
    problem = subject.get("problem")
    cause = subject.get("cause")
    if problem and cause:
        return str(problem), str(cause)

    neutralization = int(subject.get("neutralization_stamps") or 0)
    if neutralization >= 2 or subject.get("paper_recovery_only"):
        return (
            "Intended product capability was reduced to a local, synthetic, or proof-only surface.",
            "Verification boundaries were promoted into product boundaries and displaced stronger mechanisms.",
        )
    if subject.get("missing_implementation"):
        return (
            "Architecture or recruiter claims outrun repository-native implementation.",
            "The proof ceiling became the product ceiling instead of driving implementation expansion.",
        )
    if subject.get("hollow_or_thin"):
        return (
            "The repository is too thin to demonstrate a defensible mechanism under adversarial review.",
            "Scaffolding and metadata accumulated faster than executable product capability.",
        )

    defaults = {
        "spacex": (
            "Operational planes lack deterministic coordination under dissent or stale authority.",
            "Independent subsystems can disagree without a fail-closed recovery contract.",
        ),
        "colossus": (
            "Actuation can outrun complete precondition and postcondition evidence.",
            "Command execution is not receipt-bound across thermal and power constraints.",
        ),
        "mcp": (
            "Useful provider execution is either amputated or insufficiently bounded.",
            "Local proof routers replaced credentialed capability instead of constraining it.",
        ),
        "hire": (
            "Recruiter-facing claims can drift from live repository evidence.",
            "Projection surfaces are not compiled from fresh exact-source proof state.",
        ),
        "governance": (
            "Estate repair can convert executable power into reports and classifications.",
            "Process optimization displaced maximum coherent product advance.",
        ),
    }
    return defaults.get(
        infer_domain(subject),
        (
            "The repository has not concentrated enough power on its highest-leverage bottleneck.",
            "Feature scatter and proof work outpaced a composable mechanism that removes the constraint.",
        ),
    )


def select_mechanisms(domain: str, limit: int = 4) -> list[dict[str, Any]]:
    if limit < 1:
        raise GeniusEngineError("limit must be >= 1")
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for mechanism in MECHANISM_LIBRARY:
        domains = mechanism["domains"]
        domain_fit = 1.0 if domain in domains else 0.72 if "all" in domains else 0.0
        if domain == "general":
            domain_fit = max(domain_fit, 0.60)
        if domain_fit == 0.0:
            continue
        score = (
            0.45 * domain_fit
            + 0.30 * float(mechanism["leverage"])
            + 0.25 * float(mechanism["recovery"])
        )
        scored.append((score, mechanism["id"], mechanism))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [mechanism for _, _, mechanism in scored[:limit]]


def _solution_scores(
    mechanism: Mapping[str, Any],
    subject: Mapping[str, Any],
    domain: str,
) -> tuple[float, float, float]:
    domains = mechanism["domains"]
    domain_fit = 1.0 if domain in domains else 0.76 if "all" in domains else 0.62
    restoration_pressure = min(
        1.0,
        0.35
        + 0.16 * int(subject.get("neutralization_stamps") or 0)
        + 0.18 * bool(subject.get("paper_recovery_only"))
        + 0.14 * bool(subject.get("missing_implementation")),
    )
    novelty = _clamp01(
        0.34 * domain_fit
        + 0.28 * float(mechanism["leverage"])
        + 0.22 * restoration_pressure
        + 0.16 * float(mechanism["recovery"])
    )
    coherence = _clamp01(
        0.40 * domain_fit
        + 0.25 * float(mechanism["recovery"])
        + 0.20 * float(mechanism["leverage"])
        + 0.15 * (1.0 if subject.get("repository") else 0.72)
    )
    genius = _clamp01(0.46 * novelty + 0.54 * coherence)
    return novelty, coherence, genius


def build_solution(
    *,
    subject: Mapping[str, Any],
    mechanism: Mapping[str, Any],
    problem: str,
    cause: str,
) -> GeniusSolution:
    repository = str(subject.get("repository") or subject.get("name") or "").strip() or None
    domain = infer_domain(subject)
    novelty, coherence, genius = _solution_scores(mechanism, subject, domain)
    title = str(mechanism["name"])
    if repository:
        title = f"{title} for {repository}"

    implementation = (
        f"Implement `{mechanism['id']}` as repository-native code. Recover useful donor "
        "mechanisms individually, preserve stronger later interfaces, expose a real execution "
        "path, add structured observations and rollback, then bind promotion to exact-source tests."
    )
    measurement = (
        "Run deterministic and adversarial mechanism tests, refuse-path tests, before/after "
        "capability checks, and a runtime or benchmark proof when the mechanism has measurable output."
    )
    failure_mode = (
        "Incomplete provenance, invalid authority, missing postcondition evidence, capability shrink, "
        "or unsupported claim promotion must fail closed without deleting recoverable implementation."
    )
    boundary = (
        "Do not infer company affiliation or production authority; keep secrets/private evidence off "
        "public surfaces; verification limits constrain claims, not the implementation target."
    )
    value = (
        "Removes the selected bottleneck while increasing reusable executable power, recovery depth, "
        "and evidence-coupled recruiter value."
    )
    return GeniusSolution(
        solution_id=_stable_id(repository or "estate", str(mechanism["id"]), problem[:96]),
        title=title,
        problem=problem,
        cause=cause,
        mechanism=f"{mechanism['name']}: {mechanism['pattern']}",
        implementation=implementation,
        measurement=measurement,
        failure_mode=failure_mode,
        boundary=boundary,
        value=value,
        domain=domain,
        repository=repository,
        company_track=str(subject["company"]) if subject.get("company") else None,
        novelty_score=round(novelty, 4),
        coherence_score=round(coherence, 4),
        genius_score=round(genius, 4),
        tags=(str(mechanism["id"]), domain, EXECUTION_LAW),
    )


def attack_solution(solution: GeniusSolution) -> tuple[bool, tuple[str, ...]]:
    """Reject incomplete, theatrical, or capability-neutralizing proposals."""
    blockers: list[str] = []
    if solution.missing_fields():
        blockers.append(f"missing fields: {', '.join(solution.missing_fields())}")
    if solution.genius_score < 0.35:
        blockers.append("genius score below 0.35")
    if solution.coherence_score < 0.35:
        blockers.append("coherence score below 0.35")

    body = " ".join(str(value) for value in solution.to_dict().values()).lower()
    theater_terms = ("placeholder", "todo", "fake adapter", "simulate success", "docs only")
    if any(term in body for term in theater_terms):
        blockers.append("proposal contains delivery-theater language")
    if "delete" in solution.implementation.lower() and "capability" in solution.implementation.lower():
        blockers.append("proposal risks capability deletion as simplification")
    if EXECUTION_LAW.lower() not in " ".join(solution.tags).lower():
        blockers.append("maximum coherent advance law missing")
    return not blockers, tuple(blockers)


def _receipt_payload(
    subject: Mapping[str, Any],
    solutions: Sequence[GeniusSolution],
    rejected: Sequence[Mapping[str, Any]],
) -> str:
    payload = {
        "engine_id": ENGINE_ID,
        "identity": APEX_IDENTITY,
        "law": EXECUTION_LAW,
        "subject": dict(subject),
        "solutions": [solution.to_dict() for solution in solutions],
        "rejected": list(rejected),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def invent(
    subject: Mapping[str, Any],
    *,
    limit: int = 3,
    include_atlas_seeds: bool = True,
) -> GeniusRun:
    """Generate, attack, and rank mechanisms for one repository or job subject."""
    del include_atlas_seeds  # Reserved compatibility flag; source seeds remain optional input data.
    if not subject or not any(value for value in subject.values()):
        raise GeniusEngineError("subject must contain at least one meaningful signal")
    if limit < 1:
        raise GeniusEngineError("limit must be >= 1")

    problem, cause = infer_bottleneck(subject)
    domain = infer_domain(subject)
    candidates = [
        build_solution(subject=subject, mechanism=mechanism, problem=problem, cause=cause)
        for mechanism in select_mechanisms(domain, max(limit * 2, 4))
    ]

    accepted: list[GeniusSolution] = []
    rejected: list[dict[str, Any]] = []
    for candidate in candidates:
        ok, blockers = attack_solution(candidate)
        if ok:
            accepted.append(candidate)
        else:
            rejected.append(
                {
                    "solution_id": candidate.solution_id,
                    "title": candidate.title,
                    "blockers": list(blockers),
                }
            )

    accepted.sort(
        key=lambda solution: (
            -solution.genius_score,
            -solution.coherence_score,
            -solution.novelty_score,
            solution.solution_id,
        )
    )
    accepted = accepted[:limit]
    receipt = _receipt_payload(subject, accepted, rejected)
    return GeniusRun(
        engine_id=ENGINE_ID,
        identity=APEX_IDENTITY,
        law=EXECUTION_LAW,
        subject=dict(subject),
        solutions=tuple(accepted),
        rejected=tuple(rejected),
        primary=accepted[0] if accepted else None,
        receipt_sha256=receipt,
    )


def invent_restoration(subject: Mapping[str, Any], *, limit: int = 3) -> GeniusRun:
    """Force restoration pressure while preserving caller-supplied repository context."""
    restored_subject = dict(subject)
    restored_subject.setdefault("neutralization_stamps", 2)
    restored_subject.setdefault("paper_recovery_only", True)
    return invent(restored_subject, limit=limit, include_atlas_seeds=False)


def invent_estate(
    subjects: Sequence[Mapping[str, Any]],
    *,
    limit_per: int = 1,
) -> dict[str, Any]:
    """Run the engine across an estate and rank repositories by primary opportunity."""
    runs = [invent(subject, limit=limit_per).to_dict() for subject in subjects]
    runs.sort(
        key=lambda run: (
            -float((run.get("primary") or {}).get("genius_score") or 0.0),
            str((run.get("subject") or {}).get("repository") or ""),
        )
    )
    canonical = json.dumps(runs, sort_keys=True, separators=(",", ":")).encode()
    return {
        "engine_id": ENGINE_ID,
        "count": len(runs),
        "runs": runs,
        "receipt_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def load_atlas_genius_seeds(root: Path | None = None) -> list[dict[str, Any]]:
    """Read historical company-track ideas without treating them as implementation proof."""
    path = (root or repository_root()) / "excellence" / "grades" / "atlas_company_grades.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: Any = payload
    if isinstance(payload, dict):
        rows = payload.get("companies") or payload.get("grades") or payload.get("items") or []
    if not isinstance(rows, list):
        return []
    seeds: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        genius = row.get("genius_solution") or row.get("genius")
        if genius:
            seeds.append(
                {
                    "company": row.get("company") or row.get("display_name") or row.get("name"),
                    "genius_solution": str(genius),
                    "estate": row.get("estate"),
                    "opportunity": row.get("opp") or row.get("opportunity"),
                }
            )
    return seeds


def render_markdown(run: GeniusRun) -> str:
    lines = [
        "# Genius Engine Run",
        "",
        f"- Engine: `{run.engine_id}`",
        f"- Law: `{run.law}`",
        f"- Receipt: `{run.receipt_sha256}`",
        "",
    ]
    if run.primary is None:
        lines.extend(["## Result", "", "No candidate survived adversarial attack.", ""])
        return "\n".join(lines)

    lines.extend(["## Primary", "", f"### {run.primary.title}", ""])
    for field_name in SOLUTION_FIELDS:
        title = field_name.replace("_", " ").title()
        lines.extend([f"**{title}:** {getattr(run.primary, field_name)}", ""])
    lines.append(
        "Scores: "
        f"genius={run.primary.genius_score:.4f}, "
        f"coherence={run.primary.coherence_score:.4f}, "
        f"novelty={run.primary.novelty_score:.4f}"
    )
    if len(run.solutions) > 1:
        lines.extend(["", "## Ranked alternatives", ""])
        for index, solution in enumerate(run.solutions[1:], start=2):
            lines.append(f"{index}. **{solution.title}** — {solution.genius_score:.4f}")
    return "\n".join(lines) + "\n"


def _subject_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "repository": args.repository,
        "company": getattr(args, "company", None),
        "domain": getattr(args, "domain", None),
        "bottleneck": getattr(args, "bottleneck", None),
        "neutralization_stamps": getattr(args, "neutralization_stamps", 0),
        "paper_recovery_only": getattr(args, "paper_recovery", False),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GlacierEQ Genius Engine")
    subcommands = parser.add_subparsers(dest="command", required=True)

    invent_parser = subcommands.add_parser("invent")
    invent_parser.add_argument("--repository", required=True)
    invent_parser.add_argument("--company")
    invent_parser.add_argument("--domain")
    invent_parser.add_argument("--bottleneck")
    invent_parser.add_argument("--neutralization-stamps", type=int, default=0)
    invent_parser.add_argument("--paper-recovery", action="store_true")
    invent_parser.add_argument("--limit", type=int, default=3)

    restore_parser = subcommands.add_parser("restore")
    restore_parser.add_argument("--repository", required=True)
    restore_parser.add_argument("--limit", type=int, default=3)

    estate_parser = subcommands.add_parser("estate")
    estate_parser.add_argument("subjects", type=Path)
    estate_parser.add_argument("--limit-per", type=int, default=1)

    args = parser.parse_args(argv)
    if args.command == "invent":
        result: Any = invent(_subject_from_args(args), limit=args.limit).to_dict()
    elif args.command == "restore":
        result = invent_restoration({"repository": args.repository}, limit=args.limit).to_dict()
    else:
        payload = json.loads(args.subjects.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise GeniusEngineError("estate subjects must be a JSON list of objects")
        result = invent_estate(payload, limit_per=args.limit_per)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
