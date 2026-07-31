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
        self.fail_delete_for: str | None = None
        self.stale_files = ["pyproject.toml", "uv.lock"]
        self.stale_open_pulls: list[dict[str, Any]] = []
        self.candidate_merged = False

    def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
        if branch not in self.refs:
            return 404, None
        return 200, {"object": {"sha": self.refs[branch]}}

    def delete_ref(self, branch: str) -> None:
        if branch == self.fail_delete_for:
            raise RuntimeError(f"delete failed for {branch}")
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
                "head": {"ref": "merged"},
                "base": {"ref": "main"},
            },
            2: {
                "number": 2,
                "state": "closed",
                "merged_at": None,
                "head": {"ref": "superseded"},
                "base": {"ref": "main"},
            },
            3: {
                "number": 3,
                "state": "closed",
                "merged_at": "2026-07-30T01:00:00Z",
                "head": {"ref": "replacement"},
                "base": {"ref": "main"},
            },
            4: {
                "number": 4,
                "state": "closed" if self.candidate_merged else "open",
                "merged_at": (
                    "2026-07-30T02:00:00Z" if self.candidate_merged else None
                ),
                "head": {"ref": "candidate"},
                "base": {"ref": "main"},
            },
        }
        return pulls[number]

    def open_pulls_for_branch(self, branch: str) -> list[dict[str, Any]]:
        assert branch == "stale"
        return self.stale_open_pulls

    def compare(self, base: str, head: str) -> dict[str, Any]:
        assert base == "main"
        assert head == "stale"
        return {"files": [{"filename": name} for name in self.stale_files]}

    def read_text_file(self, path: str, ref: str) -> str:
        assert path == "pyproject.toml"
        assert ref == "stale"
        return '[project]\nversion = "0.2.0"\n'


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
                        "reason": "merged",
                    },
                    {
                        "name": "superseded",
                        "policy": "superseded_pr",
                        "closed_pull_request": 2,
                        "replacement_pull_request": 3,
                        "reason": "superseded",
                    },
                    {
                        "name": "stale",
                        "policy": "stale_dependency",
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


def test_canonical_manifest_never_targets_main_and_has_unique_branches() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    branches = payload["branches"]
    names = [entry["name"] for entry in branches]

    assert payload["schema"] == "glaciereq.obsolete-branches.v1"
    assert payload["default_branch"] == "main"
    assert "main" not in names
    assert len(names) == len(set(names))
    assert "dependabot/uv/uv-590e9db7b9" in names
    assert "deploy/canonical-recruiter-surface-2026-07-30" in names


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
    assert {result.outcome for result in results} == {"DRY_RUN"}
    candidate = next(result for result in results if result.branch == "candidate")
    assert candidate.preflight == "PENDING_MERGE"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "VERIFIED"
    assert payload["mode"] == "DRY_RUN"


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
    assert all(result.preflight == "VERIFIED" for result in results)


def test_any_preflight_failure_preserves_every_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.candidate_merged = True
    fake.stale_files = ["unexpected.py"]
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
    assert set(fake.refs) == {"merged", "superseded", "stale", "candidate"}
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "FAILED_PREFLIGHT"
    stale = next(result for result in payload["results"] if result["branch"] == "stale")
    assert stale["outcome"] == "PRESERVED"


def test_delete_failure_rolls_back_prior_deletions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.candidate_merged = True
    original_refs = dict(fake.refs)

    def failing_delete(branch: str) -> None:
        if branch == "stale":
            raise module.CleanupError("injected deletion failure")
        fake.deleted.append(branch)
        fake.refs.pop(branch, None)

    fake.delete_ref = failing_delete
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

    assert fake.refs == original_refs
    assert fake.restored == [
        ("superseded", original_refs["superseded"]),
        ("merged", original_refs["merged"]),
    ]
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "FAILED_ROLLED_BACK"
    outcomes = {result["branch"]: result["outcome"] for result in payload["results"]}
    assert outcomes["merged"] == "ROLLED_BACK"
    assert outcomes["superseded"] == "ROLLED_BACK"


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
                "reason": "never allowed",
            },
            default_branch="main",
            apply=False,
        )
