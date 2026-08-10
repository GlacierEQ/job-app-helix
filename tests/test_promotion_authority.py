from __future__ import annotations

from pathlib import Path

import pytest

from job_app_helix.repo_excellence import (
    REQUIRED_EXCELLENT_GATES,
    ExcellenceContractError,
    allowed_transition,
    validate_repo_excellence_record,
)

ROOT = Path(__file__).resolve().parents[1]


def promoted_record() -> dict[str, object]:
    return {
        "schema": "glaciereq.repo-excellence.record.v1",
        "identity": {
            "repository": "GlacierEQ/example",
            "repository_id": "123456",
            "canonical_head": "a" * 40,
            "default_branch": "main",
            "lineage_action": "verified",
        },
        "state": "PROMOTED",
        "canonical_role": "SPECIALIST_COMPONENT",
        "scores": {
            "target_architecture": 10.0,
            "current_proof": "A",
            "company_fit": 10.0,
            "canonical_confidence": 1.0,
        },
        "gates": {gate: True for gate in REQUIRED_EXCELLENT_GATES},
        "evolution": {"next_gate": "CANONICAL"},
        "proof_receipt": {
            "source_sha": "a" * 40,
            "identity": "receipt-example-001",
        },
    }


def test_promoted_record_requires_every_excellence_gate() -> None:
    payload = promoted_record()
    gates = payload["gates"]
    assert isinstance(gates, dict)
    gates["deterministic_tests_pass"] = False

    with pytest.raises(ExcellenceContractError, match="requires every excellence gate"):
        validate_repo_excellence_record(payload)


@pytest.mark.parametrize(
    ("field", "value", "pattern"),
    [
        ("source_sha", "HYPER_VALIDATED_SHA256", r"placeholder proof_receipt\.source_sha"),
        ("identity", "HYPER_VALIDATED_IDENTITY", r"placeholder proof_receipt\.identity"),
        ("source_sha", "not-a-real-source-digest", "40- or 64-hex digest"),
    ],
)
def test_fabricated_proof_cannot_promote(field: str, value: str, pattern: str) -> None:
    payload = promoted_record()
    receipt = payload["proof_receipt"]
    assert isinstance(receipt, dict)
    receipt[field] = value

    with pytest.raises(ExcellenceContractError, match=pattern):
        validate_repo_excellence_record(payload)


def test_promotion_transition_requires_authority_and_projection_closure() -> None:
    assert not allowed_transition("PROOF_REPRODUCED", "PROMOTED")

    gates = {gate: False for gate in REQUIRED_EXCELLENT_GATES}
    gates["security_authority_bounded"] = True
    assert not allowed_transition("PROOF_REPRODUCED", "PROMOTED", gates)

    gates["projections_truth_consistent"] = True
    assert allowed_transition("PROOF_REPRODUCED", "PROMOTED", gates)


def test_retired_synthetic_promoter_stays_quarantined() -> None:
    assert not (ROOT / "scripts" / "hyper_excellence_engine.py").exists()
