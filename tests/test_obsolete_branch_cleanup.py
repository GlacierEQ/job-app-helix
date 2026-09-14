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
        self.stale_files = ["pyproject.toml", "uv.lock"]
        self.stale_open_pulls: list[dict[str, Any]] = []
        self.candidate_merged = False

    def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
        if branch not in self.refs:
            return 404, None
        return 200, {"object": {"sha": self.refs[branch]}}

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
                        "reason": "historically merged",
                    },
                    {
                        "name": "superseded",
                        "policy": "superseded_pr",
                        "closed_pull_request": 2,
                        "expected_head_sha": "2" * 40,
                        "replacement_pull_request": 3,
                        "replacement_head_sha": "5" * 40,
                        "reason": "historically superseded",
                    },
                    {
                        "name": "stale",
                        "policy": "stale_dependency",
                        "expected_head_sha": "3" * 40,
                        "expected_version": "0.2.0",
                        "expected_files": ["pyproject.toml", "uv.lock"],
                        "reason": "historically stale",
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


def test_script_exposes_no_ref_mutation_methods_or_apply_mode() -> None:
    module = _load_module()
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert not hasattr(module.GitHubAPI, "delete_ref")
    assert not hasattr(module.GitHubAPI, "create_ref")
    assert "--apply" not in source
    assert '"DELETE"' not in source
    assert '"POST"' not in source


def test_provider_adapter_rejects_non_get_methods() -> None:
    module = _load_module()
    api = module.GitHubAPI("GlacierEQ/job-app-helix", "token")

    with pytest.raises(module.CleanupError, match="read-only"):
        api.request("PATCH", "/repos/GlacierEQ/job-app-helix/git/refs/heads/example")


def test_audit_preserves_all_existing_refs_as_active_in_mesh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    results = module.audit(
        manifest,
        repository="GlacierEQ/job-app-helix",
        token="token",
        output=receipt,
    )

    assert fake.refs == {
        "merged": "1" * 40,
        "superseded": "2" * 40,
        "stale": "3" * 40,
        "candidate": "4" * 40,
    }
    assert {result.outcome for result in results} == {"ACTIVE_IN_MESH"}
    assert {result.preflight for result in results} == {
        "VERIFIED_OVERLAP",
        "PENDING_MERGE",
    }

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema"] == "glaciereq.branch-lineage-audit-receipt.v2"
    assert payload["mode"] == "READ_ONLY_LINEAGE_AUDIT"
    assert payload["conclusion"] == "VERIFIED_READ_ONLY"
    assert payload["anti_replacement"] == {
        "latest_is_routing_cursor_only": True,
        "overlap_is_not_zero_unique_contribution": True,
        "remote_ref_deletion_authority": False,
        "drained_terminal_state": "PRESERVE_DRAINED_LINEAGE",
    }


def test_merged_candidate_remains_active_in_mesh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.candidate_merged = True
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    _write_manifest(manifest)

    results = module.audit(
        manifest,
        repository="GlacierEQ/job-app-helix",
        token="token",
        output=None,
    )

    candidate = next(result for result in results if result.branch == "candidate")
    assert candidate.preflight == "VERIFIED_OVERLAP"
    assert candidate.outcome == "ACTIVE_IN_MESH"
    assert "UNIQUE_CONTRIBUTION=0" in candidate.detail


def test_missing_remote_ref_preserves_historical_lineage_pointer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.refs.pop("superseded")
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    _write_manifest(manifest)

    results = module.audit(
        manifest,
        repository="GlacierEQ/job-app-helix",
        token="token",
        output=None,
    )

    superseded = next(result for result in results if result.branch == "superseded")
    assert superseded.preflight == "REF_ABSENT"
    assert superseded.outcome == "PRESERVE_HISTORICAL_LINEAGE_POINTER"
    assert "does not prove" in superseded.detail


def test_failed_historical_preflight_never_promotes_retirement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    fake.stale_files = ["unexpected.py"]
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    results = module.audit(
        manifest,
        repository="GlacierEQ/job-app-helix",
        token="token",
        output=receipt,
    )

    stale = next(result for result in results if result.branch == "stale")
    assert stale.preflight == "FAILED"
    assert stale.outcome == "ACTIVE_IN_MESH"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "READ_ONLY_WITH_FINDINGS"


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
        )
