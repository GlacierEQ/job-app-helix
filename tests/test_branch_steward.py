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
    assert result.operator_review_required is True
    assert result.capability_review_required is True
    assert result.behind == 7
    assert result.ahead == 2
    assert "later gains" in result.reason


def test_patch_equivalence_never_becomes_retirement_authority(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with (
        patch.object(branch_steward, "_run") as run,
        patch.object(branch_steward, "_count_pair", return_value=(4, 3)),
        patch.object(branch_steward, "_unique_patch_commits", return_value=()),
        patch.object(branch_steward, "_changed_files", return_value=("README.md",)),
    ):
        run.return_value = completed("mergebase123\n")
        result = branch_steward.assess_branch(tmp_path, "origin/main", "origin/old")

    assert result.classification == "PATCH_EQUIVALENT_CAPABILITY_REVIEW_REQUIRED"
    assert result.safe_direct_merge is False
    assert result.retirement_ready is False
    assert result.operator_review_required is True
    assert result.capability_review_required is True
    assert "not proof" in result.reason


def test_ancestry_equivalence_never_becomes_retirement_authority(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with (
        patch.object(branch_steward, "_run") as run,
        patch.object(branch_steward, "_count_pair", return_value=(3, 0)),
        patch.object(branch_steward, "_unique_patch_commits", return_value=()),
        patch.object(branch_steward, "_changed_files", return_value=()),
    ):
        run.return_value = completed("mergebase123\n")
        result = branch_steward.assess_branch(tmp_path, "origin/main", "origin/old")

    assert result.classification == "ANCESTRY_EQUIVALENT_CAPABILITY_REVIEW_REQUIRED"
    assert result.retirement_ready is False
    assert result.operator_review_required is True
    assert result.capability_review_required is True
    assert "cannot establish capability exhaustion" in result.reason


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
    assert result.operator_review_required is True
    assert result.capability_review_required is True


def test_repository_assessment_has_zero_automatic_retirement_ready(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with (
        patch.object(branch_steward, "list_remote_branches", return_value=("old",)),
        patch.object(branch_steward, "assess_branch") as assess,
    ):
        assess.return_value = branch_steward.BranchAssessment(
            repository=tmp_path.name,
            reference_branch="origin/main",
            branch="origin/old",
            merge_base="abc",
            ahead=0,
            behind=1,
            unique_patch_commits=(),
            changed_files=(),
            classification="ANCESTRY_EQUIVALENT_CAPABILITY_REVIEW_REQUIRED",
            safe_direct_merge=False,
            retirement_ready=False,
            operator_review_required=True,
            capability_review_required=True,
            reason="review capability",
        )
        result = branch_steward.assess_repository(tmp_path)

    assert result["retirement_ready"] == 0
    assert result["capability_review_required"] == 1
    assert result["retirement_policy"] == "OPERATOR_AUTHORIZATION_REQUIRED_AFTER_CAPABILITY_REVIEW"
