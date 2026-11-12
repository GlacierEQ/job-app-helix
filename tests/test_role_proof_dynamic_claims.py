"""Recovered role-specific proof routing cannot reintroduce stale global counts."""
from __future__ import annotations

import pytest

from job_app_helix.role_proof_contracts import (
    ProofClaim,
    RoleProofContractError,
    build_role_proof_contract,
    role_contract_ids,
)


def test_historical_metrics_are_not_replayed_without_current_source_proof() -> None:
    assert "scale-public-sector-fdse" in role_contract_ids()
    contract = build_role_proof_contract("scale-public-sector-fdse")
    assert contract["proof_claims"] == []
    assert contract["claim_state"] == "NO_CURRENT_EVIDENCE_BOUND"


def test_current_evidence_preserves_role_order_and_the_actual_supplied_value() -> None:
    actual = ProofClaim(
        id="mcp_connectors",
        statement="Connector reachability was verified for this application run",
        value="SOURCE_OBSERVED",
        verification_state="VERIFIED",
        source_refs=("provider:current-execution-readback",),
        tags=("integration", "mcp"),
    )
    contract = build_role_proof_contract(
        "scale-public-sector-fdse", admitted_claims={"mcp_connectors": actual}
    )
    assert len(contract["proof_claims"]) == 1
    assert contract["proof_claims"][0]["statement"] == actual.statement
    assert contract["proof_claims"][0]["value"] == actual.value
    assert contract["claim_state"] == "SOURCE_BOUND_INPUT"


@pytest.mark.parametrize("state,refs", [
    ("CAMPAIGN_STANDARDIZED", ("historical:2026-10-02",)),
    ("UNVERIFIED", ("source:unverified",)),
    ("PROVIDER_VERIFIED", ()),
])
def test_stale_or_unverified_claims_are_rejected(state: str, refs: tuple[str, ...]) -> None:
    claim = ProofClaim(
        id="mcp_connectors",
        statement="A claim that needs source admission",
        value=204,
        verification_state=state,
        source_refs=refs,
        tags=("integration",),
    )
    with pytest.raises(RoleProofContractError):
        build_role_proof_contract("scale-public-sector-fdse", admitted_claims={"mcp_connectors": claim})
