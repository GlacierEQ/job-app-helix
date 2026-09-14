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
            "candidate": "4" * 40,
        }
        self.mutations: list[tuple[str, str]] = []

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
                "state": "open",
                "merged_at": None,
                "head": {"ref": "candidate", "sha": "4" * 40},
                "base": {"ref": "main"},
            },
        }
        return pulls[number]

    def open_pulls_for_branch(self, branch: str) -> list[dict[str, Any]]:
        assert branch == "stale"
        return []

    def compare(self, base: str, head: str) -> dict[str, Any]:
        assert base == "main"
        assert head == "3" * 40
        return {"files": [{"filename": "pyproject.toml"}, {"filename": "uv.lock"}]}

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
                        "reason": "historical candidate",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_reference_manifest_remains_historical_input_only() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    names = [entry["name"] for entry in payload["branches"]]
    assert payload["schema"] == "glaciereq.obsolete-branches.v1"
    assert payload["default_branch"] == "main"
    assert "main" not in names
    assert len(names) == len(set(names))


def test_read_only_audit_preserves_all_existing_donors(
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

    assert fake.mutations == []
    assert {result.outcome for result in results} == {"PRESERVE_ACTIVE_IN_MESH"}
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["mode"] == "READ_ONLY_LINEAGE_AUDIT"
    assert payload["remote_ref_deletion_authorized"] is False
    assert payload["unique_contribution_zero_proven"] is False
    assert payload["conclusion"] == "VERIFIED_READ_ONLY"


def test_compatibility_cleanup_rejects_apply_before_any_provider_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    with pytest.raises(module.CleanupError, match="--apply is retired"):
        module.cleanup(
            manifest,
            repository="GlacierEQ/job-app-helix",
            token="token",
            apply=True,
            output=receipt,
        )

    assert fake.mutations == []
    assert not receipt.exists()


def test_api_rejects_non_get_methods_without_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    api = module.GitHubAPI("GlacierEQ/job-app-helix", "token")
    called = False

    def _urlopen(*args: object, **kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("network mutation must never be reached")

    monkeypatch.setattr(module.urllib.request, "urlopen", _urlopen)
    with pytest.raises(module.CleanupError, match="permanently read-only"):
        api.request("DELETE", "/repos/GlacierEQ/job-app-helix/git/refs/heads/donor")
    assert called is False


def test_cli_has_no_apply_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(sys, "argv", ["cleanup_obsolete_branches.py", "--apply"])
    with pytest.raises(SystemExit):
        module.parse_args()
