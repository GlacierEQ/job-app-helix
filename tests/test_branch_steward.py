from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from job_app_helix import branch_steward


def completed(stdout: str = ""):
    class Result:
        returncode = 0
        stderr = ""
        def __init__(self, value: str):
            self.stdout = value
    return Result(stdout)


def test_diverged_unique_branch_is_never_safe_direct_merge(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with (
        patch.object(branch_steward, "_run") as run,
        patch.object(branch_steward, "_count_pair", return_value=(7, 2)),
        patch.object(branch_steward, "_unique_patch_commits", return_value=("abc", "def")),
        patch.object(branch_steward, "_changed_files", return_value=("src/core.py",)),
    ):
        run.return_value = completed("mergebase123\n")
        result = branch_steward.assess_branch(tmp_path, "origin/main", "origin/feature")

    assert result.classification == "DIVERGED_UNIQUE_VALUE"
    assert result.safe_direct_merge is False
    assert result.retirement_ready is False
    assert result.behind == 7
    assert result.ahead == 2
    assert "fresh canonical ancestry" in result.reason


def test_patch_equivalent_branch_is_retirement_ready(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with (
        patch.object(branch_steward, "_run") as run,
        patch.object(branch_steward, "_count_pair", return_value=(4, 3)),
        patch.object(branch_steward, "_unique_patch_commits", return_value=()),
        patch.object(branch_steward, "_changed_files", return_value=("README.md",)),
    ):
        run.return_value = completed("mergebase123\n")
        result = branch_steward.assess_branch(tmp_path, "origin/main", "origin/old")

    assert result.classification == "PATCH_EQUIVALENT_EXHAUSTED"
    assert result.safe_direct_merge is False
    assert result.retirement_ready is True


def test_current_unique_branch_can_advance_to_verification(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with (
        patch.object(branch_steward, "_run") as run,
        patch.object(branch_steward, "_count_pair", return_value=(0, 1)),
        patch.object(branch_steward, "_unique_patch_commits", return_value=("abc",)),
        patch.object(branch_steward, "_changed_files", return_value=("docs/new.md",)),
    ):
        run.return_value = completed("mergebase123\n")
        result = branch_steward.assess_branch(tmp_path, "origin/main", "origin/feature")

    assert result.classification == "CURRENT_UNIQUE_VALUE"
    assert result.safe_direct_merge is True
    assert result.retirement_ready is False
