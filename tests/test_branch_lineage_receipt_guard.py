"""Fail-closed branch-lineage receipt validation from the surviving innovation donor."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from job_app_helix.library_program import (
    LibraryProgramError,
    validate_latest_execution_receipt,
    validate_library_program,
)

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "manifests/library_priority_spine.json"


def _state() -> tuple[dict, dict]:
    program = json.loads(PROGRAM.read_text(encoding="utf-8"))
    receipt = json.loads((ROOT / program["latest_execution_receipt"]).read_text(encoding="utf-8"))
    return program, receipt


def _validate_modified(tmp_path: Path, program: dict, receipt: dict) -> dict:
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    program_path = manifests / "library_priority_spine.json"
    program_path.write_text(json.dumps(program), encoding="utf-8")
    receipt_path = tmp_path / program["latest_execution_receipt"]
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    provenance = receipt.get("historical_source_receipt")
    if provenance:
        source_path = tmp_path / provenance["path"]
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes((ROOT / provenance["path"]).read_bytes())
    return validate_latest_execution_receipt(program_path, validate_library_program(program_path))


def test_active_receipt_never_directs_remote_branch_deletion() -> None:
    _, receipt = _state()
    validate_latest_execution_receipt(PROGRAM, validate_library_program(PROGRAM))
    for outcome in receipt["outcomes"]:
        for directive in (outcome, *outcome.get("branch_dispositions", [])):
            action = directive.get("remote_ref_disposition", "")
            assert not any(word in action for word in ("DELETE", "DISCARD", "REMOVE_REF"))


def test_validator_rejects_destructive_ref_disposition(tmp_path: Path) -> None:
    program, receipt = _state()
    receipt = copy.deepcopy(receipt)
    receipt["outcomes"][0]["remote_ref_disposition"] = "DELETE_REF_REQUIRED"
    with pytest.raises(LibraryProgramError, match="destructive remote-ref disposition"):
        _validate_modified(tmp_path, program, receipt)


def test_validator_rejects_unproven_zero_unique_value(tmp_path: Path) -> None:
    program, receipt = _state()
    receipt = copy.deepcopy(receipt)
    receipt["outcomes"][0]["unique_value"] = "NONE"
    receipt["outcomes"][0]["remote_ref_disposition"] = "PRESERVE_DRAINED_LINEAGE"
    with pytest.raises(LibraryProgramError, match="unique_contribution_verification"):
        _validate_modified(tmp_path, program, receipt)


def test_validator_accepts_structural_preservation_proof(tmp_path: Path) -> None:
    # Synthetic input exercises structure; it does not claim a real GitHub readback.
    program, receipt = _state()
    receipt = copy.deepcopy(receipt)
    receipt["outcomes"][0]["unique_value"] = "NONE"
    receipt["outcomes"][0]["remote_ref_disposition"] = "PRESERVE_DRAINED_LINEAGE"
    receipt["outcomes"][0]["unique_contribution_verification"] = {
        "verdict": "ZERO",
        "provider_readback_refs": ["synthetic-test://verified-branch-evidence"],
        "lineage_preserved": True,
    }
    accepted = _validate_modified(tmp_path, program, receipt)
    assert accepted["outcomes"][0]["remote_ref_disposition"] == "PRESERVE_DRAINED_LINEAGE"


def test_validator_rejects_tampered_historical_receipt_digest(tmp_path: Path) -> None:
    program, receipt = _state()
    receipt = copy.deepcopy(receipt)
    receipt["historical_source_receipt"]["sha256"] = "0" * 64
    with pytest.raises(LibraryProgramError, match="historical source receipt digest mismatch"):
        _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize(
    "disposition",
    [None, [], {}, ["DELETE_REF_REQUIRED"], {"action": "DELETE_REF_REQUIRED"}, "", "  ", 0, False],
)
def test_validator_rejects_malformed_dispositions(
    tmp_path: Path, nested: bool, disposition: object
) -> None:
    program, receipt = _state()
    directive = {"remote_ref_disposition": disposition}
    if nested:
        receipt["outcomes"][0]["branch_dispositions"] = [directive]
    else:
        receipt["outcomes"][0].update(directive)
    with pytest.raises(LibraryProgramError, match="remote_ref_disposition must be non-empty text"):
        _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize(
    "disposition",
    [
        "RETIRE_REF_REQUIRED",
        "KILL_REF",
        "SUPERSEDE_REF",
        "CONSOLIDATE_REF",
        "remove-ref",
        "remove ref",
    ],
)
def test_validator_rejects_alternate_retirement_dispositions(
    tmp_path: Path, nested: bool, disposition: str
) -> None:
    program, receipt = _state()
    directive = {"remote_ref_disposition": disposition}
    if nested:
        receipt["outcomes"][0]["branch_dispositions"] = [directive]
    else:
        receipt["outcomes"][0].update(directive)
    with pytest.raises(LibraryProgramError, match="destructive remote-ref disposition"):
        _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize(
    "unique", [0, 0.0, "0", " 0 ", "+0", "-0", "0.00", "0e9", "ZERO", "NONE", "NO_UNIQUE_VALUE"]
)
def test_all_zero_spellings_require_preserved_lineage_proof(
    tmp_path: Path, nested: bool, unique: object
) -> None:
    program, receipt = _state()
    directive = {"unique_value": unique}
    if nested:
        receipt["outcomes"][0]["branch_dispositions"] = [directive]
    else:
        receipt["outcomes"][0].update(directive)
    with pytest.raises(LibraryProgramError, match="unique_contribution_verification"):
        _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize(
    "unique",
    [None, False, True, [], {}, "", "  ", -1, "-1", float("nan"), float("inf"), "NaN", "Infinity"],
)
def test_validator_rejects_invalid_unique_value_types(tmp_path: Path, unique: object) -> None:
    program, receipt = _state()
    receipt["outcomes"][0]["unique_value"] = unique
    with pytest.raises(LibraryProgramError, match="unique_value"):
        _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("unique", [0, 0.0, "0", "0.0", "0e9", "NONE"])
def test_zero_values_with_structural_proof_remain_valid(
    tmp_path: Path, nested: bool, unique: object
) -> None:
    program, receipt = _state()
    directive = {
        "unique_value": unique,
        "remote_ref_disposition": "PRESERVE_DRAINED_LINEAGE",
        "unique_contribution_verification": {
            "verdict": "ZERO",
            "provider_readback_refs": ["synthetic-test://verified-branch-evidence"],
            "lineage_preserved": True,
        },
    }
    if nested:
        receipt["outcomes"][0]["branch_dispositions"] = [directive]
    else:
        receipt["outcomes"][0].update(directive)
    _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize(
    "proof",
    [
        {},
        {"verdict": "PRESENT"},
        {"verdict": "ZERO", "provider_readback_refs": []},
        {"verdict": "ZERO", "provider_readback_refs": ["source"], "lineage_preserved": False},
    ],
)
def test_partial_zero_proof_is_rejected(tmp_path: Path, proof: dict) -> None:
    program, receipt = _state()
    receipt["outcomes"][0].update({"unique_value": 0, "unique_contribution_verification": proof})
    with pytest.raises(LibraryProgramError):
        _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize(
    "unique",
    [
        "0e9223372036854775808",
        "0e-9223372036854775809",
        "-1e9223372036854775808",
        "0e9_223372036854775808",
    ],
)
def test_numeric_parse_failures_cannot_be_descriptive_fallback(
    tmp_path: Path, nested: bool, unique: str
) -> None:
    program, receipt = _state()
    directive = {"unique_value": unique}
    if nested:
        receipt["outcomes"][0]["branch_dispositions"] = [directive]
    else:
        receipt["outcomes"][0].update(directive)
    with pytest.raises(LibraryProgramError, match="unsupported numeric encoding"):
        _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize(
    "disposition",
    ["REMOVE\tREF", "REMOVE__REF", "REMOVE/REF", "delete.ref", "PURGE_REF", "DESTROY_REF"],
)
def test_command_separator_variants_cannot_evade_disposition_guard(
    tmp_path: Path, nested: bool, disposition: str
) -> None:
    program, receipt = _state()
    directive = {"remote_ref_disposition": disposition}
    if nested:
        receipt["outcomes"][0]["branch_dispositions"] = [directive]
    else:
        receipt["outcomes"][0].update(directive)
    with pytest.raises(LibraryProgramError, match="destructive remote-ref disposition"):
        _validate_modified(tmp_path, program, receipt)


@pytest.mark.parametrize(
    "disposition",
    ["PRESERVE_RETIRED_LINEAGE", "RETIREMENT_NOT_AUTHORIZED", "PRESERVE_DRAINED_LINEAGE"],
)
def test_preservation_only_labels_are_not_destructive_commands(
    tmp_path: Path, disposition: str
) -> None:
    program, receipt = _state()
    receipt["outcomes"][0]["remote_ref_disposition"] = disposition
    _validate_modified(tmp_path, program, receipt)
