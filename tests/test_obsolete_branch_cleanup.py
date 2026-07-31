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
    spec = importlib.util.spec_from_file_location("cleanup_obsolete_branches", SCRIPT_PATH)
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
        }
        self.deleted: list[str] = []

    def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
        if branch not in self.refs:
            return 404, None
        return 200, {"object": {"sha": self.refs[branch]}}

    def delete_ref(self, branch: str) -> None:
        self.deleted.append(branch)
        self.refs.pop(branch, None)

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
        }
        return pulls[number]

    def open_pulls_for_branch(self, branch: str) -> list[dict[str, Any]]:
        return []

    def compare(self, base: str, head: str) -> dict[str, Any]:
        assert base == "main"
        assert head == "stale"
        return {"files": [{"filename": "pyproject.toml"}, {"filename": "uv.lock"}]}

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


def test_dry_run_verifies_without_deleting(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "VERIFIED"
    assert payload["mode"] == "DRY_RUN"


def test_apply_deletes_only_after_every_entry_preflights(
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
        apply=True,
        output=receipt,
    )

    assert fake.deleted == ["merged", "superseded", "stale"]
    assert {result.outcome for result in results} == {"DELETED"}
    assert all(result.preflight == "VERIFIED" for result in results)


def test_stale_dependency_policy_fails_if_patch_scope_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.compare = lambda base, head: {"files": [{"filename": "unexpected.py"}]}
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

    assert "stale" not in fake.deleted
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "FAILED"
    stale = next(result for result in payload["results"] if result["branch"] == "stale")
    assert stale["outcome"] == "PRESERVED"


def test_default_branch_is_rejected_even_if_manifest_requests_it(tmp_path: Path) -> None:
    module = _load_module()
    manifest = tmp_path / "branches.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "glaciereq.obsolete-branches.v1",
                "repository": "GlacierEQ/job-app-helix",
                "default_branch": "main",
                "branches": [
                    {
                        "name": "main",
                        "policy": "merged_pr",
                        "pull_request": 1,
                        "reason": "never allowed",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(module.CleanupError, match="Default branch"):
        module._preflight_entry(
            FakeAPI(),
            json.loads(manifest.read_text(encoding="utf-8"))["branches"][0],
            default_branch="main",
        )
