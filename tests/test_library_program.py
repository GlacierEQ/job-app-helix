from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from job_app_helix.library_program import (
    EXPECTED_REPOSITORIES,
    LibraryProgramError,
    render_library_program,
    validate_library_program,
)

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "manifests" / "library_priority_spine.json"


def _write_program(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "library.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _payload() -> dict[str, object]:
    return json.loads(PROGRAM.read_text(encoding="utf-8"))


def test_checked_in_library_program_is_valid() -> None:
    payload = validate_library_program(PROGRAM)

    assert tuple(item["repository"] for item in payload["repositories"]) == (
        EXPECTED_REPOSITORIES
    )
    assert payload["canonical_control_plane"] == "GlacierEQ/job-app-helix"


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


def test_render_is_deterministic_and_truth_bounded() -> None:
    payload = validate_library_program(PROGRAM)

    first = render_library_program(payload)
    second = render_library_program(copy.deepcopy(payload))

    assert first == second
    assert "Closing a pull request does not prove" in first
    assert "GlacierEQ/pro-code" in first
    assert "PENDING_USER_INTENT_CONFIRMATION" not in first
