from __future__ import annotations

import json

import pytest

from job_app_helix.role_proof_contracts import (
    RoleProofContractError,
    build_role_proof_contract,
    role_contract_ids,
    validate_outreach_copy,
)


def test_scale_and_clickup_share_facts_but_not_positioning() -> None:
    scale = build_role_proof_contract("scale-public-sector-fdse")
    clickup = build_role_proof_contract("clickup-multi-agent-frameworks")

    assert scale["positioning_axis"] == "mission_delivery"
    assert clickup["positioning_axis"] == "agent_platform"
    assert scale["lead_thesis"] != clickup["lead_thesis"]

    scale_claims = {claim["id"]: claim for claim in scale["proof_claims"]}
    clickup_claims = {claim["id"]: claim for claim in clickup["proof_claims"]}
    shared = set(scale_claims) & set(clickup_claims)
    assert {"estate_repositories", "repositories_shipped_90d", "mcp_connectors", "control_plane_tests"} <= shared
    for claim_id in shared:
        assert scale_claims[claim_id]["statement"] == clickup_claims[claim_id]["statement"]
        assert scale_claims[claim_id]["value"] == clickup_claims[claim_id]["value"]


def test_scale_prioritizes_field_execution_evidence() -> None:
    contract = build_role_proof_contract("scale-public-sector-fdse")

    assert contract["proof_claims"][0]["id"] == "mcp_connectors"
    assert "customer" in contract["lead_thesis"].lower() or "mission" in contract["lead_thesis"].lower()
    assert "provider_readback" in contract["required_capabilities"]
    assert contract["guardrails"]["clearance_claim"] == "eligibility_only_unless_verified"


def test_clickup_prioritizes_agent_runtime_evidence() -> None:
    contract = build_role_proof_contract("clickup-multi-agent-frameworks")

    assert contract["proof_claims"][0]["id"] == "agent_coordinator_tests"
    assert "multi-agent" in contract["lead_thesis"].lower()
    assert {
        "capability_is_not_authority",
        "returned_is_not_completed",
        "memory_is_not_truth",
    } <= set(contract["architecture_invariants"])


def test_unverified_claims_are_never_projected() -> None:
    scale = build_role_proof_contract("scale-public-sector-fdse")
    clickup = build_role_proof_contract("clickup-multi-agent-frameworks")

    for contract in (scale, clickup):
        assert all(claim["verification_state"] != "UNVERIFIED" for claim in contract["proof_claims"])
        assert "zero hallucinations" not in json.dumps(contract).lower()
        assert "1000-step" not in json.dumps(contract).lower()


def test_scale_copy_rejects_unverified_active_clearance_claim() -> None:
    with pytest.raises(RoleProofContractError, match="active clearance"):
        validate_outreach_copy(
            "scale-public-sector-fdse",
            "I hold an active TS/SCI clearance and can start immediately.",
        )


def test_scale_copy_allows_bounded_clearance_language() -> None:
    validate_outreach_copy(
        "scale-public-sector-fdse",
        "I understand the requirements of cleared environments and can address eligibility accurately in the application.",
    )


def test_role_contract_digest_is_deterministic() -> None:
    first = build_role_proof_contract("clickup-multi-agent-frameworks")
    second = build_role_proof_contract("clickup-multi-agent-frameworks")

    assert first["digest"] == second["digest"]
    assert len(first["digest"]) == 64


def test_priority_campaign_roles_have_distinct_proof_contracts() -> None:
    expected = {
        "anthropic-gtm-ai-engineering": ("Anthropic", "gtm_agent_systems"),
        "harvey-ai-platform": ("Harvey", "high_stakes_ai_platform"),
        "vercel-forward-deployed-engineer": ("Vercel", "ai_customer_deployment"),
        "openai-legal-fde": ("OpenAI", "legal_workflow_deployment"),
        "supabase-ai-tooling": ("Supabase", "developer_ai_tooling"),
        "blackstraw-forward-deployed-ai-engineer": (
            "Blackstraw.AI",
            "client_embedded_ai_delivery",
        ),
    }

    for role_id, (company, axis) in expected.items():
        contract = build_role_proof_contract(role_id)
        assert contract["company"] == company
        assert contract["positioning_axis"] == axis
        assert contract["proof_claims"]
        assert all(
            claim["verification_state"] != "UNVERIFIED"
            for claim in contract["proof_claims"]
        )


def test_vercel_contract_promotes_current_production_readiness() -> None:
    contract = build_role_proof_contract("vercel-forward-deployed-engineer")
    claims = {claim["id"]: claim for claim in contract["proof_claims"]}

    assert contract["proof_claims"][0]["id"] == "colossus_gateway_vercel_prod"
    assert claims["colossus_gateway_vercel_prod"]["value"] == "READY"
    assert (
        "provider:vercel:dpl_3PPqV2axC25HPgRRj7dT3iVbuQY2"
        in claims["colossus_gateway_vercel_prod"]["source_refs"]
    )


def test_recruiter_theses_lead_with_strength_not_disclaimers() -> None:
    for role_id in (
        "scale-public-sector-fdse",
        "clickup-multi-agent-frameworks",
        "anthropic-gtm-ai-engineering",
        "harvey-ai-platform",
        "vercel-forward-deployed-engineer",
        "openai-legal-fde",
        "supabase-ai-tooling",
        "blackstraw-forward-deployed-ai-engineer",
    ):
        contract = build_role_proof_contract(role_id)
        thesis = contract["lead_thesis"].lower()
        assert "unverified" not in thesis
        assert "unsupported" not in thesis
        assert "independent applicant" not in thesis
        assert "no affiliation" not in thesis
        assert contract["presentation_policy"] == (
            "lead with the strongest substantiated capability; keep verification metadata "
            "structured and concise; surface caveats only when materially necessary"
        )


def test_known_unsupported_placeholder_claims_are_not_in_claim_registry() -> None:
    from job_app_helix.role_proof_contracts import CLAIMS

    assert "unsupported_zero_hallucinations" not in CLAIMS
    assert "unsupported_thousand_step" not in CLAIMS


def test_role_contract_ids_expose_every_campaign_contract_for_downstream_clis() -> None:
    assert {
        "scale-public-sector-fdse",
        "clickup-multi-agent-frameworks",
        "anthropic-gtm-ai-engineering",
        "harvey-ai-platform",
        "vercel-forward-deployed-engineer",
        "openai-legal-fde",
        "supabase-ai-tooling",
        "blackstraw-forward-deployed-ai-engineer",
    } == set(role_contract_ids())


def test_recruiter_lead_theses_are_candidate_first_not_job_description_imperatives() -> None:
    for role_id in role_contract_ids():
        thesis = build_role_proof_contract(role_id)["lead_thesis"]
        assert thesis.startswith("I ")


@pytest.mark.parametrize(
    "copy",
    [
        "I have an active TS/SCI.",
        "I possess an active TS/SCI clearance.",
        "I maintain active TS-SCI clearance.",
        "I have an active Top Secret clearance.",
    ],
)
def test_scale_copy_rejects_common_unverified_active_clearance_variants(copy: str) -> None:
    with pytest.raises(RoleProofContractError, match="active clearance"):
        validate_outreach_copy("scale-public-sector-fdse", copy)


def test_scale_copy_allows_verified_active_clearance_when_receipt_is_supplied() -> None:
    validate_outreach_copy(
        "scale-public-sector-fdse",
        "I have an active TS/SCI clearance.",
        evidence_refs=("clearance:provider-verified:receipt-123",),
    )


@pytest.mark.parametrize(
    "copy",
    [
        "The agent has zero-hallucination behavior.",
        "The system runs 1,000-step production agent workflows.",
        "The system runs 1000 steps autonomously.",
        "The system runs 1000-steps autonomously.",
    ],
)
def test_copy_rejects_punctuated_unsupported_claim_variants(copy: str) -> None:
    with pytest.raises(RoleProofContractError, match="unsupported"):
        validate_outreach_copy("clickup-multi-agent-frameworks", copy)


def test_rolling_campaign_claims_are_dated_and_test_count_is_a_verified_lower_bound() -> None:
    contract = build_role_proof_contract("clickup-multi-agent-frameworks")
    claims = {claim["id"]: claim for claim in contract["proof_claims"]}

    assert claims["repositories_shipped_90d"]["statement"] == (
        "862 repositories shipped in the 90 days ending 2026-10-02"
    )
    assert claims["control_plane_tests"]["statement"] == "900+ test control-plane corpus"
    assert claims["control_plane_tests"]["value"] == "900+"
    assert claims["control_plane_tests"]["verification_state"] == "VERIFIED_LOWER_BOUND"
