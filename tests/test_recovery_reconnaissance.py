from __future__ import annotations

import json
import subprocess
from pathlib import Path

from job_app_helix.recovery_reconnaissance import (
    HistoricalDonor,
    build_recovery_reconnaissance,
    discover_from_manifest,
    load_historical_donors,
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
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "APEX Recon Test")
    _git(repo, "config", "user.email", "recon@example.invalid")
    return repo


def test_manifest_loader_prefers_preservation_record_for_same_exact_head(tmp_path: Path) -> None:
    manifest = tmp_path / "refs.json"
    manifest.write_text(
        json.dumps(
            {
                "retired_refs": [
                    {
                        "name": "retired-name",
                        "expected_head_sha": "a" * 40,
                        "state": "REF_ABSENT_VERIFIED",
                    }
                ],
                "restored_refs_after_failed_transaction": [
                    {
                        "name": "restored-name",
                        "expected_head_sha": "a" * 40,
                        "state": "RESTORED_AFTER_FAILED_TRANSACTION",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    donors = load_historical_donors(manifest)

    assert len(donors) == 1
    assert donors[0].name == "restored-name"
    assert donors[0].source_bucket == "restored_refs_after_failed_transaction"


def test_stranded_unmerged_source_becomes_high_priority_and_feeds_intelligent_plan(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base = _commit(repo, "base")

    _git(repo, "switch", "-c", "stranded", base)
    source = repo / "src" / "lost_engine.py"
    source.parent.mkdir(parents=True)
    source.write_text("def recover_value():\n    return 42\n", encoding="utf-8")
    donor = _commit(repo, "unique recovery engine")

    _git(repo, "switch", "main")
    (repo / "README.md").write_text("later stronger main\n", encoding="utf-8")
    target = _commit(repo, "later main")

    report = build_recovery_reconnaissance(
        repo,
        donors=(
            HistoricalDonor(
                name="stranded",
                expected_head_sha=donor,
                source_bucket="retired_refs",
                state="REF_ABSENT_VERIFIED",
                pull_request=99,
            ),
        ),
        target_ref=target,
    )
    row = report.donors[0]

    assert row.availability == "AVAILABLE"
    assert row.reachable_from_target is False
    assert row.lineage_mode == "DIVERGED_BRANCH"
    assert row.lineage_base_sha == base
    assert row.deleted_source_test_count == 1
    assert row.disposition == "HIGH_PRIORITY_STRANDED"
    assert row.qualified_paths == ("src/lost_engine.py",)
    assert "src/lost_engine.py" in row.top_paths
    assert report.intelligent_plan_summary is not None
    assert report.intelligent_plan_summary["auto_recoverable_count"] == 1


def test_divergent_branch_excludes_inherited_snapshot_files_from_recovery(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    old = repo / "src" / "old_baseline.py"
    old.parent.mkdir(parents=True)
    old.write_text("def old_baseline():\n    return 'historical'\n", encoding="utf-8")
    base = _commit(repo, "shared base with old code")

    _git(repo, "switch", "-c", "feature", base)
    unique = repo / "src" / "unique_branch_engine.py"
    unique.write_text("def unique_engine():\n    return 'recover me'\n", encoding="utf-8")
    donor = _commit(repo, "add unique branch capability")

    _git(repo, "switch", "main")
    old.unlink()
    (repo / "README.md").write_text("modern main\n", encoding="utf-8")
    target = _commit(repo, "modern main removes unrelated old baseline")

    report = build_recovery_reconnaissance(
        repo,
        donors=(
            HistoricalDonor(
                name="feature",
                expected_head_sha=donor,
                source_bucket="retired_refs",
                state="REF_ABSENT_VERIFIED",
            ),
        ),
        target_ref=target,
    )
    row = report.donors[0]

    assert row.observed_candidate_count == 2
    assert row.candidate_count == 1
    assert row.excluded_baseline_count == 1
    assert row.qualified_paths == ("src/unique_branch_engine.py",)
    assert "src/old_baseline.py" not in row.qualified_paths
    assert report.intelligent_plan_summary is not None
    top = report.intelligent_plan_summary["top_candidates"]
    assert [candidate["path"] for candidate in top] == ["src/unique_branch_engine.py"]


def test_ancestor_with_no_current_delta_is_not_mistaken_for_lost_capability(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "src" / "retained.py"
    source.parent.mkdir(parents=True)
    source.write_text("def retained():\n    return 1\n", encoding="utf-8")
    donor = _commit(repo, "retained capability")
    (repo / "README.md").write_text("later docs\n", encoding="utf-8")
    target = _commit(repo, "later docs only")

    report = build_recovery_reconnaissance(
        repo,
        donors=(
            HistoricalDonor(
                name="already-integrated",
                expected_head_sha=donor,
                source_bucket="retired_refs",
                state="REF_ABSENT_VERIFIED",
            ),
        ),
        target_ref=target,
    )
    row = report.donors[0]

    assert row.reachable_from_target is True
    assert row.lineage_mode == "ANCESTOR_SNAPSHOT"
    assert row.candidate_count == 0
    assert row.disposition == "NO_CURRENT_DELTA"
    assert report.intelligent_plan_summary is None


def test_missing_donor_isolated_while_other_donor_still_advances(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "src" / "recoverable.py"
    source.parent.mkdir(parents=True)
    source.write_text("def value():\n    return 7\n", encoding="utf-8")
    donor = _commit(repo, "donor")
    source.unlink()
    target = _commit(repo, "target removes source")

    report = build_recovery_reconnaissance(
        repo,
        donors=(
            HistoricalDonor(
                name="missing",
                expected_head_sha="f" * 40,
                source_bucket="retired_refs",
                state="REF_ABSENT_VERIFIED",
            ),
            HistoricalDonor(
                name="available",
                expected_head_sha=donor,
                source_bucket="retired_refs",
                state="REF_ABSENT_VERIFIED",
            ),
        ),
        target_ref=target,
    )

    by_name = {row.name: row for row in report.donors}
    assert by_name["missing"].disposition == "UNAVAILABLE"
    assert by_name["missing"].lineage_mode == "UNAVAILABLE"
    assert by_name["missing"].blocker == "historical commit object is not present locally"
    assert by_name["available"].disposition == "HIGH_PRIORITY_STRANDED"
    assert report.intelligent_plan_summary is not None


def test_discover_from_manifest_is_deterministic_for_same_repository_state(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "src" / "lost.py"
    source.parent.mkdir(parents=True)
    source.write_text("def lost():\n    return 'x'\n", encoding="utf-8")
    donor = _commit(repo, "donor")
    source.unlink()
    target = _commit(repo, "target")
    manifest = repo / "refs.json"
    manifest.write_text(
        json.dumps(
            {
                "retired_refs": [
                    {
                        "name": "lost-branch",
                        "pull_request": 1,
                        "expected_head_sha": donor,
                        "state": "REF_ABSENT_VERIFIED",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    first = discover_from_manifest(repo, manifest, target_ref=target)
    second = discover_from_manifest(repo, manifest, target_ref=target)

    assert first.receipt_sha256 == second.receipt_sha256
    assert first.donors[0].expected_head_sha == donor
    assert first.intelligent_plan_summary == second.intelligent_plan_summary
