"""Genius Engine — invent and score profound engineering mechanisms.

APEX identity: counter to canonical destruction.
Law: MAXIMUM_COHERENT_ADVANCE.

This is not portfolio theater. A genius solution must name a real bottleneck,
propose a mechanism with failure modes and measurement, pass a novelty test,
and prefer the largest coherent executable tranche over MVP amputation.

The Frontier constitution (docs/FRONTIER_REPOSITORY_INNOVATION_ENGINE.md) is the
judgment constitution. This module is the executable invent → attack → rank runtime.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

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

# Reusable mechanism primitives (wheel knowledge → chassis innovation)
MECHANISM_LIBRARY: tuple[dict[str, str], ...] = (
    {
        "id": "split_brain_actuation",
        "name": "Mission Assurance Split Brain",
        "pattern": "Separate policy-decider from actuator; dual-key receipts; neither alone completes side effects.",
        "domains": ("control", "security", "ops", "colossus", "spacex"),
    },
    {
        "id": "authority_half_life",
        "name": "Command Authority Half-life",
        "pattern": "Cryptographically expiring command tokens; stale authority cannot fire.",
        "domains": ("spacex", "ops", "security", "agent"),
    },
    {
        "id": "thread_quorum",
        "name": "Mission Thread Quorum",
        "pattern": "Independent planes vote with dissent freeze and deterministic hold codes.",
        "domains": ("spacex", "mesh", "ops"),
    },
    {
        "id": "claim_fence",
        "name": "Claim Fence",
        "pattern": "Marketing/public claims compile only from proof receipts; unproven language auto-downgrades.",
        "domains": ("hire", "portfolio", "docs", "vercel"),
    },
    {
        "id": "dual_plane_truth",
        "name": "Dual-Plane Truth Router",
        "pattern": "VERIFIED/IMPLEMENTED/TARGET planes coexist; never delete implemented power to green a smaller harness.",
        "domains": ("governance", "portfolio", "mcp", "all"),
    },
    {
        "id": "capability_restore_queue",
        "name": "Capability Restore Queue",
        "pattern": "capability-planes.json is a restore ladder with donors and promotion gates, not a memorial of loss.",
        "domains": ("governance", "recovery", "all"),
    },
    {
        "id": "provenance_compulsory",
        "name": "Answer/Actuation Provenance",
        "pattern": "Every externalized claim or actuation maps to source offsets or signed intent graph; missing map withholds.",
        "domains": ("agent", "llm", "legal", "ops"),
    },
    {
        "id": "entropy_budget_futures",
        "name": "Reasoning Budget Futures",
        "pattern": "Pre-purchased compute/token envelopes with circuit-break on entropy spike; no silent overspend.",
        "domains": ("llm", "agent", "cost"),
    },
    {
        "id": "receipt_bus",
        "name": "Actuation Receipt Bus",
        "pattern": "Every command is signed intent with preconditions, abort predicates, and post-condition evidence.",
        "domains": ("colossus", "energy", "cooling", "ops"),
    },
    {
        "id": "lambert_power",
        "name": "Solver Power Expansion",
        "pattern": "When claims outrun implementation, build the missing solver/mechanism; keep honest non-affiliation labels.",
        "domains": ("orbital", "physics", "numerical"),
    },
    {
        "id": "mcp_package_restore",
        "name": "Provider Surface Restore",
        "pattern": "Restore credential-gated stdio/MCP packages beside local allowlist routers; dual-plane proof.",
        "domains": ("mcp", "integration", "agent"),
    },
    {
        "id": "anti_neutralization_gate",
        "name": "Anti-Neutralization Merge Gate",
        "pattern": "CI fails capability shrink or package amputation without OPERATOR_AUTHORIZED_REDUCTION.",
        "domains": ("governance", "ci", "all"),
    },
)


class GeniusEngineError(ValueError):
    """Invalid genius-engine input or invariant violation."""


@dataclass(frozen=True)
class GeniusSolution:
    """One profound mechanism, fully specified."""

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
    plane: str = "IMPLEMENTED"  # VERIFIED | IMPLEMENTED | TARGET
    novelty_score: float = 0.0
    coherence_score: float = 0.0
    genius_score: float = 0.0
    apex_aligned: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def missing_fields(self) -> tuple[str, ...]:
        missing = []
        for name in SOLUTION_FIELDS:
            val = getattr(self, name)
            if not isinstance(val, str) or not val.strip():
                missing.append(name)
        return tuple(missing)


@dataclass(frozen=True)
class GeniusRun:
    """One invent → attack → rank cycle."""

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
            "solutions": [s.to_dict() for s in self.solutions],
            "rejected": list(self.rejected),
            "primary": self.primary.to_dict() if self.primary else None,
            "receipt_sha256": self.receipt_sha256,
        }


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s[:64] or "solution"


def _stable_id(*parts: str) -> str:
    raw = "|".join(parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"genius-{digest}"


def _clamp01(x: float) -> float:
    if not isfinite(x):
        return 0.0
    return max(0.0, min(1.0, x))


def load_atlas_genius_seeds(root: Path | None = None) -> list[dict[str, Any]]:
    """Load company-track genius solutions already captured in helix grades."""
    base = root or repository_root()
    path = base / "excellence" / "grades" / "atlas_company_grades.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("companies") or payload.get("grades") or payload
    if isinstance(payload, dict) and "companies" not in payload and "grades" not in payload:
        # maybe list at top or nested
        for key in ("items", "scorecard", "results"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
    if not isinstance(rows, list):
        return []
    seeds: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        genius = row.get("genius_solution") or row.get("genius")
        if not genius:
            continue
        seeds.append(
            {
                "company": row.get("company") or row.get("display_name") or row.get("name"),
                "genius_solution": str(genius),
                "estate": row.get("estate"),
                "opportunity": row.get("opp") or row.get("opportunity"),
            }
        )
    return seeds


def infer_domain(subject: Mapping[str, Any]) -> str:
    name = str(subject.get("repository") or subject.get("name") or "").lower()
    text = " ".join(
        str(subject.get(k) or "")
        for k in ("repository", "name", "description", "bottleneck", "domain", "tags")
    ).lower()
    rules = (
        ("spacex", ("spacex", "launch", "orbital", "propulsion", "telemetry", "pad")),
        ("colossus", ("colossus", "cooling", "thermal", "megapack", "energy")),
        ("mcp", ("mcp", "tool-router", "stdio")),
        ("orbital", ("orbital", "kepler", "lambert", "astrodynamic")),
        ("agent", ("agent", "llm", "reasoning", "orchestr")),
        ("hire", ("job-app", "hire", "resume", "portfolio", "recruiter")),
        ("governance", ("akos", "helix", "governance", "estate", "excellence")),
        ("security", ("security", "auth", "zero-trust", "oidc")),
    )
    for domain, keys in rules:
        if any(k in name or k in text for k in keys):
            return domain
    return str(subject.get("domain") or "general")


def infer_bottleneck(subject: Mapping[str, Any]) -> tuple[str, str]:
    """Return (problem, cause) from subject signals."""
    if subject.get("problem") and subject.get("cause"):
        return str(subject["problem"]), str(subject["cause"])

    neut = int(subject.get("neutralization_stamps") or 0)
    missing_impl = bool(subject.get("missing_implementation"))
    paper_only = bool(subject.get("paper_recovery_only"))
    hollow = bool(subject.get("hollow_or_thin"))
    domain = infer_domain(subject)

    if neut >= 2 or paper_only:
        return (
            "Intended product capability was reduced to a local/synthetic/proof-only surface so a smaller harness could pass.",
            "Governance-as-denial / truth-harden treated unfinished ambition as defect and canonicalized the demoted HEAD.",
        )
    if missing_impl:
        return (
            "Public or architectural claims outrun the repository-native implementation.",
            "Proof ceiling was used as product ceiling instead of expanding implementation and measurement.",
        )
    if hollow:
        return (
            "Repository surface is too thin to demonstrate a defensible mechanism under adversarial review.",
            "Scaffold or stamp work substituted for a minimum-deepest mechanism with tests.",
        )
    defaults = {
        "spacex": (
            "Operational planes lack a fail-closed coordination mechanism under dissent and stale authority.",
            "Independent subsystems can disagree without a deterministic freeze/hold contract.",
        ),
        "colossus": (
            "Actuation paths can fire without complete precondition and post-condition evidence.",
            "Command path is not receipt-bound end-to-end under thermal/power constraints.",
        ),
        "mcp": (
            "Tool execution authority is either absent or unbounded relative to host policy.",
            "Local demos were preserved while credentialed provider surfaces were amputated or ungoverned.",
        ),
        "hire": (
            "Recruiter claims can drift from repository-native evidence.",
            "Projection surfaces are not fail-closed against missing or stale proof receipts.",
        ),
        "governance": (
            "Estate repair repeatedly converts power into reports.",
            "Minimization was treated as default engineering law.",
        ),
    }
    return defaults.get(
        domain,
        (
            "The repository has not yet concentrated on one profound bottleneck-removing mechanism.",
            "Feature scatter or cosmetic excellence outpaced leverage on the real operational constraint.",
        ),
    )


def select_mechanisms(domain: str, limit: int = 4) -> list[dict[str, str]]:
    scored: list[tuple[int, dict[str, str]]] = []
    for mech in MECHANISM_LIBRARY:
        domains = mech.get("domains", ())
        score = 2 if domain in domains else 1 if "all" in domains else 0
        if domain == "general":
            score = max(score, 1)
        if score:
            scored.append((score, mech))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [m for _, m in scored[:limit]]


def build_solution(
    *,
    subject: Mapping[str, Any],
    mech: Mapping[str, str],
    problem: str,
    cause: str,
    plane: str = "IMPLEMENTED",
) -> GeniusSolution:
    repo = subject.get("repository") or subject.get("name")
    domain = infer_domain(subject)
    title = f"{mech['name']}"
    if repo:
        title = f"{mech['name']} for {repo}"
    implementation = (
        f"Implement `{mech['id']}` in repository-native modules with dual-plane truth: "
        f"keep honest VERIFIED labels; land the mechanism on the IMPLEMENTED plane; "
        f"preserve TARGET north-star. Prefer MAXIMUM_COHERENT_ADVANCE over MVP amputation."
    )
    measurement = (
        "Exact-head tests for mechanism invariants; refuse-path unit tests; "
        "before/after proof receipts; optional benchmark only when measured."
    )
    failure_mode = (
        "Mechanism silent-fail, authority forgery, receipt graph incomplete, "
        "or claim/promotion without evidence must fail closed."
    )
    boundary = (
        "No false company affiliation; no flight/production authority claims without proof; "
        "no legal/private data on public hire surface; no capability deletion to green CI."
    )
    value = (
        "Removes the named bottleneck while increasing evidence-coupled executable power — "
        "the unit of APEX completion."
    )
    sol = GeniusSolution(
        solution_id=_stable_id(str(repo or "estate"), mech["id"], problem[:80]),
        title=title,
        problem=problem,
        cause=cause,
        mechanism=f"{mech['name']}: {mech['pattern']}",
        implementation=implementation,
        measurement=measurement,
        failure_mode=failure_mode,
        boundary=boundary,
        value=value,
        domain=domain,
        repository=str(repo) if repo else None,
        company_track=str(subject["company"]) if subject.get("company") else None,
        plane=plane,
        tags=(mech["id"], domain, EXECUTION_LAW),
    )
    novelty = novelty_score(sol, subject)
    coherence = coherence_score(sol, subject)
    genius = _clamp01(0.45 * novelty + 0.55 * coherence)
    return GeniusSolution(
        **{
            **sol.to_dict(),
            "novelty_score": novelty,
            "coherence_score": coherence,
            "genius_score": genius,
            "tags": sol.tags,
        }
    )


def novelty_score(sol: GeniusSolution, subject: Mapping[str, Any]) -> float:
    """Heuristic novelty: mechanism specificity + non-wrapper language + domain fit."""
    text = " ".join(
        [
            sol.mechanism,
            sol.implementation,
            sol.problem,
            sol.value,
        ]
    ).lower()
    score = 0.35
    if any(k in text for k in ("receipt", "quorum", "half-life", "dual-plane", "fail closed", "provenance")):
        score += 0.2
    if any(k in text for k in ("wrapper", "rename only", "thin scaffold", "todo", "placeholder")):
        score -= 0.3
    if sol.domain != "general" and sol.domain in text:
        score += 0.1
    if sol.missing_fields():
        score -= 0.4
    if subject.get("paper_recovery_only") and "restore" in text:
        score += 0.15
    return _clamp01(score)


def coherence_score(sol: GeniusSolution, subject: Mapping[str, Any]) -> float:
    """How well solution advances maximum coherent power without false claims."""
    score = 0.4
    if not sol.missing_fields():
        score += 0.2
    if sol.plane in {"IMPLEMENTED", "VERIFIED"}:
        score += 0.1
    if "MAXIMUM_COHERENT_ADVANCE" in sol.implementation or "dual-plane" in sol.implementation.lower():
        score += 0.15
    if "no false" in sol.boundary.lower() or "affiliation" in sol.boundary.lower():
        score += 0.1
    if subject.get("neutralization_stamps", 0) and any(
        k in sol.mechanism.lower() for k in ("restore", "dual-plane", "anti-neutral", "receipt")
    ):
        score += 0.15
    if "mvp" in sol.implementation.lower() and "avoid" not in sol.implementation.lower():
        score -= 0.2
    return _clamp01(score)


def attack_solution(sol: GeniusSolution) -> tuple[bool, tuple[str, ...]]:
    """Adversarial gate: survive only if fully specified and non-theatrical."""
    blockers: list[str] = []
    missing = sol.missing_fields()
    if missing:
        blockers.append(f"incomplete_fields:{','.join(missing)}")
    blob = " ".join(sol.to_dict()[k] for k in SOLUTION_FIELDS).lower()
    if any(x in blob for x in ("lorem ipsum", "tbd", "coming soon", "as needed")):
        blockers.append("placeholder_language")
    if sol.genius_score < 0.35:
        blockers.append("genius_score_below_floor")
    if len(sol.mechanism) < 40:
        blockers.append("mechanism_too_shallow")
    if "delete capability" in blob or "shrink product until" in blob:
        blockers.append("neutralization_pattern")
    return (not blockers, tuple(blockers))


def invent(
    subject: Mapping[str, Any],
    *,
    limit: int = 3,
    include_atlas_seeds: bool = True,
    root: Path | None = None,
) -> GeniusRun:
    """Invent ranked genius solutions for a repository/company subject."""
    if not isinstance(subject, Mapping) or not subject:
        raise GeniusEngineError("subject must be a non-empty mapping")

    problem, cause = infer_bottleneck(subject)
    domain = infer_domain(subject)
    mechs = select_mechanisms(domain, limit=max(limit, 3))
    candidates: list[GeniusSolution] = []
    rejected: list[dict[str, Any]] = []

    for mech in mechs:
        sol = build_solution(subject=subject, mech=mech, problem=problem, cause=cause)
        ok, blockers = attack_solution(sol)
        if ok:
            candidates.append(sol)
        else:
            rejected.append({"solution_id": sol.solution_id, "title": sol.title, "blockers": list(blockers)})

    if include_atlas_seeds and subject.get("company"):
        company = str(subject["company"]).lower()
        for seed in load_atlas_genius_seeds(root):
            seed_company = str(seed.get("company") or "").lower()
            if company not in seed_company and seed_company not in company:
                continue
            genius_text = str(seed["genius_solution"])
            sol = GeniusSolution(
                solution_id=_stable_id("atlas", company, genius_text[:80]),
                title=genius_text.split(":")[0][:80],
                problem=problem,
                cause=cause,
                mechanism=genius_text,
                implementation=(
                    "Translate the atlas genius solution into repository-native modules with tests, "
                    "receipts, and dual-plane promotion. Independent reference only — no company affiliation."
                ),
                measurement="Repository-native tests + exact-head proof receipt bound to the mechanism.",
                failure_mode="Refuse promotion if mechanism is only documented, not executable.",
                boundary="No company affiliation, endorsement, or proprietary access claims.",
                value="Company-track leverage with evidence-coupled originality.",
                domain=domain,
                repository=str(subject.get("repository") or "") or None,
                company_track=str(subject.get("company")),
                plane="TARGET",
                tags=("atlas-seed", domain),
            )
            novelty = novelty_score(sol, subject)
            coherence = coherence_score(sol, subject)
            sol = GeniusSolution(
                **{
                    **sol.to_dict(),
                    "novelty_score": novelty,
                    "coherence_score": coherence,
                    "genius_score": _clamp01(0.45 * novelty + 0.55 * coherence),
                    "tags": sol.tags,
                }
            )
            ok, blockers = attack_solution(sol)
            if ok:
                candidates.append(sol)
            else:
                rejected.append({"solution_id": sol.solution_id, "title": sol.title, "blockers": list(blockers)})

    candidates.sort(key=lambda s: (-s.genius_score, s.title))
    top = tuple(candidates[:limit])
    primary = top[0] if top else None
    subject_out = {
        "repository": subject.get("repository") or subject.get("name"),
        "company": subject.get("company"),
        "domain": domain,
        "problem": problem,
        "cause": cause,
        "neutralization_stamps": subject.get("neutralization_stamps"),
        "paper_recovery_only": subject.get("paper_recovery_only"),
    }
    receipt_body = {
        "engine_id": ENGINE_ID,
        "identity": APEX_IDENTITY,
        "law": EXECUTION_LAW,
        "subject": subject_out,
        "solutions": [s.to_dict() for s in top],
        "rejected": rejected,
    }
    receipt_sha = hashlib.sha256(
        json.dumps(receipt_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return GeniusRun(
        engine_id=ENGINE_ID,
        identity=APEX_IDENTITY,
        law=EXECUTION_LAW,
        subject=subject_out,
        solutions=top,
        rejected=tuple(rejected),
        primary=primary,
        receipt_sha256=receipt_sha,
    )


def invent_restoration(subject: Mapping[str, Any], **kwargs: Any) -> GeniusRun:
    """Specialize invent for neutralized repositories (APEX restore mode)."""
    enriched = dict(subject)
    enriched.setdefault("paper_recovery_only", True)
    enriched["neutralization_stamps"] = max(int(enriched.get("neutralization_stamps") or 0), 2)
    return invent(enriched, **kwargs)


def invent_estate(
    subjects: Sequence[Mapping[str, Any]],
    *,
    limit_per: int = 1,
) -> dict[str, Any]:
    """Run genius invent across many subjects; return ranked estate plan."""
    runs: list[dict[str, Any]] = []
    for subject in subjects:
        run = invent(subject, limit=limit_per)
        runs.append(run.to_dict())
    runs.sort(
        key=lambda r: (
            -(r["primary"]["genius_score"] if r.get("primary") else 0.0),
            str((r.get("subject") or {}).get("repository") or ""),
        )
    )
    return {
        "engine_id": ENGINE_ID,
        "identity": APEX_IDENTITY,
        "law": EXECUTION_LAW,
        "count": len(runs),
        "runs": runs,
    }


def render_markdown(run: GeniusRun) -> str:
    lines = [
        f"# Genius Engine Run",
        "",
        f"- **Engine:** `{run.engine_id}`",
        f"- **Identity:** {run.identity}",
        f"- **Law:** {run.law}",
        f"- **Subject:** `{run.subject.get('repository') or run.subject.get('domain')}`",
        f"- **Receipt:** `{run.receipt_sha256}`",
        "",
    ]
    if not run.solutions:
        lines.append("_No solutions survived adversarial gate._")
        return "\n".join(lines) + "\n"
    for i, sol in enumerate(run.solutions, 1):
        lines.extend(
            [
                f"## {i}. {sol.title}",
                "",
                f"**Scores:** genius={sol.genius_score:.2f} novelty={sol.novelty_score:.2f} coherence={sol.coherence_score:.2f} plane={sol.plane}",
                "",
                f"- **Problem:** {sol.problem}",
                f"- **Cause:** {sol.cause}",
                f"- **Mechanism:** {sol.mechanism}",
                f"- **Implementation:** {sol.implementation}",
                f"- **Measurement:** {sol.measurement}",
                f"- **Failure mode:** {sol.failure_mode}",
                f"- **Boundary:** {sol.boundary}",
                f"- **Value:** {sol.value}",
                "",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Console entry: delegates to scripts/genius_engine semantics via invent defaults."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(prog="job-app-helix-genius")
    sub = parser.add_subparsers(dest="cmd", required=True)
    inv = sub.add_parser("invent")
    inv.add_argument("--repository", required=True)
    inv.add_argument("--company")
    inv.add_argument("--limit", type=int, default=3)
    inv.add_argument("--paper-recovery", action="store_true")
    inv.add_argument("--neutralization-stamps", type=int, default=0)
    inv.add_argument("--markdown", action="store_true")
    rest = sub.add_parser("restore")
    rest.add_argument("--repository", required=True)
    rest.add_argument("--limit", type=int, default=3)
    rest.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "invent":
        run = invent(
            {
                "repository": args.repository,
                "company": args.company,
                "paper_recovery_only": args.paper_recovery,
                "neutralization_stamps": args.neutralization_stamps,
            },
            limit=args.limit,
        )
    else:
        run = invent_restoration({"repository": args.repository}, limit=args.limit)
    if args.markdown:
        sys.stdout.write(render_markdown(run))
    else:
        json.dump(run.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
