import copy
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

ROOT = Path(__file__).resolve().parents[1]
APEX_RECORD_PATH = ROOT / "manifests/repo_excellence/apex-github-worker.json"


def valid_record():
    return {
        "schema": "glaciereq.repo-excellence.record.v1",
        "identity": {
            "repository": "GlacierEQ/example",
            "repository_id": "123",
            "canonical_head": "a" * 40,
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


def apex_record():
    return json.loads(APEX_RECORD_PATH.read_text(encoding="utf-8"))


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


def test_promoted_to_canonical_requires_every_excellence_gate():
    assert transition_gate_requirements("PROMOTED", "CANONICAL") == REQUIRED_EXCELLENT_GATES
    assert not allowed_transition("PROMOTED", "CANONICAL")
    gates = {name: True for name in REQUIRED_EXCELLENT_GATES}
    assert allowed_transition("PROMOTED", "CANONICAL", gates)
    gates["projections_truth_consistent"] = False
    assert not allowed_transition("PROMOTED", "CANONICAL", gates)


def test_promoted_record_must_preserve_earned_projection_closure():
    record = valid_record()
    record["state"] = "PROMOTED"
    record["proof_receipt"] = {
        "source_sha": "b" * 40,
        "canonical_merge_sha": "a" * 40,
        "identity": "receipt:abc",
    }
    record["gates"] = {name: True for name in REQUIRED_EXCELLENT_GATES}
    record["gates"]["projections_truth_consistent"] = False

    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "requires every excellence gate" in str(exc)
        assert "projections_truth_consistent" in str(exc)
    else:
        raise AssertionError("PROMOTED without projection closure should be rejected")

    record["gates"]["projections_truth_consistent"] = True
    assert validate_repo_excellence_record(record)["state"] == "PROMOTED"


def test_canonical_requires_exact_content_addressed_position_receipt():
    record = apex_record()
    assert validate_repo_excellence_record(record)["state"] == "CANONICAL"
    record["canonical_position_receipt"]["blob_sha"] = "c" * 40
    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "Git blob SHA does not match" in str(exc)
    else:
        raise AssertionError("CANONICAL with mismatched receipt bytes should fail")


def test_canonical_rejects_lineage_conflict_or_duplicate_repo():
    record = apex_record()
    record["canonical_position_receipt"]["lineage_conflict_absent"] = False
    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "lineage_conflict_absent" in str(exc)
    else:
        raise AssertionError("CANONICAL with lineage conflict should fail")

    record = apex_record()
    record["canonical_position_receipt"]["duplicate_repository_rejected"] = False
    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "duplicate_repository_rejected" in str(exc)
    else:
        raise AssertionError("CANONICAL without duplicate-repo rejection should fail")


def test_canonical_requires_company_evidence_and_evolving_as_next_gate():
    record = apex_record()
    missing_company = copy.deepcopy(record)
    del missing_company["company_evidence"]
    try:
        validate_repo_excellence_record(missing_company)
    except ExcellenceContractError as exc:
        assert "requires company_evidence" in str(exc)
    else:
        raise AssertionError("CANONICAL without company evidence should fail")

    record["evolution"]["next_gate"] = "CANONICAL"
    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "EVOLVING" in str(exc)
    else:
        raise AssertionError("CANONICAL next-gate regression should fail")


def test_canonical_requires_all_retained_blockers_classified():
    record = apex_record()
    record["blockers"].append({"id": "unclassified_blocker"})
    try:
        validate_repo_excellence_record(record)
    except ExcellenceContractError as exc:
        assert "do not match retained" in str(exc)
    else:
        raise AssertionError("unclassified CANONICAL blocker should fail")


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


def test_apex_merge_authority_record_is_machine_valid_canonical_and_bounded():
    validated = validate_repo_excellence_record(apex_record())

    assert validated["state"] == "CANONICAL"
    assert validated["canonical_role"] == "SPECIALIST_COMPONENT"
    assert validated["capability_id"] == "merge_authority_graph"
    assert validated["scores"]["current_proof"] == "A"
    assert validated["gates"]["runtime_behavior_observed"] is True
    assert validated["gates"]["security_authority_bounded"] is True
    assert validated["gates"]["projections_truth_consistent"] is True
    assert excellent(validated["gates"])
    assert validated["proof_receipt"]["canonical_merge_sha"] == (
        validated["identity"]["canonical_head"]
    )
    assert validated["projection_receipt"]["projection_truth_closed"] is True
    assert validated["evolution"]["next_gate"] == "EVOLVING"
    assert validated["company_evidence"]["stage"] == "CLAIM_PROMOTED"
    assert validated["company_evidence"]["claim_ceiling"] == "proof_bound_company_specific"
    assert allowed_transition("PROMOTED", validated["state"], validated["gates"])
    assert allowed_transition(
        validated["state"],
        validated["evolution"]["next_gate"],
        validated["gates"],
    )
