from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from job_app_helix.library_program import (
    EXPECTED_REPOSITORIES,
    LibraryProgramError,
    render_library_program,
    validate_latest_execution_receipt,
    validate_library_program,
)

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "manifests" / "library_priority_spine.json"
RECEIPT = ROOT / "status" / "priority-spine-wave-1-2026-07-30.json"


def _write_program(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "library.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_program_with_receipt(
    tmp_path: Path,
    program_payload: dict[str, object],
    receipt_payload: dict[str, object],
) -> Path:
    manifests = tmp_path / "manifests"
    status = tmp_path / "status"
    manifests.mkdir()
    status.mkdir()
    program_path = manifests / "library_priority_spine.json"
    program_path.write_text(json.dumps(program_payload), encoding="utf-8")
    receipt_reference = str(program_payload["latest_execution_receipt"])
    receipt_path = tmp_path / receipt_reference
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt_payload), encoding="utf-8")
    return program_path


def _payload() -> dict[str, object]:
    return json.loads(PROGRAM.read_text(encoding="utf-8"))


def _receipt_payload() -> dict[str, object]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_checked_in_library_program_is_valid() -> None:
    payload = validate_library_program(PROGRAM)

    assert tuple(item["repository"] for item in payload["repositories"]) == (
        EXPECTED_REPOSITORIES
    )
    assert payload["canonical_control_plane"] == "GlacierEQ/job-app-helix"


def test_checked_in_latest_execution_receipt_is_valid() -> None:
    program = validate_library_program(PROGRAM)
    receipt = validate_latest_execution_receipt(PROGRAM, program)

    assert tuple(item["repository"] for item in receipt["outcomes"]) == (
        EXPECTED_REPOSITORIES
    )
    assert receipt["summary"]["whole_library_complete"] is False
    assert receipt["summary"]["remote_branch_refs_deleted"] == 0


def test_priorities_are_exact_and_contiguous() -> None:
    payload = _payload()
    repositories = payload["repositories"]

    assert [item["priority"] for item in repositories] == list(range(len(repositories)))


def test_program_rejects_reordered_authority(tmp_path: Path) -> None:
    payload = _payload()
    repositories = payload["repositories"]
    repositories[0], repositories[1] = repositories[1], repositories[0]

    with pytest.raises(LibraryProgramError, match="exact and ordered"):
        validate_library_program(_write_program(tmp_path, payload))


def test_program_rejects_duplicate_aliases(tmp_path: Path) -> None:
    payload = _payload()
    repositories = payload["repositories"]
    repositories[1]["aliases"].append(repositories[0]["aliases"][0])

    with pytest.raises(LibraryProgramError, match="is shared"):
        validate_library_program(_write_program(tmp_path, payload))


def test_program_preserves_megamind_identity_boundary(tmp_path: Path) -> None:
    payload = _payload()
    payload["repositories"][-1]["identity_state"] = "CONFIRMED"

    with pytest.raises(LibraryProgramError, match="must remain explicitly unresolved"):
        validate_library_program(_write_program(tmp_path, payload))


def test_program_rejects_branch_closure_without_preservation(tmp_path: Path) -> None:
    payload = _payload()
    payload["policy"]["preserve_unique_value_before_closure"] = False

    with pytest.raises(LibraryProgramError, match="preserved before closure"):
        validate_library_program(_write_program(tmp_path, payload))


def test_receipt_rejects_remote_branch_deletion_overclaim(tmp_path: Path) -> None:
    program_payload = _payload()
    receipt_payload = _receipt_payload()
    receipt_payload["summary"]["remote_branch_refs_deleted"] = 1
    program_path = _write_program_with_receipt(
        tmp_path, program_payload, receipt_payload
    )
    program = validate_library_program(program_path)

    with pytest.raises(LibraryProgramError, match="overstates remote branch deletion"):
        validate_latest_execution_receipt(program_path, program)


def test_receipt_rejects_whole_library_completion_overclaim(tmp_path: Path) -> None:
    program_payload = _payload()
    receipt_payload = _receipt_payload()
    receipt_payload["summary"]["whole_library_complete"] = True
    program_path = _write_program_with_receipt(
        tmp_path, program_payload, receipt_payload
    )
    program = validate_library_program(program_path)

    with pytest.raises(LibraryProgramError, match="whole-library completion"):
        validate_latest_execution_receipt(program_path, program)


def test_render_is_deterministic_and_truth_bounded() -> None:
    payload = validate_library_program(PROGRAM)

    first = render_library_program(payload)
    second = render_library_program(copy.deepcopy(payload))

    assert first == second
    assert "Closing a pull request does not prove" in first
    assert "GlacierEQ/pro-code" in first
    assert "PENDING_USER_INTENT_CONFIRMATION" not in first
