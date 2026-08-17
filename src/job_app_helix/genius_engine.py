"""Genius Engine — ENGINEERED invent → attack → rank → advance.

APEX identity: counter to canonical destruction.
Execution law: MAXIMUM_COHERENT_ADVANCE.
Core craft verb: ENGINEERED.

Loop: RESEARCH/STUDY (mandatory) → invent → attack → rank → advance brief
       → accumulate lite knowledge → publish library-of-links.

Not theater. Not freeze. Not generated sludge.
Pro elite, humanized, ENGINEERED code — complete, born to run,
first pass is last pass — continuously impressive to masters.
Governance balanced with bravery.

Honesty on planes is labeling. ENGINEERED is how power lands.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any

from job_app_helix.genius_research import (
    ResearchDossier,
    accumulate_knowledge,
    publish_library_link,
    research_subject,
)

ENGINE_ID = "glaciereq.genius-engine.v3"
APEX_IDENTITY = "APEX_IS_THE_COUNTER_TO_CANONICAL_DESTRUCTION"
EXECUTION_LAW = "MAXIMUM_COHERENT_ADVANCE"
CRAFT_VERB = "ENGINEERED"
CRAFT_LAW = "PRO_ELITE_HUMANIZED_ENGINEERED_CODE"
CRAFT_STANDARD: tuple[str, ...] = (
    "ENGINEERED",
    "PRO_ELITE_HUMANIZED_ENGINEERED_CODE",
    "CONTINUOUSLY_IMPRESSIVE_TO_MASTERS",
    "COMPLETE",
    "BORN_TO_RUN",
    "FIRST_PASS_IS_LAST_PASS",
    "GOVERNANCE_BALANCED_WITH_BRAVERY",
)

# Score weights / floors — named, not magic
NOVELTY_WEIGHT = 0.45
COHERENCE_WEIGHT = 0.55
MASTER_GRADE_FLOOR = 0.30
MECHANISM_MIN_CHARS = 40
SLUG_MAX_CHARS = 64
RECEIPT_ID_HEX_CHARS = 12

# Base / delta contributions for novelty & coherence
NOVELTY_BASE = 0.35
NOVELTY_SIGNAL_BONUS = 0.20
NOVELTY_WRAPPER_PENALTY = 0.30
NOVELTY_DOMAIN_BONUS = 0.10
NOVELTY_MISSING_PENALTY = 0.40
NOVELTY_RESTORE_BONUS = 0.15
COHERENCE_BASE = 0.40
COHERENCE_COMPLETE_BONUS = 0.15
COHERENCE_PLANE_BONUS = 0.10
COHERENCE_MCA_BONUS = 0.10
COHERENCE_CRAFT_BONUS = 0.10
COHERENCE_MASTER_BONUS = 0.05
COHERENCE_BOUNDARY_BONUS = 0.05
COHERENCE_RESTORE_BONUS = 0.15
COHERENCE_PARALYSIS_PENALTY = 0.35
COHERENCE_MVP_PENALTY = 0.20

VALID_PLANES = frozenset({"VERIFIED", "IMPLEMENTED", "TARGET"})

PARALYSIS_PATTERNS: tuple[str, ...] = (
    "wait for approval before implementing",
    "defer implement",
    "cannot ship until fully verified",
    "shrink product until green",
    "delete capability",
    "mvp amputation",
    "governance freeze",
    "paper only forever",
)
THEATER_PATTERNS: tuple[str, ...] = (
    "lorem ipsum",
    "tbd",
    "coming soon",
    "as needed",
    "todo later",
    "stub only",
    "scaffold only",
    "thin wrapper",
    "rename only",
)
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


@dataclass(frozen=True)
class MechanismPrimitive:
    """ENGINEERED reusable mechanism (wheel → chassis)."""

    id: str
    name: str
    pattern: str
    domains: tuple[str, ...]

    def as_mapping(self) -> dict[str, str | tuple[str, ...]]:
        return {
            "id": self.id,
            "name": self.name,
            "pattern": self.pattern,
            "domains": self.domains,
        }


# Reusable mechanism primitives (wheel knowledge → chassis innovation)
MECHANISM_LIBRARY: tuple[MechanismPrimitive, ...] = (
    MechanismPrimitive(
        "split_brain_actuation",
        "Mission Assurance Split Brain",
        "Separate policy-decider from actuator; dual-key receipts; neither alone completes side effects.",
        ("control", "security", "ops", "colossus", "spacex"),
    ),
    MechanismPrimitive(
        "authority_half_life",
        "Command Authority Half-life",
        "Cryptographically expiring command tokens; stale authority cannot fire.",
        ("spacex", "ops", "security", "agent"),
    ),
    MechanismPrimitive(
        "thread_quorum",
        "Mission Thread Quorum",
        "Independent planes vote with dissent freeze and deterministic hold codes.",
        ("spacex", "mesh", "ops"),
    ),
    MechanismPrimitive(
        "claim_fence",
        "Claim Fence",
        "Marketing/public claims compile only from proof receipts; unproven language auto-downgrades.",
        ("hire", "portfolio", "docs", "vercel"),
    ),
    MechanismPrimitive(
        "dual_plane_truth",
        "Dual-Plane Truth Router",
        "VERIFIED/IMPLEMENTED/TARGET planes coexist; never delete implemented power to green a smaller harness.",
        ("governance", "portfolio", "mcp", "all"),
    ),
    MechanismPrimitive(
        "capability_restore_queue",
        "Capability Restore Queue",
        "capability-planes.json is a restore ladder with donors and promotion gates, not a memorial of loss.",
        ("governance", "recovery", "all"),
    ),
    MechanismPrimitive(
        "provenance_compulsory",
        "Answer/Actuation Provenance",
        "Every externalized claim or actuation maps to source offsets or signed intent graph; missing map withholds.",
        ("agent", "llm", "legal", "ops"),
    ),
    MechanismPrimitive(
        "entropy_budget_futures",
        "Reasoning Budget Futures",
        "Pre-purchased compute/token envelopes with circuit-break on entropy spike; no silent overspend.",
        ("llm", "agent", "cost"),
    ),
    MechanismPrimitive(
        "receipt_bus",
        "Actuation Receipt Bus",
        "Every command is signed intent with preconditions, abort predicates, and post-condition evidence.",
        ("colossus", "energy", "cooling", "ops"),
    ),
    MechanismPrimitive(
        "lambert_power",
        "Solver Power Expansion",
        "When claims outrun implementation, build the missing solver/mechanism; keep honest non-affiliation labels.",
        ("orbital", "physics", "numerical"),
    ),
    MechanismPrimitive(
        "mcp_package_restore",
        "Provider Surface Restore",
        "Restore credential-gated stdio/MCP packages beside local allowlist routers; dual-plane proof.",
        ("mcp", "integration", "agent"),
    ),
    MechanismPrimitive(
        "anti_neutralization_gate",
        "Anti-Neutralization Merge Gate",
        "CI fails capability shrink or package amputation without OPERATOR_AUTHORIZED_REDUCTION.",
        ("governance", "ci", "all"),
    ),
    MechanismPrimitive(
        "bravery_with_governance",
        "Bravery-Balanced Governance",
        (
            "Honest plane labels (VERIFIED/IMPLEMENTED/TARGET) without freeze: "
            "build the complete born-to-run tranche now; governance gates false claims "
            "and capability deletion, never ambition or first-pass quality."
        ),
        ("governance", "recovery", "all"),
    ),
    MechanismPrimitive(
        "first_pass_last_pass",
        "First Pass Is Last Pass",
        (
            "Ship master-grade complete mechanisms on the first land: no scaffold-to-fix later, "
            "no stub that needs a second personality. Born to run under load and review."
        ),
        ("all", "agent", "ops", "hire", "governance"),
    ),
    MechanismPrimitive(
        "engineered_first_class",
        "Engineered First Class",
        (
            "Every land is ENGINEERED: typed boundaries, named invariants, measured failure modes, "
            "no magic, no placeholder personality — pro elite humanized code masters respect."
        ),
        ("all", "governance", "ops", "agent"),
    ),
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

    def engineered_failures(self) -> tuple[str, ...]:
        """Structural craft failures — not policy freeze."""
        failures: list[str] = []
        missing = self.missing_fields()
        if missing:
            failures.append(f"incomplete_fields:{','.join(missing)}")
        if self.plane not in VALID_PLANES:
            failures.append(f"invalid_plane:{self.plane}")
        if len(self.mechanism.strip()) < MECHANISM_MIN_CHARS:
            failures.append("mechanism_too_shallow")
        blob = " ".join(getattr(self, name) for name in SOLUTION_FIELDS).lower()
        if any(p in blob for p in THEATER_PATTERNS):
            failures.append("not_engineered_theater")
        if any(p in blob for p in PARALYSIS_PATTERNS):
            failures.append("paralysis_or_neutralization_pattern")
        if not isfinite(self.genius_score) or self.genius_score < 0.0 or self.genius_score > 1.0:
            failures.append("invalid_genius_score")
        return tuple(failures)

    def is_engineered(self) -> bool:
        return not self.engineered_failures() and self.genius_score >= MASTER_GRADE_FLOOR


@dataclass(frozen=True)
class GeniusRun:
    """One research → invent → attack → rank → advance cycle."""

    engine_id: str
    identity: str
    law: str
    craft: tuple[str, ...]
    subject: dict[str, Any]
    research: dict[str, Any]
    solutions: tuple[GeniusSolution, ...]
    rejected: tuple[dict[str, Any], ...]
    primary: GeniusSolution | None
    advance_brief: dict[str, Any] | None
    knowledge_path: str | None
    library_link_path: str | None
    receipt_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "identity": self.identity,
            "law": self.law,
            "craft": list(self.craft),
            "subject": self.subject,
            "research": self.research,
            "solutions": [s.to_dict() for s in self.solutions],
            "rejected": list(self.rejected),
            "primary": self.primary.to_dict() if self.primary else None,
            "advance_brief": self.advance_brief,
            "knowledge_path": self.knowledge_path,
            "library_link_path": self.library_link_path,
            "receipt_sha256": self.receipt_sha256,
        }


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s[:SLUG_MAX_CHARS] or "solution"


def _stable_id(*parts: str) -> str:
    raw = "|".join(parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:RECEIPT_ID_HEX_CHARS]
    return f"genius-{digest}"


def _clamp01(x: float) -> float:
    if not isfinite(x):
        return 0.0
    return max(0.0, min(1.0, x))


def genius_composite(novelty: float, coherence: float) -> float:
    """Weighted ENGINEERED score: novelty + coherence."""
    return _clamp01(NOVELTY_WEIGHT * novelty + COHERENCE_WEIGHT * coherence)


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


def infer_domain(
    subject: Mapping[str, Any],
    research: ResearchDossier | None = None,
) -> str:
    if subject.get("domain"):
        return str(subject["domain"])
    name = str(subject.get("repository") or subject.get("name") or "").lower()
    text_parts = [
        name,
        str(subject.get("description") or ""),
        str(subject.get("bottleneck") or ""),
    ]
    if research is not None:
        text_parts.extend(
            [
                research.description,
                research.readme_excerpt[:600],
                " ".join(research.topics),
                " ".join(research.signals),
                research.primary_language,
            ]
        )
    text = " ".join(text_parts).lower()
    rules = (
        ("spacex", ("spacex", "launch", "propulsion", "telemetry", "pad", "mission")),
        ("colossus", ("colossus", "cooling", "thermal", "megapack", "energy", "thermal_energy")),
        ("mcp", ("mcp", "tool-router", "stdio", "mcp_tools")),
        ("orbital", ("orbital", "kepler", "lambert", "astrodynamic")),
        ("agent", ("agent", "llm", "reasoning", "orchestr", "agent_mesh", "megamind")),
        ("hire", ("job-app", "hire", "resume", "portfolio", "recruiter", "hire_surface")),
        ("governance", ("akos", "helix", "governance", "estate", "excellence")),
        ("security", ("security", "auth", "zero-trust", "oidc")),
        ("polyglot", ("babel", "polyglot", "tower-of-babel", "language")),
    )
    for domain, keys in rules:
        if any(k in name or k in text for k in keys):
            return domain
    return "general"


def infer_bottleneck(
    subject: Mapping[str, Any],
    research: ResearchDossier | None = None,
) -> tuple[str, str]:
    """Return (problem, cause) from research + subject — leaf-sensitive."""
    if subject.get("problem") and subject.get("cause"):
        return str(subject["problem"]), str(subject["cause"])

    neut = int(subject.get("neutralization_stamps") or 0)
    missing_impl = bool(subject.get("missing_implementation"))
    paper_only = bool(subject.get("paper_recovery_only"))
    hollow = bool(subject.get("hollow_or_thin"))
    domain = infer_domain(subject, research)
    signals = set(research.signals) if research else set()
    repo = str(subject.get("repository") or (research.full_name if research else "leaf"))
    short = repo.split("/")[-1]
    desc = ""
    if research and research.description:
        desc = research.description.strip()
    elif subject.get("description"):
        desc = str(subject["description"]).strip()

    if neut >= 2 or paper_only or "neutralization" in signals or "paper_recovery" in signals:
        return (
            f"{short}: intended capability was reduced to a local/synthetic/proof-only surface "
            f"so a smaller harness could pass"
            + (f" (surface: {desc[:120]})" if desc else "")
            + ".",
            "Governance-as-denial / truth-harden treated unfinished ambition as defect and "
            "canonicalized the demoted HEAD.",
        )
    if missing_impl or "missing_impl" in signals:
        return (
            f"{short}: public or architectural claims outrun repository-native implementation"
            + (f" — {desc[:120]}" if desc else "")
            + ".",
            "Proof ceiling was used as product ceiling instead of expanding implementation and measurement.",
        )
    if hollow or "hollow" in signals or "tiny_repo" in signals or "scaffold_language" in signals:
        return (
            f"{short}: surface is too thin to demonstrate a defensible mechanism under adversarial review.",
            "Scaffold or stamp work substituted for a minimum-deepest mechanism with tests.",
        )
    if "unknown_or_offline" in signals and domain == "general" and not desc:
        return (
            f"{short}: no reliable leaf signals yet — research found no description, domain, or live surface; "
            "cannot honestly claim a specialized bottleneck.",
            "Subject lacks study density; invent must stay general and refuse overfitted governance stamps.",
        )

    defaults: dict[str, tuple[str, str]] = {
        "spacex": (
            f"{short}: operational planes lack fail-closed coordination under dissent and stale authority.",
            "Independent subsystems can disagree without a deterministic freeze/hold contract.",
        ),
        "colossus": (
            f"{short}: actuation paths can fire without complete precondition and post-condition evidence.",
            "Command path is not receipt-bound end-to-end under thermal/power constraints.",
        ),
        "mcp": (
            f"{short}: tool execution authority is either absent or unbounded relative to host policy.",
            "Local demos were preserved while credentialed provider surfaces were amputated or ungoverned.",
        ),
        "hire": (
            f"{short}: recruiter claims can drift from repository-native evidence.",
            "Projection surfaces are not fail-closed against missing or stale proof receipts.",
        ),
        "governance": (
            f"{short}: estate repair repeatedly converts power into reports.",
            "Minimization was treated as default engineering law.",
        ),
        "orbital": (
            f"{short}: numerical claims outrun a complete, tested solver path for the named mission geometry.",
            "Solver power was left as aspiration while wrappers and prose advanced.",
        ),
        "agent": (
            f"{short}: agent authority and orchestration lack expiring, receipt-bound decision tokens.",
            "Mesh roles were registered without fail-closed actuation provenance.",
        ),
        "polyglot": (
            f"{short}: language placement is not bound to measurable ownership boundaries with native proof.",
            "Polyglot theater risk — languages present without W4H lane contracts.",
        ),
        "security": (
            f"{short}: authority paths lack dual-key or half-life constraints under hostile inputs.",
            "Security policy is documentary rather than executable refuse paths.",
        ),
    }
    if domain in defaults:
        return defaults[domain]
    if desc:
        return (
            f"{short}: has not yet concentrated on one profound bottleneck-removing mechanism "
            f"for its stated surface ({desc[:140]}).",
            "Feature scatter or cosmetic excellence outpaced leverage on the real operational constraint.",
        )
    return (
        f"{short}: has not yet concentrated on one profound bottleneck-removing mechanism.",
        "Feature scatter or cosmetic excellence outpaced leverage on the real operational constraint.",
    )


# Signal → preferred mechanism ids (leaf-native selection, not flagship defaults)
SIGNAL_MECHANISM_BONUS: dict[str, tuple[str, ...]] = {
    "neutralization": ("capability_restore_queue", "dual_plane_truth", "anti_neutralization_gate", "mcp_package_restore"),
    "paper_recovery": ("capability_restore_queue", "dual_plane_truth", "mcp_package_restore", "anti_neutralization_gate"),
    "telemetry": ("thread_quorum", "receipt_bus", "split_brain_actuation", "authority_half_life"),
    "thermal_energy": ("receipt_bus", "split_brain_actuation", "authority_half_life"),
    "mcp_tools": ("mcp_package_restore", "provenance_compulsory", "claim_fence"),
    "orbital": ("lambert_power", "receipt_bus", "provenance_compulsory"),
    "agent_mesh": ("authority_half_life", "provenance_compulsory", "entropy_budget_futures", "thread_quorum"),
    "hire_surface": ("claim_fence", "dual_plane_truth", "first_pass_last_pass"),
    "governance": ("bravery_with_governance", "anti_neutralization_gate", "dual_plane_truth"),
    "polyglot": ("first_pass_last_pass", "engineered_first_class", "claim_fence"),
    "hollow": ("engineered_first_class", "first_pass_last_pass", "dual_plane_truth"),
    "scaffold_language": ("engineered_first_class", "first_pass_last_pass"),
    "missing_impl": ("lambert_power", "engineered_first_class", "capability_restore_queue"),
    "tiny_repo": ("engineered_first_class", "first_pass_last_pass"),
    "unknown_or_offline": ("engineered_first_class", "first_pass_last_pass"),
}


def select_mechanisms(
    domain: str,
    limit: int = 4,
    research: ResearchDossier | None = None,
) -> list[MechanismPrimitive]:
    """Rank mechanisms by domain + research signals — avoid universal anti-neutralization."""
    signals = set(research.signals) if research else set()
    scored: list[tuple[int, MechanismPrimitive]] = []
    for mech in MECHANISM_LIBRARY:
        score = 0
        if domain in mech.domains:
            score += 4
        elif "all" in mech.domains:
            score += 1
        if domain == "general":
            score = max(score, 1)
        for sig in signals:
            if mech.id in SIGNAL_MECHANISM_BONUS.get(sig, ()):
                score += 5
        # Prefer restore/anti-neut only when signals justify it
        if mech.id in {
            "anti_neutralization_gate",
            "capability_restore_queue",
            "dual_plane_truth",
        } and not signals.intersection(
            {"neutralization", "paper_recovery", "governance", "missing_impl"}
        ):
            score -= 3
        # Prefer engineered_first_class for unknown/thin leaves
        if mech.id == "engineered_first_class" and signals.intersection(
            {"unknown_or_offline", "tiny_repo", "hollow", "scaffold_language"}
        ):
            score += 6
        # Prior mechanism diversity: soft penalty for exact repeat
        if research and research.prior_primary_mechanism == mech.id:
            score -= 1
        if score > 0:
            scored.append((score, mech))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    picked = [m for _, m in scored[:limit]]
    if not picked:
        # hard fallback — engineered first class, not anti-neutralization
        by_id = {m.id: m for m in MECHANISM_LIBRARY}
        return [by_id["engineered_first_class"], by_id["first_pass_last_pass"]][:limit]
    return picked


def _leaf_paths(repo: str, mech_id: str, language: str) -> dict[str, str]:
    leaf = repo.split("/")[-1]
    snake = re.sub(r"[^a-z0-9]+", "_", leaf.lower()).strip("_") or "leaf"
    lang = (language or "python").lower()
    if lang in {"typescript", "ts", "javascript", "js"}:
        return {
            "module": f"src/{snake}/{mech_id}.ts",
            "tests": f"src/{snake}/{mech_id}.test.ts",
            "receipt": f"receipts/{mech_id}_proof.json",
            "config": f"src/{snake}/{mech_id}.config.ts",
        }
    if lang in {"go"}:
        return {
            "module": f"internal/{snake}/{mech_id}.go",
            "tests": f"internal/{snake}/{mech_id}_test.go",
            "receipt": f"receipts/{mech_id}_proof.json",
            "config": f"internal/{snake}/{mech_id}_config.go",
        }
    if lang in {"rust"}:
        return {
            "module": f"src/{mech_id}.rs",
            "tests": f"tests/{mech_id}_test.rs",
            "receipt": f"receipts/{mech_id}_proof.json",
            "config": f"src/{mech_id}_config.rs",
        }
    return {
        "module": f"src/{snake}/{mech_id}.py",
        "tests": f"tests/test_{snake}_{mech_id}.py",
        "receipt": f"receipts/{mech_id}_proof.json",
        "config": f"src/{snake}/{mech_id}_config.py",
    }


def build_solution(
    *,
    subject: Mapping[str, Any],
    mech: MechanismPrimitive,
    problem: str,
    cause: str,
    research: ResearchDossier | None = None,
    plane: str = "IMPLEMENTED",
) -> GeniusSolution:
    if plane not in VALID_PLANES:
        raise GeniusEngineError(f"invalid plane: {plane}")
    repo = str(subject.get("repository") or subject.get("name") or (research.full_name if research else "estate"))
    domain = infer_domain(subject, research)
    language = (
        (research.primary_language if research else None)
        or str(subject.get("language") or "Python")
    )
    paths = _leaf_paths(repo, mech.id, language)
    short = repo.split("/")[-1]
    signals = list(research.signals) if research else []
    title = f"{mech.name} for {repo}"

    implementation = (
        f"ENGINEER `{mech.id}` into `{short}` as first-pass-is-last-pass code.\n"
        f"- Module: `{paths['module']}` — typed API for {mech.name}; named invariants; no magic.\n"
        f"- Config: `{paths['config']}` — leaf boundaries from research signals "
        f"[{', '.join(signals[:8]) or 'general'}]; language={language}.\n"
        f"- Wire: call sites that currently embody the bottleneck must route through the mechanism "
        f"(refuse path if preconditions fail).\n"
        f"- Dual-plane: IMPLEMENTED when tests green; VERIFIED only with proof receipt "
        f"`{paths['receipt']}`; keep TARGET north-star.\n"
        f"- MAXIMUM_COHERENT_ADVANCE: land the full coherent tranche now — not a stub."
    )
    measurement = (
        f"1) `{paths['tests']}` — unit tests for happy path + refuse path for {mech.id}.\n"
        f"2) Exact-head proof receipt at `{paths['receipt']}` binding mechanism id + commit.\n"
        f"3) Born-to-run smoke: import/load `{paths['module']}` and exercise one real bottleneck case "
        f"from `{short}`"
        + (
            f" (desc: {research.description[:80]})"
            if research and research.description
            else ""
        )
        + "."
    )
    failure_mode = (
        f"If `{paths['module']}` silent-fails, forges authority, or ships without `{paths['tests']}` "
        f"refuse-path coverage, fail closed. Do not amputate sibling capability to green CI."
    )
    boundary = (
        f"Leaf={repo}; domain={domain}; language={language}. "
        "No false company affiliation; no flight/production authority without proof; "
        "no legal/private data on public hire surface; no capability deletion to green CI; "
        "no governance paralysis blocking a complete born-to-run land."
    )
    value = (
        f"Removes the named bottleneck on `{short}` with ENGINEERED executable power: "
        f"{mech.pattern} — complete mechanism masters can review in `{paths['module']}`."
    )
    if research and research.advanced_context:
        top_k = research.advanced_context[0]
        value += f" Grounded in advanced library knowledge: {top_k[:160]}"
        implementation = (
            implementation
            + f"\n- Knowledge: apply insights from `{top_k.split('|')[0].strip()}` "
            + "(Library of Links impact shelf) without false affiliation claims."
        )
        if research.impact_actions:
            measurement = (
                measurement
                + f"\n4) Impact check: {research.impact_actions[0][:160]}"
            )
    sol = GeniusSolution(
        solution_id=_stable_id(repo, mech.id, problem[:80]),
        title=title,
        problem=problem,
        cause=cause,
        mechanism=f"{mech.name}: {mech.pattern}",
        implementation=implementation,
        measurement=measurement,
        failure_mode=failure_mode,
        boundary=boundary,
        value=value,
        domain=domain,
        repository=repo,
        company_track=str(subject["company"]) if subject.get("company") else None,
        plane=plane,
        tags=(mech.id, domain, EXECUTION_LAW, CRAFT_LAW, CRAFT_VERB),
    )
    novelty = novelty_score(sol, subject, research)
    coherence = coherence_score(sol, subject, research)
    genius = genius_composite(novelty, coherence)
    return GeniusSolution(
        **{
            **sol.to_dict(),
            "novelty_score": novelty,
            "coherence_score": coherence,
            "genius_score": genius,
            "tags": sol.tags,
        }
    )


def novelty_score(
    sol: GeniusSolution,
    subject: Mapping[str, Any],
    research: ResearchDossier | None = None,
) -> float:
    """Score honesty: judge problem/cause/mechanism only — not template boilerplate."""
    # Intentionally exclude implementation text (was self-scoring on craft adjectives).
    core = " ".join([sol.problem, sol.cause, sol.mechanism, sol.value]).lower()
    score = NOVELTY_BASE
    mechanism_signals = (
        "receipt",
        "quorum",
        "half-life",
        "dual-plane",
        "fail closed",
        "provenance",
        "restore",
        "solver",
        "budget",
    )
    if any(k in sol.mechanism.lower() for k in mechanism_signals):
        score += NOVELTY_SIGNAL_BONUS
    if any(k in core for k in ("wrapper", "rename only", "thin scaffold", "todo", "placeholder")):
        score -= NOVELTY_WRAPPER_PENALTY
    # Leaf name in problem = subject-sensitive
    short = (sol.repository or "").split("/")[-1].lower()
    if short and short in sol.problem.lower():
        score += NOVELTY_DOMAIN_BONUS
    if sol.domain != "general" and sol.domain in core:
        score += NOVELTY_DOMAIN_BONUS * 0.5
    if sol.missing_fields():
        score -= NOVELTY_MISSING_PENALTY
    if (subject.get("paper_recovery_only") or (research and "paper_recovery" in research.signals)) and (
        "restore" in sol.mechanism.lower() or "dual-plane" in sol.mechanism.lower()
    ):
        score += NOVELTY_RESTORE_BONUS
    # Research density bonus
    if research and len(research.lite_facts) >= 4:
        score += 0.05
    if research and "unknown_or_offline" in research.signals and sol.domain != "general":
        # overfitted domain without evidence
        score -= 0.1
    # Prefer mechanisms the research signal map selected
    if research and sol.tags:
        preferred: set[str] = set()
        for sig in research.signals:
            preferred.update(SIGNAL_MECHANISM_BONUS.get(sig, ()))
        if sol.tags[0] in preferred:
            score += 0.22
        elif sol.tags[0] in {
            "anti_neutralization_gate",
            "capability_restore_queue",
            "dual_plane_truth",
        } and not set(research.signals).intersection(
            {"neutralization", "paper_recovery", "governance", "missing_impl"}
        ):
            score -= 0.15
    # Path specificity in implementation (leaf-native)
    if sol.repository and sol.repository.split("/")[-1].replace("-", "_") in sol.implementation:
        score += 0.08
    if "test_" in sol.measurement or ".test." in sol.measurement or "_test." in sol.measurement:
        score += 0.05
    return _clamp01(score)


def coherence_score(
    sol: GeniusSolution,
    subject: Mapping[str, Any],
    research: ResearchDossier | None = None,
) -> float:
    """Coherence without rewarding universal craft-adjective spam."""
    score = COHERENCE_BASE
    if not sol.missing_fields():
        score += COHERENCE_COMPLETE_BONUS
    if sol.plane in {"IMPLEMENTED", "VERIFIED"}:
        score += COHERENCE_PLANE_BONUS
    # Leaf-native paths present
    if "Module:" in sol.implementation and "tests" in sol.measurement.lower():
        score += COHERENCE_CRAFT_BONUS
    if "refuse" in sol.measurement.lower() or "refuse" in sol.failure_mode.lower():
        score += COHERENCE_MASTER_BONUS
    if sol.repository and sol.repository.split("/")[-1] in sol.problem:
        score += COHERENCE_BOUNDARY_BONUS
    if "no false" in sol.boundary.lower() or "affiliation" in sol.boundary.lower():
        score += COHERENCE_BOUNDARY_BONUS
    # MCA only if dual-plane wiring named with receipt path
    if "dual-plane" in sol.implementation.lower() and "receipts/" in sol.implementation:
        score += COHERENCE_MCA_BONUS
    neut = bool(subject.get("neutralization_stamps", 0)) or (
        bool(research and research.signals and "neutralization" in research.signals)
    )
    if neut and any(
        k in sol.mechanism.lower() for k in ("restore", "dual-plane", "anti-neutral", "receipt")
    ):
        score += COHERENCE_RESTORE_BONUS
    blob = " ".join([sol.mechanism, sol.implementation, sol.measurement, sol.boundary]).lower()
    if any(p in blob for p in PARALYSIS_PATTERNS):
        score -= COHERENCE_PARALYSIS_PENALTY
    impl = sol.implementation.lower()
    if (
        "mvp" in impl
        and "amputation" not in impl
        and "avoid" not in impl
        and "not" not in impl
    ):
        score -= COHERENCE_MVP_PENALTY
    # Penalize generic anti-neut on unknown leaves
    if research and "unknown_or_offline" in research.signals and (
        "anti-neutralization" in sol.mechanism.lower()
        or (sol.tags and sol.tags[0] == "anti_neutralization_gate")
    ):
        score -= 0.2
    return _clamp01(score)


def attack_solution(sol: GeniusSolution) -> tuple[bool, tuple[str, ...]]:
    """Adversarial gate: must be ENGINEERED — kill theater/paralysis, not ambition."""
    blockers = list(sol.engineered_failures())
    if sol.genius_score < MASTER_GRADE_FLOOR:
        blockers.append("craft_not_yet_master_grade")
    return (not blockers, tuple(blockers))


def compose_advance_brief(run_like: Mapping[str, Any] | GeniusRun) -> dict[str, Any]:
    """Turn primary into an executable advance brief (files, tests, refuse paths)."""
    data = run_like.to_dict() if isinstance(run_like, GeniusRun) else dict(run_like)
    primary = data.get("primary")
    subject = data.get("subject") or {}
    research = data.get("research") or {}
    if not primary:
        return {
            "schema": "glaciereq.genius-advance-brief.v1",
            "status": "NO_PRIMARY",
            "steps": [],
        }
    impl = str(primary.get("implementation") or "")
    modules = re.findall(r"`([^`]+)`", impl)
    return {
        "schema": "glaciereq.genius-advance-brief.v1",
        "status": "READY",
        "repository": primary.get("repository") or subject.get("repository"),
        "mechanism_title": primary.get("title"),
        "mechanism_id": (primary.get("tags") or [None])[0],
        "plane": primary.get("plane"),
        "problem": primary.get("problem"),
        "paths": [p for p in modules if "/" in p or p.endswith((".py", ".ts", ".go", ".rs", ".json"))],
        "measurement": primary.get("measurement"),
        "failure_mode": primary.get("failure_mode"),
        "research_signals": list(research.get("signals") or []),
        "steps": [
            "Create module path from brief with typed public API.",
            "Add refuse-path unit tests before happy path.",
            "Wire bottleneck call sites through the mechanism.",
            "Emit proof receipt JSON bound to commit SHA.",
            "Keep dual-plane labels honest (no false VERIFIED).",
        ],
        "receipt_sha256": data.get("receipt_sha256"),
    }


def invent(
    subject: Mapping[str, Any],
    *,
    limit: int = 3,
    include_atlas_seeds: bool = True,
    root: Path | None = None,
    live_research: bool = True,
    accumulate: bool = True,
    publish_links: bool = True,
) -> GeniusRun:
    """Research → invent → attack → rank → advance brief → accumulate knowledge."""
    if not isinstance(subject, Mapping) or not subject:
        raise GeniusEngineError("subject must be a non-empty mapping")
    if not (subject.get("repository") or subject.get("name")):
        raise GeniusEngineError("subject.repository is required")

    helix_root = root or repository_root()
    # Mandatory research / study
    dossier = research_subject(subject, helix_root=helix_root, live=live_research)
    problem, cause = infer_bottleneck(subject, dossier)
    domain = infer_domain(subject, dossier)
    mechs = select_mechanisms(domain, limit=max(limit, 3), research=dossier)
    candidates: list[GeniusSolution] = []
    rejected: list[dict[str, Any]] = []

    for rank, mech in enumerate(mechs):
        sol = build_solution(
            subject=subject,
            mech=mech,
            problem=problem,
            cause=cause,
            research=dossier,
        )
        # Research-fit rank must beat alphabetical ties on equal genius scores.
        fit_boost = max(0.0, 0.12 - (0.03 * rank))
        if fit_boost:
            boosted = _clamp01(sol.genius_score + fit_boost)
            sol = GeniusSolution(**{**sol.to_dict(), "genius_score": boosted, "tags": sol.tags})
        ok, blockers = attack_solution(sol)
        if ok:
            candidates.append(sol)
        else:
            rejected.append(
                {"solution_id": sol.solution_id, "title": sol.title, "blockers": list(blockers)}
            )

    if include_atlas_seeds and subject.get("company"):
        company = str(subject["company"]).lower()
        for seed in load_atlas_genius_seeds(helix_root):
            seed_company = str(seed.get("company") or "").lower()
            if company not in seed_company and seed_company not in company:
                continue
            genius_text = str(seed["genius_solution"])
            leaf = str(subject.get("repository") or dossier.full_name)
            paths = _leaf_paths(leaf, "atlas_seed", dossier.primary_language)
            sol = GeniusSolution(
                solution_id=_stable_id("atlas", company, genius_text[:80]),
                title=genius_text.split(":")[0][:80],
                problem=problem,
                cause=cause,
                mechanism=genius_text,
                implementation=(
                    f"ENGINEER atlas seed into `{leaf}`:\n"
                    f"- Module: `{paths['module']}`\n"
                    f"- Tests: `{paths['tests']}`\n"
                    f"- Receipt: `{paths['receipt']}`\n"
                    "Independent reference only — no company affiliation."
                ),
                measurement=(
                    f"`{paths['tests']}` must prove the atlas mechanism executable; "
                    f"receipt at `{paths['receipt']}`."
                ),
                failure_mode="Refuse promotion if mechanism is only documented, not executable.",
                boundary="No company affiliation, endorsement, or proprietary access claims.",
                value="Company-track leverage with evidence-coupled originality.",
                domain=domain,
                repository=leaf,
                company_track=str(subject.get("company")),
                plane="TARGET",
                tags=("atlas-seed", domain),
            )
            novelty = novelty_score(sol, subject, dossier)
            coherence = coherence_score(sol, subject, dossier)
            sol = GeniusSolution(
                **{
                    **sol.to_dict(),
                    "novelty_score": novelty,
                    "coherence_score": coherence,
                    "genius_score": genius_composite(novelty, coherence),
                    "tags": sol.tags,
                }
            )
            ok, blockers = attack_solution(sol)
            if ok:
                candidates.append(sol)
            else:
                rejected.append(
                    {
                        "solution_id": sol.solution_id,
                        "title": sol.title,
                        "blockers": list(blockers),
                    }
                )

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
        "research_signals": list(dossier.signals),
    }
    research_out = dossier.to_dict()
    # Drop bulky raw_subject from receipt if present
    research_out.pop("raw_subject", None)

    receipt_body = {
        "engine_id": ENGINE_ID,
        "identity": APEX_IDENTITY,
        "law": EXECUTION_LAW,
        "craft": list(CRAFT_STANDARD),
        "subject": subject_out,
        "research": {
            "repository": research_out.get("repository"),
            "signals": research_out.get("signals"),
            "lite_facts": research_out.get("lite_facts"),
            "sources": research_out.get("sources"),
            "exists": research_out.get("exists"),
        },
        "solutions": [s.to_dict() for s in top],
        "rejected": rejected,
    }
    receipt_sha = hashlib.sha256(
        json.dumps(receipt_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    knowledge_path: str | None = None
    library_path: str | None = None
    primary_dict = primary.to_dict() if primary else None
    if accumulate and primary_dict is not None:
        kpath = accumulate_knowledge(
            dossier,
            helix_root=helix_root,
            primary=primary_dict,
            receipt_sha256=receipt_sha,
        )
        knowledge_path = str(kpath)
    if publish_links and primary_dict is not None:
        lpath = publish_library_link(
            dossier,
            primary=primary_dict,
            receipt_sha256=receipt_sha,
        )
        if lpath is not None:
            library_path = str(lpath)

    run = GeniusRun(
        engine_id=ENGINE_ID,
        identity=APEX_IDENTITY,
        law=EXECUTION_LAW,
        craft=CRAFT_STANDARD,
        subject=subject_out,
        research=research_out,
        solutions=top,
        rejected=tuple(rejected),
        primary=primary,
        advance_brief=None,
        knowledge_path=knowledge_path,
        library_link_path=library_path,
        receipt_sha256=receipt_sha,
    )
    brief = compose_advance_brief(run)
    return GeniusRun(
        engine_id=run.engine_id,
        identity=run.identity,
        law=run.law,
        craft=run.craft,
        subject=run.subject,
        research=run.research,
        solutions=run.solutions,
        rejected=run.rejected,
        primary=run.primary,
        advance_brief=brief,
        knowledge_path=run.knowledge_path,
        library_link_path=run.library_link_path,
        receipt_sha256=run.receipt_sha256,
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
    live_research: bool = True,
    accumulate: bool = True,
    publish_links: bool = True,
) -> dict[str, Any]:
    """Run genius invent across many subjects; return ranked estate plan."""
    runs: list[dict[str, Any]] = []
    for subject in subjects:
        run = invent(
            subject,
            limit=limit_per,
            live_research=live_research,
            accumulate=accumulate,
            publish_links=publish_links,
        )
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
        "craft": list(CRAFT_STANDARD),
        "count": len(runs),
        "runs": runs,
    }


def render_markdown(run: GeniusRun) -> str:
    craft = ", ".join(run.craft)
    signals = ", ".join(run.research.get("signals") or [])
    lines = [
        "# Genius Engine Run",
        "",
        f"- **Engine:** `{run.engine_id}`",
        f"- **Identity:** {run.identity}",
        f"- **Law:** {run.law}",
        f"- **Craft:** {craft}",
        f"- **Subject:** `{run.subject.get('repository') or run.subject.get('domain')}`",
        f"- **Research signals:** {signals or '_none_'}",
        f"- **Knowledge:** `{run.knowledge_path or 'n/a'}`",
        f"- **Library link:** `{run.library_link_path or 'n/a'}`",
        f"- **Receipt:** `{run.receipt_sha256}`",
        "",
    ]
    adv = run.research.get("advanced_context") or []
    if adv:
        lines.append("## Advanced knowledge (Library of Links impact)")
        lines.append("")
        for line in adv[:5]:
            lines.append(f"- {line}")
        lines.append("")

    if run.advance_brief and run.advance_brief.get("status") == "READY":
        paths = ", ".join(f"`{p}`" for p in (run.advance_brief.get("paths") or [])[:8])
        lines.extend(
            [
                "## Advance brief",
                "",
                f"- **Mechanism:** {run.advance_brief.get('mechanism_title')}",
                f"- **Paths:** {paths or '_see implementation_'}",
                "",
            ]
        )
    if not run.solutions:
        lines.append("_No solutions survived adversarial gate._")
        return "\n".join(lines) + "\n"
    for i, sol in enumerate(run.solutions, 1):
        lines.extend(
            [
                f"## {i}. {sol.title}",
                "",
                f"**Scores:** genius={sol.genius_score:.2f} novelty={sol.novelty_score:.2f} "
                f"coherence={sol.coherence_score:.2f} plane={sol.plane}",
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
    """Console entry: invent / restore / advance."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(prog="job-app-helix-genius")
    sub = parser.add_subparsers(dest="cmd", required=True)
    inv = sub.add_parser("invent", help="Research + invent for one subject")
    inv.add_argument("--repository", required=True)
    inv.add_argument("--company")
    inv.add_argument("--limit", type=int, default=3)
    inv.add_argument("--paper-recovery", action="store_true")
    inv.add_argument("--neutralization-stamps", type=int, default=0)
    inv.add_argument("--offline", action="store_true", help="Skip live GitHub research")
    inv.add_argument("--no-accumulate", action="store_true")
    inv.add_argument("--no-publish-links", action="store_true")
    inv.add_argument("--markdown", action="store_true")
    rest = sub.add_parser("restore", help="Restoration invent (neutralization-aware)")
    rest.add_argument("--repository", required=True)
    rest.add_argument("--limit", type=int, default=3)
    rest.add_argument("--offline", action="store_true")
    rest.add_argument("--markdown", action="store_true")
    adv = sub.add_parser("advance", help="Print advance brief for a subject invent")
    adv.add_argument("--repository", required=True)
    adv.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)

    def _run_invent(repo: str, **extra: Any) -> GeniusRun:
        return invent(
            {
                "repository": repo,
                "company": extra.get("company"),
                "paper_recovery_only": extra.get("paper_recovery", False),
                "neutralization_stamps": extra.get("neutralization_stamps", 0),
            },
            limit=int(extra.get("limit") or 3),
            live_research=not extra.get("offline", False),
            accumulate=not extra.get("no_accumulate", False),
            publish_links=not extra.get("no_publish_links", False),
        )

    if args.cmd == "invent":
        run = _run_invent(
            args.repository,
            company=args.company,
            paper_recovery=args.paper_recovery,
            neutralization_stamps=args.neutralization_stamps,
            limit=args.limit,
            offline=args.offline,
            no_accumulate=args.no_accumulate,
            no_publish_links=args.no_publish_links,
        )
    elif args.cmd == "restore":
        run = invent_restoration(
            {"repository": args.repository},
            limit=args.limit,
            live_research=not args.offline,
        )
    else:
        run = _run_invent(args.repository, offline=args.offline, limit=1)
        json.dump(run.advance_brief or {}, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if args.markdown:
        sys.stdout.write(render_markdown(run))
    else:
        json.dump(run.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
