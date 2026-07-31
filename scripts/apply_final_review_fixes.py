from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected source block missing in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_builder() -> None:
    builder = Path("scripts/build_recruiter_site.py")
    replace_exact(
        builder,
        dedent(
            r'''\
            PHONE_PATTERN = re.compile(
                r"(?<!\d)(?:\+?1[\s().-]*)?(?:\(\d{3}\)|\d{3})"
                r"[\s.-]*\d{3}[\s.-]*\d{4}(?!\d)"
            )
            '''
        ),
        dedent(
            r'''\
            PHONE_PATTERN = re.compile(
                r"(?<![0-9A-Fa-f])(?:\+?1[\s().-]*)?(?:\(\d{3}\)|\d{3})"
                r"[\s.-]*\d{3}[\s.-]*\d{4}(?![0-9A-Fa-f])"
            )
            '''
        ),
    )


def patch_cleanup() -> None:
    cleanup = Path("scripts/cleanup_obsolete_branches.py")
    replace_exact(
        cleanup,
        dedent(
            '''\
                deleted: list[DeletionCandidate] = []
                final_results: list[BranchResult] = [
                    result for result in preflight_results if result.preflight == "ALREADY_ABSENT"
                ]
            '''
        ),
        dedent(
            '''\
                deleted: list[DeletionCandidate] = []
                attempted: list[DeletionCandidate] = []
                final_results: list[BranchResult] = [
                    result for result in preflight_results if result.preflight == "ALREADY_ABSENT"
                ]
            '''
        ),
    )
    replace_exact(
        cleanup,
        dedent(
            '''\
                        api.delete_ref(candidate.branch)
                        after_status, _ = api.get_ref(candidate.branch)
            '''
        ),
        dedent(
            '''\
                        api.delete_ref(candidate.branch)
                        attempted.append(candidate)
                        after_status, _ = api.get_ref(candidate.branch)
            '''
        ),
    )
    replace_exact(
        cleanup,
        "    for candidate in reversed(deleted):",
        "    for candidate in reversed(attempted):",
    )
    replace_exact(
        cleanup,
        dedent(
            '''\
                results_after_rollback: list[BranchResult] = []
                for result in preflight_results:
                    if result.branch in rolled_back:
                        results_after_rollback.append(
                            BranchResult(
                                branch=result.branch,
                                policy=result.policy,
                                reason=result.reason,
                                ref_sha=result.ref_sha,
                                preflight=result.preflight,
                                outcome="ROLLED_BACK",
                                detail="Deletion was reversed after a later failure",
                            )
                        )
                    else:
                        results_after_rollback.append(result)
            '''
        ),
        dedent(
            '''\
                attempted_names = {candidate.branch for candidate in attempted}
                results_after_rollback: list[BranchResult] = []
                for result in preflight_results:
                    if result.branch in rolled_back:
                        outcome = "ROLLED_BACK"
                        detail = "Deletion was reversed after a later failure"
                    elif result.branch in attempted_names:
                        outcome = "ROLLBACK_FAILED"
                        detail = "Deletion was attempted and restoration was not verified"
                    elif result.preflight == "ALREADY_ABSENT":
                        outcome = "NO_ACTION"
                        detail = result.detail
                    else:
                        outcome = "PRESERVED"
                        detail = "Branch was not deleted because the transaction failed"
                    results_after_rollback.append(
                        BranchResult(
                            branch=result.branch,
                            policy=result.policy,
                            reason=result.reason,
                            ref_sha=result.ref_sha,
                            preflight=result.preflight,
                            outcome=outcome,
                            detail=detail,
                        )
                    )
            '''
        ),
    )


def patch_site_tests() -> None:
    path = Path("tests/test_recruiter_site_deployment.py")
    text = path.read_text(encoding="utf-8")
    if "test_phone_pattern_ignores_digit_runs_inside_hex_sha" in text:
        return
    marker = "\ndef test_deployment_manifest_hashes_every_payload"
    addition = dedent(
        '''

        @pytest.mark.parametrize(
            "sha_like",
            [
                "ab1234567890cdefabcdefabcdefabcdefabcdef",
                "abcdef1234567890abcdefabcdefabcdefabcdef",
            ],
        )
        def test_phone_pattern_ignores_digit_runs_inside_hex_sha(sha_like: str) -> None:
            builder = _load_builder()
            assert len(sha_like) == 40
            assert builder.PHONE_PATTERN.search(sha_like) is None


        def test_site_build_accepts_hex_sha_with_embedded_digit_run(tmp_path: Path) -> None:
            builder = _load_builder()
            output = tmp_path / "site"
            source_commit = "ab1234567890cdefabcdefabcdefabcdefabcdef"

            builder.build(output, source_commit)

            index = (output / "index.html").read_text(encoding="utf-8")
            assert source_commit in index
        '''
    )
    if marker not in text:
        raise SystemExit("Site-test insertion marker missing")
    path.write_text(text.replace(marker, addition + marker, 1), encoding="utf-8")


def patch_cleanup_tests() -> None:
    path = Path("tests/test_obsolete_branch_cleanup.py")
    replace_exact(
        path,
        dedent(
            '''\
                    self.change_before_delete: str | None = None
                    self.get_ref_counts: dict[str, int] = {}
            '''
        ),
        dedent(
            '''\
                    self.change_before_delete: str | None = None
                    self.post_delete_error: Exception | None = None
                    self.post_delete_error_branch: str | None = None
                    self.get_ref_counts: dict[str, int] = {}
            '''
        ),
    )
    replace_exact(
        path,
        dedent(
            '''\
                def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
                    self.get_ref_counts[branch] = self.get_ref_counts.get(branch, 0) + 1
                    if branch == self.change_before_delete and self.get_ref_counts[branch] >= 3:
                        self.refs[branch] = "9" * 40
                    if branch not in self.refs:
                        return 404, None
            '''
        ),
        dedent(
            '''\
                def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
                    self.get_ref_counts[branch] = self.get_ref_counts.get(branch, 0) + 1
                    if branch == self.change_before_delete and self.get_ref_counts[branch] >= 3:
                        self.refs[branch] = "9" * 40
                    if (
                        branch == self.post_delete_error_branch
                        and branch in self.deleted
                        and self.post_delete_error is not None
                    ):
                        error = self.post_delete_error
                        self.post_delete_error = None
                        raise error
                    if branch not in self.refs:
                        return 404, None
            '''
        ),
    )
    text = path.read_text(encoding="utf-8")
    if "test_post_delete_verification_failure_restores_attempted_branch" in text:
        return
    marker = "\ndef test_open_dependency_pr_fails_closed_without_deletion"
    addition = dedent(
        '''

        def test_post_delete_verification_failure_restores_attempted_branch_and_preserves_rest(
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
            original_refs = dict(fake.refs)
            monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
            manifest = tmp_path / "branches.json"
            receipt = tmp_path / "receipt.json"
            _write_manifest(manifest)

            with pytest.raises(module.CleanupError, match="post-delete verification"):
                module.cleanup(
                    manifest,
                    repository="GlacierEQ/job-app-helix",
                    token="token",
                    apply=True,
                    output=receipt,
                )

            assert fake.refs == original_refs
            assert fake.deleted == ["merged"]
            assert fake.restored == [("merged", original_refs["merged"])]
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            assert payload["conclusion"] == "FAILED_ROLLED_BACK"
            outcomes = {
                result["branch"]: result["outcome"] for result in payload["results"]
            }
            assert outcomes["merged"] == "ROLLED_BACK"
            assert outcomes["superseded"] == "PRESERVED"
            assert outcomes["stale"] == "PRESERVED"
            assert outcomes["candidate"] == "PRESERVED"
            assert "READY" not in outcomes.values()
        '''
    )
    if marker not in text:
        raise SystemExit("Cleanup-test insertion marker missing")
    path.write_text(text.replace(marker, addition + marker, 1), encoding="utf-8")


def main() -> int:
    patch_builder()
    patch_cleanup()
    patch_site_tests()
    patch_cleanup_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
