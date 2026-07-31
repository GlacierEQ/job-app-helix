from __future__ import annotations

from pathlib import Path


CLEANUP = Path("scripts/cleanup_obsolete_branches.py")
TESTS = Path("tests/test_obsolete_branch_cleanup.py")


def replace_between(path: Path, start: str, end: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    path.write_text(
        text[:start_index] + replacement + text[end_index:],
        encoding="utf-8",
    )


def patch_cleanup() -> None:
    replacement = '''    final_results: list[BranchResult] = [
        result for result in preflight_results if result.preflight == "ALREADY_ABSENT"
    ]
    deletion_failures: list[str] = []
    rollback_failures: list[str] = []

    for candidate in candidates:
        attempted = False
        try:
            current_sha = _ref_sha(api, candidate.branch)
            if current_sha != candidate.ref_sha:
                raise CleanupError(
                    f"Branch changed after preflight: {candidate.ref_sha} -> {current_sha}"
                )
            api.delete_ref(candidate.branch)
            attempted = True
            after_status, _ = api.get_ref(candidate.branch)
            if after_status != 404:
                raise CleanupError(
                    f"Branch {candidate.branch} still exists after delete"
                )
            final_results.append(
                BranchResult(
                    branch=candidate.branch,
                    policy=candidate.policy,
                    reason=candidate.reason,
                    ref_sha=candidate.ref_sha,
                    preflight=candidate.preflight,
                    outcome="DELETED",
                    detail=candidate.detail,
                )
            )
        except CleanupError as exc:
            deletion_failures.append(f"{candidate.branch}: {exc}")
            outcome = "DELETE_BLOCKED_PRESERVED"
            detail = f"Deletion was blocked before mutation: {exc}"

            if attempted:
                try:
                    status, _ = api.get_ref(candidate.branch)
                    if status == 404:
                        api.create_ref(candidate.branch, candidate.ref_sha)
                    restored_sha = _ref_sha(api, candidate.branch)
                    if restored_sha != candidate.ref_sha:
                        raise CleanupError(
                            f"Branch {candidate.branch} did not restore to "
                            f"{candidate.ref_sha}"
                        )
                    outcome = "DELETE_BLOCKED_ROLLED_BACK"
                    detail = f"Deletion attempt was restored after failure: {exc}"
                except CleanupError as rollback_exc:
                    rollback_failures.append(
                        f"{candidate.branch}: rollback failed: {rollback_exc}"
                    )
                    outcome = "DELETE_BLOCKED_ROLLBACK_FAILED"
                    detail = (
                        f"Deletion failed and restoration was not verified: "
                        f"{exc}; {rollback_exc}"
                    )

            final_results.append(
                BranchResult(
                    branch=candidate.branch,
                    policy=candidate.policy,
                    reason=candidate.reason,
                    ref_sha=candidate.ref_sha,
                    preflight=candidate.preflight,
                    outcome=outcome,
                    detail=detail,
                )
            )

    if rollback_failures:
        conclusion = "FAILED_ROLLBACK"
    elif deletion_failures:
        conclusion = "VERIFIED_WITH_BLOCKED_REFS"
    else:
        conclusion = "VERIFIED"

    all_failures = [*deletion_failures, *rollback_failures]
    payload = _receipt(
        repository=repository,
        default_branch=default_branch,
        apply=True,
        conclusion=conclusion,
        results=final_results,
        failures=all_failures,
    )
    _write_receipt(output, payload)

    if rollback_failures:
        raise CleanupError("; ".join(all_failures))
    return final_results
'''
    replace_between(
        CLEANUP,
        "    deleted: list[DeletionCandidate] = []\n",
        "\n\ndef parse_args() -> argparse.Namespace:\n",
        replacement,
    )


def patch_changed_ref_test() -> None:
    replacement = '''def test_changed_ref_blocks_only_that_candidate_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.candidate_merged = True
    fake.change_before_delete = "stale"
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    results = module.cleanup(
        manifest,
        repository="GlacierEQ/job-app-helix",
        token="token",
        apply=True,
        output=receipt,
    )

    assert fake.deleted == ["merged", "superseded", "candidate"]
    assert fake.refs == {"stale": "9" * 40}
    outcomes = {result.branch: result.outcome for result in results}
    assert outcomes == {
        "merged": "DELETED",
        "superseded": "DELETED",
        "stale": "DELETE_BLOCKED_PRESERVED",
        "candidate": "DELETED",
    }
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "VERIFIED_WITH_BLOCKED_REFS"


'''
    replace_between(
        TESTS,
        "def test_changed_ref_before_delete_rolls_back_prior_deletions(\n",
        "def test_post_delete_verification_failure_restores_attempted_branch_and_preserves_rest(\n",
        replacement,
    )


def patch_post_delete_test() -> None:
    replacement = '''def test_post_delete_verification_failure_restores_candidate_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.candidate_merged = True
    fake.post_delete_error_branch = "merged"
    fake.post_delete_error = module.CleanupError(
        "transient post-delete verification failure"
    )
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    results = module.cleanup(
        manifest,
        repository="GlacierEQ/job-app-helix",
        token="token",
        apply=True,
        output=receipt,
    )

    assert fake.refs == {"merged": "1" * 40}
    assert fake.deleted == ["merged", "superseded", "stale", "candidate"]
    assert fake.restored == [("merged", "1" * 40)]
    outcomes = {result.branch: result.outcome for result in results}
    assert outcomes == {
        "merged": "DELETE_BLOCKED_ROLLED_BACK",
        "superseded": "DELETED",
        "stale": "DELETED",
        "candidate": "DELETED",
    }
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "VERIFIED_WITH_BLOCKED_REFS"


'''
    replace_between(
        TESTS,
        "def test_post_delete_verification_failure_restores_attempted_branch_and_preserves_rest(\n",
        "def test_open_dependency_pr_fails_closed_without_deletion(\n",
        replacement,
    )


def main() -> int:
    patch_cleanup()
    patch_changed_ref_test()
    patch_post_delete_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
