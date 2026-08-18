from __future__ import annotations

import json

import pytest

from job_app_helix.public_proof_runtime import (
    DONOR,
    PROTOCOL,
    PublicProofError,
    main,
    run_launch_campaign,
    run_pair,
    verify_receipt,
)


def test_nominal_campaign_is_green_and_bound_to_retired_donor() -> None:
    receipt = run_launch_campaign("nominal")
    assert receipt["protocol"] == PROTOCOL
    assert receipt["initial_decision"] == "GO"
    assert receipt["final_decision"] == "GO"
    assert receipt["summary"] == {
        "pairs_run": 3,
        "initial_green": 3,
        "final_green": 3,
        "refinements": 0,
    }
    assert receipt["recovery_lineage"]["branch_head"] == DONOR["branch_head"]
    assert receipt["recovery_lineage"]["pull_request"] == 1
    assert verify_receipt(receipt) == (True, ())


def test_recoverable_campaign_proves_no_go_to_go_refinement() -> None:
    receipt = run_launch_campaign("recoverable")
    assert receipt["initial_decision"] == "NO-GO"
    assert receipt["final_decision"] == "GO"
    assert receipt["final_reasons"] == []
    assert receipt["summary"]["refinements"] == 2
    assert receipt["summary"]["final_green"] == 3
    assert verify_receipt(receipt) == (True, ())


def test_terminal_campaign_fails_closed_with_exact_failed_capabilities() -> None:
    receipt = run_launch_campaign("terminal")
    assert receipt["initial_decision"] == "NO-GO"
    assert receipt["final_decision"] == "NO-GO"
    assert receipt["final_reasons"] == ["flight", "propulsion", "ground"]
    assert receipt["summary"]["final_green"] == 0
    assert verify_receipt(receipt) == (True, ())


def test_evidence_hash_is_deterministic_and_observation_time_is_not_proof() -> None:
    first = run_launch_campaign("recoverable", observed_at="2026-08-17T12:00:00Z")
    second = run_launch_campaign("recoverable", observed_at="2026-08-17T13:00:00Z")
    assert first["evidence_sha256"] == second["evidence_sha256"]
    assert first["pairs"] == second["pairs"]
    assert first["observed_at"] != second["observed_at"]
    assert verify_receipt(first) == (True, ())
    assert verify_receipt(second) == (True, ())


def test_tampered_receipt_is_rejected() -> None:
    receipt = run_launch_campaign("nominal")
    receipt["pairs"][0]["final_ok"] = False
    valid, errors = verify_receipt(receipt)
    assert valid is False
    assert "evidence_digest_mismatch" in errors


def test_wrong_donor_lineage_is_rejected_even_with_rehashed_shape() -> None:
    receipt = run_launch_campaign("nominal")
    receipt["recovery_lineage"]["branch_head"] = "0" * 40
    valid, errors = verify_receipt(receipt)
    assert valid is False
    assert "evidence_digest_mismatch" in errors
    assert "donor_lineage_mismatch" in errors


def test_pair_surface_preserves_failure_semantics() -> None:
    nominal = run_pair("ground", "nominal")
    terminal = run_pair("ground", "terminal")
    assert nominal["pair"]["final_ok"] is True
    assert terminal["pair"]["final_ok"] is False
    assert terminal["pair"]["refinements"][0]["status"] == "FAILED"


def test_invalid_pair_and_scenario_fail_explicitly() -> None:
    with pytest.raises(PublicProofError, match="unknown pair"):
        run_pair("imaginary", "nominal")
    with pytest.raises(PublicProofError, match="unknown scenario"):
        run_launch_campaign("imaginary")  # type: ignore[arg-type]


def test_cli_writes_and_reverifies_receipt(tmp_path) -> None:
    receipt_path = tmp_path / "proof.json"
    assert main(["demo", "--scenario", "recoverable", "--output", str(receipt_path)]) == 0
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["final_decision"] == "GO"
    assert main(["verify", str(receipt_path)]) == 0


def test_cli_returns_nonzero_for_terminal_campaign(tmp_path) -> None:
    receipt_path = tmp_path / "terminal.json"
    assert main(["demo", "--scenario", "terminal", "--output", str(receipt_path)]) == 1
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["final_decision"] == "NO-GO"
    assert main(["verify", str(receipt_path)]) == 0
