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
PROGRAM = ROOT / "manifests" / "library_priority_spine.json"
RECEIPT = ROOT / "status" / "priority-spine-wave-1-2026-07-30.json"
REPAIR_RECEIPT = (
    ROOT / "status" / "estate_evolution" / "2026-09-14-continuity-regression-repair.json"
)
POLICY = ROOT / "manifests" / "estate_evolution_policy.json"


def _write_program_with_receipt(
    tmp_path: Path,
    program_payload: dict[str, object],
    receipt_payload: dict[str, object],
) -> Path:
    manifests = tmp_path / "manifests"
    manifests.mkdir(parents=True)
    program_path = manifests / "library_priority_spine.json"
    program_path.write_text(json.dumps(program_payload), encoding="utf-8")
    receipt_path = tmp_path / str(program_payload["latest_execution_receipt"])
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt_payload), encoding="utf-8")
    return program_path


def test_checked_in_origin_receipt_is_mesh_safe() -> None:
    program = validate_library_program(PROGRAM)
    receipt = validate_latest_execution_receipt(PROGRAM, program)

    assert receipt["policy"]["holographic_mesh_anti_replacement"]
    assert receipt["policy"]["zero_unique_contribution_required_for_retirement"]
    assert receipt["policy"]["latest_is_routing_cursor_only"]
    assert not receipt["summary"]["remote_branch_refs_requiring_later_deletion"]
    assert receipt["summary"][
        "remote_branch_refs_pending_zero_unique_contribution_proof"
    ]


def test_continuity_repair_receipt_cannot_reintroduce_destructive_authority() -> None:
    repair = json.loads(REPAIR_RECEIPT.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))

    assert repair["repair"]["destructive_mutation_authority"] == "NONE"
    requirements = " ".join(repair["repair"]["retirement_requires"]).lower()
    assert "destructive mutation" not in requirements
    assert "preserved lineage" in requirements
    assert repair["deletion_performed"] is False
    assert policy["branch_policy"]["remote_ref_deletion_is_not_retirement"] is True
    assert (
        policy["branch_policy"]["remote_ref_deletion_forbidden_in_automated_retirement"]
        is True
    )
    assert policy["receipt"]["destructive_remote_ref_disposition_allowed"] is False


def test_receipt_rejects_declarative_delete_without_zero_unique_proof(
    tmp_path: Path,
) -> None:
    program_payload = json.loads(PROGRAM.read_text(encoding="utf-8"))
    receipt_payload = copy.deepcopy(
        json.loads(RECEIPT.read_text(encoding="utf-8"))
    )
    branch = receipt_payload["outcomes"][0]["branch_dispositions"][0]
    branch["unique_value"] = "NONE"
    branch["remote_ref_disposition"] = "DELETE_REF_REQUIRED"
    branch.pop("unique_contribution_verification", None)

    program_path = _write_program_with_receipt(
        tmp_path, program_payload, receipt_payload
    )
    program = validate_library_program(program_path)

    with pytest.raises(
        LibraryProgramError,
        match="destructive remote-ref disposition is forbidden",
    ):
        validate_latest_execution_receipt(program_path, program)


def test_receipt_rejects_delete_even_with_zero_proof_and_operator_authority(
    tmp_path: Path,
) -> None:
    program_payload = json.loads(PROGRAM.read_text(encoding="utf-8"))
    receipt_payload = copy.deepcopy(
        json.loads(RECEIPT.read_text(encoding="utf-8"))
    )
    branch = receipt_payload["outcomes"][0]["branch_dispositions"][0]
    branch["unique_value"] = "NONE"
    branch["remote_ref_disposition"] = "DELETE_REF_REQUIRED"
    branch["unique_contribution_verification"] = {
        "verdict": "ZERO",
        "provider_readback_refs": [
            "github://compare/main...feature/reference-language-manifest"
        ],
        "lineage_preserved": True,
    }

    program_path = _write_program_with_receipt(
        tmp_path, program_payload, receipt_payload
    )
    program = validate_library_program(program_path)

    with pytest.raises(
        LibraryProgramError,
        match="destructive remote-ref disposition is forbidden",
    ):
        validate_latest_execution_receipt(program_path, program)


def test_receipt_rejects_drained_retirement_without_lineage_proof(
    tmp_path: Path,
) -> None:
    program_payload = json.loads(PROGRAM.read_text(encoding="utf-8"))
    receipt_payload = copy.deepcopy(
        json.loads(RECEIPT.read_text(encoding="utf-8"))
    )
    branch = receipt_payload["outcomes"][0]["branch_dispositions"][0]
    branch["unique_value"] = "NONE"
    branch["remote_ref_disposition"] = "PRESERVE_DRAINED_LINEAGE"
    branch["unique_contribution_verification"] = {
        "verdict": "ZERO",
        "provider_readback_refs": [
            "github://compare/main...feature/reference-language-manifest"
        ],
    }

    program_path = _write_program_with_receipt(
        tmp_path, program_payload, receipt_payload
    )
    program = validate_library_program(program_path)

    with pytest.raises(
        LibraryProgramError,
        match="verified durable lineage preservation",
    ):
        validate_latest_execution_receipt(program_path, program)


def test_receipt_accepts_drained_retirement_with_zero_proof_and_preserved_ref(
    tmp_path: Path,
) -> None:
    program_payload = json.loads(PROGRAM.read_text(encoding="utf-8"))
    receipt_payload = copy.deepcopy(
        json.loads(RECEIPT.read_text(encoding="utf-8"))
    )
    branch = receipt_payload["outcomes"][0]["branch_dispositions"][0]
    branch["unique_value"] = "NONE"
    branch["remote_ref_disposition"] = "PRESERVE_DRAINED_LINEAGE"
    branch["unique_contribution_verification"] = {
        "verdict": "ZERO",
        "provider_readback_refs": [
            "github://compare/main...feature/reference-language-manifest"
        ],
        "lineage_preserved": True,
    }

    program_path = _write_program_with_receipt(
        tmp_path, program_payload, receipt_payload
    )
    program = validate_library_program(program_path)
    receipt = validate_latest_execution_receipt(program_path, program)

    retired = receipt["outcomes"][0]["branch_dispositions"][0]
    assert retired["unique_contribution_verification"]["verdict"] == "ZERO"
    assert retired["unique_contribution_verification"]["lineage_preserved"]
    assert retired["remote_ref_disposition"] == "PRESERVE_DRAINED_LINEAGE"
