from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "cleanup_obsolete_branches.py"
MANIFEST_PATH = ROOT / "manifests" / "obsolete_branches.json"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "cleanup_obsolete_branches",
        SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


class FakeAPI:
    def __init__(self) -> None:
        self.refs = {
            "merged": "1" * 40,
            "superseded": "2" * 40,
            "stale": "3" * 40,
            "candidate": "4" * 40,
        }
        self.deleted: list[str] = []
        self.restored: list[tuple[str, str]] = []
        self.stale_files = ["pyproject.toml", "uv.lock"]
        self.stale_open_pulls: list[dict[str, Any]] = []
        self.candidate_merged = False
        self.change_before_delete: str | None = None
        self.post_delete_error: Exception | None = None
        self.post_delete_error_branch: str | None = None
        self.get_ref_counts: dict[str, int] = {}

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
        return 200, {"object": {"sha": self.refs[branch]}}

    def delete_ref(self, branch: str) -> None:
        self.deleted.append(branch)
        self.refs.pop(branch, None)

    def create_ref(self, branch: str, sha: str) -> None:
        self.restored.append((branch, sha))
        self.refs[branch] = sha

    def get_pull(self, number: int) -> dict[str, Any]:
        pulls = {
            1: {
                "number": 1,
                "state": "closed",
                "merged_at": "2026-07-30T00:00:00Z",
                "head": {"ref": "merged", "sha": "1" * 40},
                "base": {"ref": "main"},
            },
            2: {
                "number": 2,
                "state": "closed",
                "merged_at": None,
                "head": {"ref": "superseded", "sha": "2" * 40},
                "base": {"ref": "main"},
            },
            3: {
                "number": 3,
                "state": "closed",
                "merged_at": "2026-07-30T01:00:00Z",
                "head": {"ref": "replacement", "sha": "5" * 40},
                "base": {"ref": "main"},
            },
            4: {
                "number": 4,
                "state": "closed" if self.candidate_merged else "open",
                "merged_at": (
                    "2026-07-30T02:00:00Z" if self.candidate_merged else None
                ),
                "head": {"ref": "candidate", "sha": "4" * 40},
                "base": {"ref": "main"},
            },
        }
        return pulls[number]

    def open_pulls_for_branch(self, branch: str) -> list[dict[str, Any]]:
        assert branch == "stale"
        return self.stale_open_pulls

    def compare(self, base: str, head: str) -> dict[str, Any]:
        assert base == "main"
        assert head == "3" * 40
        return {"files": [{"filename": name} for name in self.stale_files]}

    def read_text_file(self, path: str, ref: str) -> str:
        assert path == "pyproject.toml"
        assert ref == "3" * 40
        return '[project]\nname = "job-app-helix"\nversion = "0.2.0"\n'


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "glaciereq.obsolete-branches.v1",
                "repository": "GlacierEQ/job-app-helix",
                "default_branch": "main",
                "branches": [
                    {
                        "name": "merged",
                        "policy": "merged_pr",
                        "pull_request": 1,
                        "expected_head_sha": "1" * 40,
                        "reason": "merged",
                    },
                    {
                        "name": "superseded",
                        "policy": "superseded_pr",
                        "closed_pull_request": 2,
                        "expected_head_sha": "2" * 40,
                        "replacement_pull_request": 3,
                        "replacement_head_sha": "5" * 40,
                        "reason": "superseded",
                    },
                    {
                        "name": "stale",
                        "policy": "stale_dependency",
                        "expected_head_sha": "3" * 40,
                        "expected_version": "0.2.0",
                        "expected_files": ["pyproject.toml", "uv.lock"],
                        "reason": "stale",
                    },
                    {
                        "name": "candidate",
                        "policy": "merge_candidate",
                        "pull_request": 4,
                        "reason": "current PR",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_reference_manifest_has_unique_immutable_branch_records() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    branches = payload["branches"]
    names = [entry["name"] for entry in branches]

    assert payload["schema"] == "glaciereq.obsolete-branches.v1"
    assert payload["default_branch"] == "main"
    assert "main" not in names
    assert len(names) == len(set(names))
    for entry in branches:
        if entry["policy"] != "merge_candidate":
            assert len(entry["expected_head_sha"]) == 40


def test_dry_run_accepts_open_current_candidate_without_deleting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    results = module.cleanup(
        manifest,
        repository="GlacierEQ/job-app-helix",
        token="token",
        apply=False,
        output=receipt,
    )

    assert fake.deleted == []
    candidate = next(result for result in results if result.branch == "candidate")
    assert candidate.preflight == "PENDING_MERGE"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "VERIFIED"


def test_apply_deletes_all_only_after_every_entry_preflights(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.candidate_merged = True
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

    assert fake.deleted == ["merged", "superseded", "stale", "candidate"]
    assert {result.outcome for result in results} == {"DELETED"}


def test_any_preflight_failure_preserves_every_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.candidate_merged = True
    fake.stale_files = ["unexpected.py"]
    original_refs = dict(fake.refs)
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    with pytest.raises(module.CleanupError):
        module.cleanup(
            manifest,
            repository="GlacierEQ/job-app-helix",
            token="token",
            apply=True,
            output=receipt,
        )

    assert fake.deleted == []
    assert fake.refs == original_refs
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "FAILED_PREFLIGHT"


def test_changed_ref_blocks_only_that_candidate_and_continues(
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


def test_post_delete_verification_failure_restores_candidate_and_continues(
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


def test_open_dependency_pr_fails_closed_without_deletion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.candidate_merged = True
    fake.stale_open_pulls = [{"number": 99}]
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    with pytest.raises(module.CleanupError, match="open PRs"):
        module.cleanup(
            manifest,
            repository="GlacierEQ/job-app-helix",
            token="token",
            apply=True,
            output=receipt,
        )

    assert fake.deleted == []


def test_default_branch_is_rejected_even_if_manifest_requests_it() -> None:
    module = _load_module()
    with pytest.raises(module.CleanupError, match="Default branch"):
        module._preflight_entry(
            FakeAPI(),
            {
                "name": "main",
                "policy": "merged_pr",
                "pull_request": 1,
                "expected_head_sha": "1" * 40,
                "reason": "never allowed",
            },
            default_branch="main",
            ref_sha="1" * 40,
            apply=False,
        )
