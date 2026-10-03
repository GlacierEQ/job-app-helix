from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.application_engine import find_target, load_targets, resolve_role
from job_app_helix.role_proof_contracts import (
    RoleProofContractError,
    build_role_proof_contract,
    role_contract_ids,
    validate_outreach_copy,
)

ROOT = Path(__file__).resolve().parents[1]


def test_blackstraw_is_first_class_client_embedded_fde_lane() -> None:
    assert "blackstraw-forward-deployed-ai-engineer" in role_contract_ids()

    contract = build_role_proof_contract("blackstraw-forward-deployed-ai-engineer")

    assert contract["company"] == "Blackstraw.AI"
    assert contract["role"] == "Forward Deployed AI Engineer"
    assert contract["positioning_axis"] == "client_embedded_ai_delivery"
    assert contract["proof_claims"][0]["id"] == "mcp_connectors"
    assert {
        "technical_discovery",
        "client_embedded_delivery",
        "llm_rag_agents",
        "vector_databases",
        "distributed_systems",
        "cloud_native_architecture",
        "executive_stakeholders",
    } <= set(contract["required_capabilities"])
    assert contract["guardrails"]["calendar_tenure"] == "never_inflate_to_10_plus_years"
    assert contract["guardrails"]["engagement_identity"] == "confirm_with_recruiter_do_not_infer"


def test_blackstraw_target_resolves_exact_role_with_public_proof() -> None:
    target = find_target("blackstraw_ai", load_targets(ROOT / "manifests"))

    assert target.display_name == "Blackstraw.AI"
    assert (
        resolve_role(target, "Forward Deployed AI Engineer")
        == "Forward Deployed AI Engineer"
    )
    assert target.recruiter_proofs == ()
    contract = build_role_proof_contract("blackstraw-forward-deployed-ai-engineer")
    assert contract["proof_claims"]

    dossier = json.loads(
        (
            ROOT
            / "manifests"
            / "company_dossiers"
            / "blackstraw_ai_role_intelligence_2026_10_02.json"
        ).read_text(encoding="utf-8")
    )
    refs = dossier["companies"][0]["transferable_proof_refs"]
    assert "GlacierEQ/apex-control-plane" in refs
    assert "GlacierEQ/glaciereq-mcp-stack" in refs


def test_blackstraw_copy_rejects_inflated_calendar_tenure_but_allows_gap_framing() -> None:
    with pytest.raises(RoleProofContractError, match="calendar tenure"):
        validate_outreach_copy(
            "blackstraw-forward-deployed-ai-engineer",
            "I have more than 10 years of software engineering experience.",
        )

    validate_outreach_copy(
        "blackstraw-forward-deployed-ai-engineer",
        "On the 10+ years: my depth is concentrated, not calendar-spread.",
    )
