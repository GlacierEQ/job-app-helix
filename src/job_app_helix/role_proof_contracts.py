"""Role-specific hiring proof contracts for active campaign targets.

This module keeps one evidence base while projecting different proof orders for
different engineering roles. It deliberately separates campaign-standardized
facts from repository-local verification so recruiter copy stays consistent
without silently upgrading provenance.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any


class RoleProofContractError(ValueError):
    """Raised when role proof projection or copy violates a campaign guardrail."""


@dataclass(frozen=True)
class ProofClaim:
    id: str
    statement: str
    value: int | str
    verification_state: str
    source_refs: tuple[str, ...]
    tags: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoleProfile:
    role_id: str
    company: str
    role: str
    positioning_axis: str
    lead_thesis: str
    proof_order: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    architecture_invariants: tuple[str, ...] = ()
    guardrails: tuple[tuple[str, str], ...] = ()

    def guardrail_dict(self) -> dict[str, str]:
        return dict(self.guardrails)


# The historical branch's static recruiter quantities remain available through
# Git provenance (48202e51bfa14a8c585693df70bf8d4366718d08). They are never executable defaults.
# Only explicit evidence admitted by the current caller may appear as proof.
ROLES: dict[str, RoleProfile] = {
    "scale-public-sector-fdse": RoleProfile(
        role_id="scale-public-sector-fdse",
        company="Scale AI",
        role="Forward Deployed Software Engineer, Public Sector",
        positioning_axis="mission_delivery",
        lead_thesis=(
            "I turn ambiguous customer mission problems into deployed, observable systems "
            "that integrate heterogeneous environments and survive real operational failure."
        ),
        proof_order=(
            "mcp_connectors",
            "control_plane_tests",
            "repositories_shipped_90d",
            "agent_coordinator_tests",
            "estate_repositories",
        ),
        required_capabilities=(
            "customer_edge_integration",
            "provider_readback",
            "failure_recovery",
            "end_to_end_delivery",
            "field_to_platform_feedback",
        ),
        guardrails=(
            ("clearance_claim", "eligibility_only_unless_verified"),
            ("repo_count_role", "supporting_evidence_not_headline"),
            ("framework_jargon", "translate_to_operational_outcomes"),
        ),
    ),
    "clickup-multi-agent-frameworks": RoleProfile(
        role_id="clickup-multi-agent-frameworks",
        company="ClickUp",
        role="Staff AI Engineer, Multi-Agent Frameworks",
        positioning_axis="agent_platform",
        lead_thesis=(
            "I build multi-agent control planes that make increasingly capable agents "
            "reliable, observable, recoverable, and bounded by explicit authority."
        ),
        proof_order=(
            "agent_coordinator_tests",
            "control_plane_tests",
            "mcp_connectors",
            "estate_repositories",
            "repositories_shipped_90d",
        ),
        required_capabilities=(
            "multi_agent_orchestration",
            "evaluation",
            "tool_authority",
            "persistent_context",
            "memory",
            "search_and_retrieval",
        ),
        architecture_invariants=(
            "capability_is_not_authority",
            "returned_is_not_completed",
            "memory_is_not_truth",
        ),
        guardrails=(
            ("repo_count_role", "breadth_evidence_not_architecture_substitute"),
            ("customer_story_role", "supporting_context_not_primary_identity"),
            ("framework_depth", "lead_with_runtime_primitives_and_invariants"),
        ),
    ),
    "anthropic-gtm-ai-engineering": RoleProfile(
        role_id="anthropic-gtm-ai-engineering",
        company="Anthropic",
        role="Staff Software Engineer, GTM AI Engineering",
        positioning_axis="gtm_agent_systems",
        lead_thesis=(
            "I build governed agent systems that turn go-to-market workflows into reliable "
            "automation across tools, models, integrations, and human approval boundaries."
        ),
        proof_order=(
            "agent_coordinator_tests",
            "control_plane_tests",
            "mcp_connectors",
            "repositories_shipped_90d",
            "estate_repositories",
        ),
        required_capabilities=(
            "agent_orchestration",
            "tool_integration",
            "evaluation",
            "human_approval_boundaries",
            "failure_recovery",
            "gtm_workflow_automation",
        ),
        architecture_invariants=(
            "capability_is_not_authority",
            "returned_is_not_completed",
            "memory_is_not_truth",
        ),
        guardrails=(
            ("private_operations", "application_state_excluded_from_public_contract"),
            ("repo_count_role", "supporting_evidence_not_headline"),
        ),
    ),
    "harvey-ai-platform": RoleProfile(
        role_id="harvey-ai-platform",
        company="Harvey",
        role="Senior Software Engineer, AI Platform",
        positioning_axis="high_stakes_ai_platform",
        lead_thesis=(
            "I build shared AI platform primitives for context, memory, model routing, "
            "evaluation, and recovery so high-stakes agent workflows stay reliable at scale."
        ),
        proof_order=(
            "control_plane_tests",
            "agent_coordinator_tests",
            "mcp_connectors",
            "repositories_shipped_90d",
            "estate_repositories",
        ),
        required_capabilities=(
            "context_management",
            "session_state",
            "memory",
            "model_routing",
            "evaluation_infrastructure",
            "shared_platform_abstractions",
            "high_stakes_reliability",
        ),
        architecture_invariants=(
            "memory_is_not_truth",
            "returned_is_not_completed",
            "capability_is_not_authority",
        ),
        guardrails=(
            ("legal_domain_story", "sanitized_or_public_evidence_only"),
            ("repo_count_role", "supporting_evidence_not_headline"),
        ),
    ),
    "vercel-forward-deployed-engineer": RoleProfile(
        role_id="vercel-forward-deployed-engineer",
        company="Vercel",
        role="Forward-Deployed Engineer",
        positioning_axis="ai_customer_deployment",
        lead_thesis=(
            "I turn customer AI requirements into production agent systems, MCP integrations, "
            "and reusable deployment patterns with observable provider-level execution."
        ),
        proof_order=(
            "colossus_gateway_vercel_prod",
            "mcp_connectors",
            "control_plane_tests",
            "agent_coordinator_tests",
            "repositories_shipped_90d",
            "estate_repositories",
        ),
        required_capabilities=(
            "production_ai_delivery",
            "mcp_servers",
            "agentic_workflows",
            "customer_discovery",
            "deployment",
            "provider_readback",
            "reusable_patterns",
        ),
        guardrails=(
            ("deployment_claim", "provider_receipt_required"),
            ("repo_count_role", "supporting_evidence_not_headline"),
        ),
    ),
    "openai-legal-fde": RoleProfile(
        role_id="openai-legal-fde",
        company="OpenAI",
        role="Forward Deployed Engineer (FDE), Legal",
        positioning_axis="legal_workflow_deployment",
        lead_thesis=(
            "I convert complex legal-record workflows into production AI systems with rigorous "
            "retrieval, evaluation, human verification, and reusable deployment patterns."
        ),
        proof_order=(
            "control_plane_tests",
            "mcp_connectors",
            "agent_coordinator_tests",
            "repositories_shipped_90d",
            "estate_repositories",
        ),
        required_capabilities=(
            "legal_record_workflows",
            "retrieval_and_context",
            "evaluation_and_guardrails",
            "human_in_the_loop",
            "production_adoption",
            "reusable_patterns",
        ),
        architecture_invariants=(
            "memory_is_not_truth",
            "returned_is_not_completed",
            "capability_is_not_authority",
        ),
        guardrails=(
            ("private_case_material", "never_expose_without_explicit_authorization"),
            ("location_decision", "user_attestation_required"),
        ),
    ),
    "supabase-ai-tooling": RoleProfile(
        role_id="supabase-ai-tooling",
        company="Supabase",
        role="AI Tooling / Agent Infrastructure",
        positioning_axis="developer_ai_tooling",
        lead_thesis=(
            "I improve the developer-agent loop around MCP, reusable Agent Skills, plugins, "
            "evaluations, and reliable tool execution against real application infrastructure."
        ),
        proof_order=(
            "mcp_connectors",
            "control_plane_tests",
            "agent_coordinator_tests",
            "colossus_gateway_vercel_prod",
            "repositories_shipped_90d",
            "estate_repositories",
        ),
        required_capabilities=(
            "mcp",
            "agent_skills",
            "plugin_tooling",
            "evaluations",
            "developer_experience",
            "upstream_contribution",
        ),
        guardrails=(
            ("opening_state", "contribution_led_until_matching_role_is_live"),
            ("repo_count_role", "supporting_evidence_not_headline"),
        ),
    ),
    "blackstraw-forward-deployed-ai-engineer": RoleProfile(
        role_id="blackstraw-forward-deployed-ai-engineer",
        company="Blackstraw.AI",
        role="Forward Deployed AI Engineer",
        positioning_axis="client_embedded_ai_delivery",
        lead_thesis=(
            "I translate complex AI and platform problems into understandable architecture, "
            "then stay embedded through implementation until the system works in production."
        ),
        proof_order=(
            "mcp_connectors",
            "control_plane_tests",
            "repositories_shipped_90d",
            "agent_coordinator_tests",
            "estate_repositories",
        ),
        required_capabilities=(
            "technical_discovery",
            "client_embedded_delivery",
            "llm_rag_agents",
            "vector_databases",
            "python",
            "typescript",
            "distributed_systems",
            "cloud_native_architecture",
            "executive_stakeholders",
            "production_ai_delivery",
        ),
        architecture_invariants=(
            "capability_is_not_authority",
            "returned_is_not_completed",
        ),
        guardrails=(
            ("calendar_tenure", "never_inflate_to_10_plus_years"),
            ("engagement_identity", "confirm_with_recruiter_do_not_infer"),
            ("client_identity", "never_infer_or_publish_unverified_client"),
            ("repo_count_role", "supporting_evidence_not_headline"),
        ),
    ),
}


_ACTIVE_CLEARANCE_PATTERNS = (
    re.compile(
        r"\bi\s+(?:currently\s+)?(?:hold|have|possess|maintain)\s+"
        r"(?:an?\s+)?active\s+ts[/-]?sci\b",
        re.I,
    ),
    re.compile(r"\bmy\s+active\s+ts[/-]?sci\b", re.I),
    re.compile(r"\bactive\s+ts[/-]?sci(?:\s+clearance)?\b", re.I),
    re.compile(r"\bactive\s+top\s+secret(?:\s+clearance)?\b", re.I),
)

_BLACKSTRAW_TENURE_OVERCLAIM_PATTERNS = (
    re.compile(r"\bi\s+(?:have|bring|offer)\s+(?:more\s+than\s+)?10\+?\s+years\b", re.I),
    re.compile(r"\b10\+?\s+years\s+of\s+(?:software\s+)?engineering\s+experience\b", re.I),
)


_UNSUPPORTED_COPY_PATTERNS = (
    (re.compile(r"\bzero[-\s]+hallucinations?\b", re.I), "zero-hallucination"),
    (re.compile(r"\b1,?000\+?[-\s]?steps?\b", re.I), "1000-step"),
)


def _public_claims(
    profile: RoleProfile,
    admitted_claims: Mapping[str, ProofClaim] | None = None,
) -> list[dict[str, Any]]:
    """Project only explicit, current, source-backed proof supplied by the caller."""
    claims: list[dict[str, Any]] = []
    current = admitted_claims or {}
    allowed_states = {"VERIFIED", "PROVIDER_VERIFIED", "VERIFIED_LOWER_BOUND"}
    for claim_id in profile.proof_order:
        claim = current.get(claim_id)
        if claim is None:
            continue
        if not isinstance(claim, ProofClaim) or claim.id != claim_id:
            raise RoleProofContractError(f"invalid proof identity for {claim_id}")
        if claim.verification_state not in allowed_states:
            raise RoleProofContractError(f"stale or unverified proof for {claim_id}")
        if not claim.source_refs or any(not isinstance(ref, str) or not ref.strip() for ref in claim.source_refs):
            raise RoleProofContractError(f"missing source references for {claim_id}")
        if claim.verification_state == "PROVIDER_VERIFIED" and not any(
            ref.startswith("provider:") for ref in claim.source_refs
        ):
            raise RoleProofContractError(f"provider verification reference missing for {claim_id}")
        claims.append(claim.as_dict())
    return claims


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


_COMPANY_NOISE = frozenset({"ai", "llc", "inc", "corp", "corporation", "company", "co"})
_ROLE_NOISE = frozenset({"staff", "senior", "software", "engineer", "engineering", "ai"})


def _identity_tokens(value: str, *, noise: frozenset[str]) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token and token not in noise
    }


def resolve_role_contract_id(company: str, role: str) -> str | None:
    """Resolve a live opening to one public role contract without company leakage."""

    company_tokens = _identity_tokens(company, noise=_COMPANY_NOISE)
    role_tokens = _identity_tokens(role, noise=_ROLE_NOISE)
    if not company_tokens or not role_tokens:
        return None

    ranked: list[tuple[float, float, str]] = []
    for role_id, profile in ROLES.items():
        profile_company = _identity_tokens(profile.company, noise=_COMPANY_NOISE)
        if profile_company != company_tokens:
            continue
        profile_role = _identity_tokens(profile.role, noise=_ROLE_NOISE)
        if not profile_role:
            continue
        intersection = role_tokens & profile_role
        containment = len(intersection) / min(len(role_tokens), len(profile_role))
        jaccard = len(intersection) / len(role_tokens | profile_role)
        if containment >= 0.6:
            ranked.append((containment, jaccard, role_id))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    best = ranked[0]
    if len(ranked) > 1 and ranked[1][:2] == best[:2]:
        return None
    return best[2]


def role_contract_ids() -> tuple[str, ...]:
    """Return the authoritative role-contract IDs for downstream consumers."""

    return tuple(sorted(ROLES))


def build_role_proof_contract(
    role_id: str,
    *,
    admitted_claims: Mapping[str, ProofClaim] | None = None,
) -> dict[str, Any]:
    """Compile a deterministic, provenance-bearing proof contract for one role."""

    try:
        profile = ROLES[role_id]
    except KeyError as exc:
        raise RoleProofContractError(f"unknown role proof contract: {role_id}") from exc

    public_claims = _public_claims(profile, admitted_claims)
    payload: dict[str, Any] = {
        "schema": "glaciereq.role-proof-contract.v1",
        "role_id": profile.role_id,
        "company": profile.company,
        "role": profile.role,
        "positioning_axis": profile.positioning_axis,
        "lead_thesis": profile.lead_thesis,
        "proof_claims": public_claims,
        "claim_state": "SOURCE_BOUND_INPUT" if public_claims else "NO_CURRENT_EVIDENCE_BOUND",
        "required_capabilities": list(profile.required_capabilities),
        "architecture_invariants": list(profile.architecture_invariants),
        "guardrails": profile.guardrail_dict(),
        "provenance_policy": (
            "only caller-admitted, current, source-backed facts may appear; "
            "historical campaign metrics are not active proof"
        ),
        "presentation_policy": (
            "lead with the strongest substantiated capability; keep verification metadata "
            "structured and concise; surface caveats only when materially necessary"
        ),
    }
    payload["digest"] = _digest(payload)
    return payload


def validate_outreach_copy(
    role_id: str,
    copy: str,
    *,
    evidence_refs: Sequence[str] = (),
) -> None:
    """Reject unsupported recruiter claims unless the required evidence receipt is bound."""

    if role_id not in ROLES:
        raise RoleProofContractError(f"unknown role proof contract: {role_id}")

    for pattern, label in _UNSUPPORTED_COPY_PATTERNS:
        if pattern.search(copy):
            raise RoleProofContractError(f"unsupported {label} claim")

    if role_id == "blackstraw-forward-deployed-ai-engineer":
        for pattern in _BLACKSTRAW_TENURE_OVERCLAIM_PATTERNS:
            if pattern.search(copy):
                raise RoleProofContractError(
                    "calendar tenure claim exceeds supplied candidate history"
                )

    if role_id == "scale-public-sector-fdse":
        clearance_verified = any(
            str(ref).startswith("clearance:provider-verified:")
            for ref in evidence_refs
        )
        for pattern in _ACTIVE_CLEARANCE_PATTERNS:
            if pattern.search(copy) and not clearance_verified:
                raise RoleProofContractError(
                    "active clearance claim requires independently verified clearance evidence"
                )


def main(argv: list[str] | None = None) -> int:
    """Render a role contract as stable JSON for downstream packet generators."""

    import argparse

    parser = argparse.ArgumentParser(
        prog="job-app-helix-role-proof",
        description="Render a role-specific hiring proof contract.",
    )
    parser.add_argument("role_id", choices=sorted(ROLES))
    args = parser.parse_args(argv)

    print(json.dumps(build_role_proof_contract(args.role_id), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
