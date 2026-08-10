import json
from pathlib import Path

from job_app_helix.repo_excellence import (
    REQUIRED_EXCELLENT_GATES,
    ExcellenceContractError,
    allowed_transition,
    excellent,
    transition_gate_requirements,
    validate_repo_excellence_record,
)


def valid_record():
    return {
        "schema": "glaciereq.repo-excellence.record.v1",
        "identity": {
            "repository": "GlacierEQ/example",
            "repository_id": "123",
            "canonical_head": "abc",
            "default_branch": "main",
            "lineage_action": "EXTEND_CANONICAL",
        },
        "state": "ADVERSARIAL_VERIFIED",
        "canonical_role": "SPECIALIST_COMPONENT",
        "scores": {
            "target_architecture": 9.5,
            "current_proof": "B",
            "company_fit": 9.0,
            "canonical_confidence": 0.95,
        },
        "gates": {name: False for name in REQUIRED_EXCELLENT_GATES},
        "evolution": {"next_gate": "OPERABLE"},
    }


def test_principal_state_transition_is_exactly_one_step():
    assert allowed_transition("TESTED", "ADVERSARIAL_VERIFIED")
    assert not allowed_transition("TESTED", "OPERABLE")


def test_side_exit_is_always_available_and_reentry_restarts_at_discovery():
    assert allowed_transition("IMPLEMENTED", "BLOCKED")
    assert allowed_transition("BLOCKED", "DISCOVERED")
    assert not allowed_transition("BLOCKED", "TESTED")


def test_proof_reproduced_to_promoted_requires_authority_and_projection_closure():
    requirements = transition_gate_requirements("PROOF_REPRODUCED", "PROMOTED")
    assert requirements == (
        "security_authority_bounded",
        "projections_truth_consistent",
    )
    assert not allowed_transition("PROOF_REPRODUCED", "PROMOTED")

    gates = {name: False for name in REQUIRED_EXCELLENT_GATES}
    gates["security_authority_bounded"] = True
    assert not allowed_transition("PROOF_REPRODUCED", "PROMOTED", gates)

    gates["projections_truth_consistent"] = True
    assert allowed_transition("PROOF_REPRODUCED", "PROMOTED", gates)


def test_promoted_record_must_preserve_earned_projection_closure():
    record = valid_record()
    record["state"] = "PROMOTED"
    record["proof_receipt"] = {"source_sha": "abc", "identity": "receipt:abc"}
    record["gates"]["security_authority_bounded"] = True
    record["gates"]["projections_truth_consistent"] = False

    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "PROOF_REPRODUCED->PROMOTED" in str(exc)
        assert "projections_truth_consistent" in str(exc)
    else:
        raise AssertionError("PROMOTED without projection closure should be rejected")

    record["gates"]["projections_truth_consistent"] = True
    assert validate_repo_excellence_record(record)["state"] == "PROMOTED"


def test_excellent_requires_every_gate_true():
    gates = {name: True for name in REQUIRED_EXCELLENT_GATES}
    assert excellent(gates)
    gates["runtime_behavior_observed"] = False
    assert not excellent(gates)


def test_score_axes_are_independent_and_validated():
    record = valid_record()
    record["scores"] = {
        "target_architecture": 9.8,
        "current_proof": "D",
        "company_fit": 9.8,
        "canonical_confidence": 0.95,
    }
    assert validate_repo_excellence_record(record)["scores"]["current_proof"] == "D"


def test_invalid_proof_grade_fails_closed():
    record = valid_record()
    record["scores"]["current_proof"] = "A+"
    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "current_proof" in str(exc)
    else:
        raise AssertionError("invalid proof grade should be rejected")


def test_proof_reproduced_requires_sha_bound_receipt():
    record = valid_record()
    record["state"] = "PROOF_REPRODUCED"
    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "proof_receipt" in str(exc)
    else:
        raise AssertionError("proof promotion without receipt should be rejected")


def test_unknown_gate_is_rejected():
    record = valid_record()
    record["gates"]["sounds_finished"] = True
    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "unknown excellence gates" in str(exc)
    else:
        raise AssertionError("unknown prose gate should be rejected")


def test_apex_merge_authority_record_is_machine_valid_and_bounded():
    root = Path(__file__).resolve().parents[1]
    record_path = root / "manifests" / "repo_excellence" / "apex-github-worker.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    validated = validate_repo_excellence_record(record)

    assert validated["state"] == "PROMOTED"
    assert validated["scores"]["current_proof"] == "A"
    assert validated["gates"]["runtime_behavior_observed"] is True
    assert validated["gates"]["security_authority_bounded"] is True
    assert validated["gates"]["projections_truth_consistent"] is True
    assert excellent(validated["gates"])
    assert validated["projection_receipt"]["source_ref"] == (
        "commit:577f63c506c6c4df9c1751a0ff5b8fa07822e491"
    )
    assert validated["projection_receipt"]["projection_truth_closed"] is True
    assert validated["evolution"]["next_gate"] == "CANONICAL"
    assert validated["company_evidence"]["stage"] == "PROOF_REPRODUCED"
    assert (
        validated["company_evidence"]["claim_ceiling"]
        == "reproducible_company_specific_proof"
    )
    assert allowed_transition(
        "PROOF_REPRODUCED",
        validated["state"],
        validated["gates"],
    )
    assert allowed_transition(
        validated["state"],
        validated["evolution"]["next_gate"],
        validated["gates"],
    )
