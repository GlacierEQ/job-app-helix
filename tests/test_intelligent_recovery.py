from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from job_app_helix.intelligent_recovery import (
    IntelligentRecoveryError,
    build_automatic_packets,
    build_intelligent_recovery_plan,
    execute_automatic_recovery,
    summarize_recovery_plan,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "APEX Test")
    _git(repo, "config", "user.email", "apex@example.invalid")
    return repo


def test_deleted_source_is_ranked_and_executed_without_losing_later_work(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "src" / "engine.py"
    source.parent.mkdir(parents=True)
    source.write_text("def recover():\n    return 'capability'\n", encoding="utf-8")
    donor = _commit(repo, "capability exists")

    source.unlink()
    (repo / "README.md").write_text("later stronger presentation\n", encoding="utf-8")
    target = _commit(repo, "later work accidentally drops capability")

    plan = build_intelligent_recovery_plan(repo, donor_refs=(donor,), target_ref=target)
    candidate = next(item for item in plan.candidates if item.path == "src/engine.py")

    assert candidate.role == "SOURCE"
    assert candidate.mode == "RESTORE_FILE"
    assert candidate.auto_recoverable is True
    assert candidate.preservation_risk <= 0.15
    assert candidate.candidate_id in plan.auto_batch_ids

    receipt = execute_automatic_recovery(repo, plan)
    assert source.read_text(encoding="utf-8") == "def recover():\n    return 'capability'\n"
    assert (repo / "README.md").read_text(encoding="utf-8") == "later stronger presentation\n"
    assert receipt.restored_paths == ("src/engine.py",)


def test_modified_python_routes_to_symbol_composition_and_cannot_auto_apply(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "src" / "engine.py"
    source.parent.mkdir(parents=True)
    source.write_text("def retained():\n    return 'old'\n", encoding="utf-8")
    donor = _commit(repo, "old engine")
    source.write_text(
        "def retained():\n    return 'new'\n\ndef stronger():\n    return 2\n",
        encoding="utf-8",
    )
    target = _commit(repo, "stronger later engine")

    plan = build_intelligent_recovery_plan(repo, donor_refs=(donor,), target_ref=target)
    candidate = next(item for item in plan.candidates if item.path == "src/engine.py")

    assert candidate.mode == "SYMBOL_COMPOSITION"
    assert candidate.auto_recoverable is False
    assert candidate.preservation_risk >= 0.5
    with pytest.raises(IntelligentRecoveryError, match="non-auto-recoverable"):
        build_automatic_packets(repo, plan, selected_ids=(candidate.candidate_id,))


def test_missing_local_dependency_routes_to_semantic_closure(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    package = repo / "src" / "pkg"
    package.mkdir(parents=True)
    (package / "feature.py").write_text(
        "from .helper import value\n\ndef run():\n    return value()\n",
        encoding="utf-8",
    )
    (package / "helper.py").write_text("def value():\n    return 7\n", encoding="utf-8")
    donor = _commit(repo, "feature with local dependency")

    (package / "feature.py").unlink()
    (package / "helper.py").unlink()
    target = _commit(repo, "both capability files removed")

    plan = build_intelligent_recovery_plan(repo, donor_refs=(donor,), target_ref=target)
    feature = next(item for item in plan.candidates if item.path == "src/pkg/feature.py")
    helper = next(item for item in plan.candidates if item.path == "src/pkg/helper.py")

    assert feature.mode == "SEMANTIC_CLOSURE"
    assert feature.auto_recoverable is False
    assert feature.dependency_probe.unresolved_local_imports == (".helper",)
    assert helper.mode == "RESTORE_FILE"
    assert helper.auto_recoverable is True


def test_deleted_workflow_is_preserved_as_review_not_automatic_mutation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    workflow = repo / ".github" / "workflows" / "release.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: release\n", encoding="utf-8")
    donor = _commit(repo, "workflow")
    workflow.unlink()
    target = _commit(repo, "remove workflow")

    plan = build_intelligent_recovery_plan(repo, donor_refs=(donor,), target_ref=target)
    candidate = next(item for item in plan.candidates if item.path.endswith("release.yml"))

    assert candidate.role == "WORKFLOW"
    assert candidate.mode == "RESTORE_FILE"
    assert candidate.auto_recoverable is False
    assert candidate.candidate_id in plan.review_ids


def test_cross_donor_plan_deduplicates_identical_capability_and_records_lineage(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "src" / "engine.py"
    source.parent.mkdir(parents=True)
    source.write_text("def capability():\n    return 1\n", encoding="utf-8")
    donor_a = _commit(repo, "first donor")
    (repo / "notes.txt").write_text("later donor metadata\n", encoding="utf-8")
    donor_b = _commit(repo, "second donor same capability bytes")
    source.unlink()
    target = _commit(repo, "capability removed")

    first = build_intelligent_recovery_plan(
        repo,
        donor_refs=(donor_a, donor_b),
        target_ref=target,
    )
    second = build_intelligent_recovery_plan(
        repo,
        donor_refs=(donor_a, donor_b),
        target_ref=target,
    )
    candidates = [item for item in first.candidates if item.path == "src/engine.py"]

    assert len(candidates) == 1
    assert set(candidates[0].donor_aliases) == {donor_a, donor_b}
    assert first.receipt_sha256 == second.receipt_sha256
    summary = summarize_recovery_plan(first)
    assert summary["donor_count"] == 2
    assert summary["auto_recoverable_count"] >= 1


def test_head_drift_blocks_automatic_execution(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "src" / "engine.py"
    source.parent.mkdir(parents=True)
    source.write_text("def capability():\n    return 1\n", encoding="utf-8")
    donor = _commit(repo, "donor")
    source.unlink()
    target = _commit(repo, "target")
    plan = build_intelligent_recovery_plan(repo, donor_refs=(donor,), target_ref=target)

    (repo / "later.txt").write_text("concurrent main advance\n", encoding="utf-8")
    advanced = _commit(repo, "advance")

    with pytest.raises(IntelligentRecoveryError, match="target HEAD drifted"):
        build_automatic_packets(repo, plan)
    assert advanced != target
    assert not source.exists()
