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
            "blocked": "6" * 40,
            "restored": "7" * 40,
            "active": "8" * 40,
        }
        self.stale_files = ["pyproject.toml", "uv.lock"]
        self.stale_open_pulls: list[dict[str, Any]] = []
        self.candidate_merged = False
        self.ref_failure: str | None = None
        self.ref_calls: list[str] = []

    def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
        self.ref_calls.append(branch)
        if branch == self.ref_failure:
            raise RuntimeError("provider failure should be normalized by test adapter")
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


class FailingRefAPI(FakeAPI):
    def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
        self.ref_calls.append(branch)
        if branch == "blocked":
            module = _load_module()
            raise module.CleanupError("transient ref read failure")
        if branch not in self.refs:
            return 404, None
        return 200, {"object": {"sha": self.refs[branch]}}


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "glaciereq.obsolete-branches.v1",
                "repository": "GlacierEQ/job-app-helix",
                "default_branch": "main",
                "blocked_refs": [
                    {
                        "name": "blocked",
                        "expected_head_sha": "6" * 40,
                        "state": "DELETE_BLOCKED",
                    }
                ],
                "restored_refs_after_failed_transaction": [
                    {
                        "name": "restored",
                        "expected_head_sha": "7" * 40,
                        "state": "RESTORED_AFTER_FAILED_TRANSACTION",
                    }
                ],
                "preserved_active_refs": [
                    {
                        "name": "active",
                        "expected_head_sha": "8" * 40,
                        "state": "PRESERVED_RECOVERY_REF",
                    }
                ],
                "retired_refs": [
                    {
                        "name": "absent",
                        "expected_head_sha": "9" * 40,
                        "state": "REF_ABSENT_VERIFIED",
                    }
                ],
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


def test_reference_manifest_has_unique_lineage_records() -> None:
    module = _load_module()
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = module._audit_entries(payload)
    names = [entry["name"] for entry in entries]

    assert payload["schema"] == "glaciereq.obsolete-branches.v1"
    assert payload["default_branch"] == "main"
    assert "main" not in names
    assert len(names) == len(set(names))
    assert set(payload["blocked_refs"][index]["name"] for index in range(len(payload["blocked_refs"]))).issubset(names)
    assert set(
        payload["restored_refs_after_failed_transaction"][index]["name"]
        for index in range(len(payload["restored_refs_after_failed_transaction"]))
    ).issubset(names)
    assert set(
        payload["preserved_active_refs"][index]["name"]
        for index in range(len(payload["preserved_active_refs"]))
    ).issubset(names)


def test_script_exposes_no_ref_mutation_methods() -> None:
    module = _load_module()
    assert not hasattr(module.GitHubAPI, "delete_ref")
    assert not hasattr(module.GitHubAPI, "create_ref")


@pytest.mark.parametrize("verb", ["POST", "PUT", "PATCH", "DELETE"])
def test_provider_adapter_rejects_non_get_methods(verb: str) -> None:
    module = _load_module()
    api = module.GitHubAPI("GlacierEQ/job-app-helix", "token")
    with pytest.raises(module.CleanupError, match="mutation methods are prohibited"):
        api.request(verb, "/repos/GlacierEQ/job-app-helix/git/refs/heads/example")


def test_audit_covers_preservation_buckets_and_preserves_refs(
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

    by_name = {result.branch: result for result in results}
    assert by_name["blocked"].outcome == "ACTIVE_IN_MESH"
    assert by_name["restored"].outcome == "ACTIVE_IN_MESH"
    assert by_name["active"].outcome == "ACTIVE_IN_MESH"
    assert by_name["absent"].outcome == "PRESERVE_HISTORICAL_LINEAGE_POINTER"
    assert {"blocked", "restored", "active", "merged", "superseded", "stale", "candidate", "absent"}.issubset(fake.ref_calls)

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema"] == "glaciereq.branch-lineage-audit-receipt.v2"
    assert payload["mode"] == "READ_ONLY_LINEAGE_AUDIT"
    assert payload["conclusion"] == "VERIFIED_READ_ONLY"
    assert payload["anti_replacement"]["remote_ref_deletion_authority"] is False
    assert payload["anti_replacement"]["drained_terminal_state"] == "PRESERVE_DRAINED_LINEAGE"


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


def test_repository_override_must_match_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    called = False

    def factory(repository: str, token: str | None) -> FakeAPI:
        nonlocal called
        called = True
        return FakeAPI()

    monkeypatch.setattr(module, "GitHubAPI", factory)
    manifest = tmp_path / "branches.json"
    _write_manifest(manifest)

    with pytest.raises(module.CleanupError, match="does not match"):
        module.audit(
            manifest,
            repository="GlacierEQ/wrong-repository",
            token="token",
            output=None,
        )
    assert called is False


def test_provider_ref_failure_writes_findings_receipt_then_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()

    class ProviderFailureAPI(FakeAPI):
        def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
            self.ref_calls.append(branch)
            if branch == "blocked":
                raise module.CleanupError("transient ref read failure")
            if branch not in self.refs:
                return 404, None
            return 200, {"object": {"sha": self.refs[branch]}}

    fake = ProviderFailureAPI()
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    with pytest.raises(module.CleanupError, match="receipt was preserved"):
        module.audit(
            manifest,
            repository="GlacierEQ/job-app-helix",
            token="token",
            output=receipt,
        )

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "READ_ONLY_WITH_FINDINGS"
    blocked = next(item for item in payload["results"] if item["branch"] == "blocked")
    assert blocked["preflight"] == "READBACK_UNRESOLVED"
    assert blocked["outcome"] == "ACTIVE_IN_MESH"
    assert "stale" in fake.ref_calls


def test_failed_historical_preflight_writes_receipt_then_fails(
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

    with pytest.raises(module.CleanupError, match="receipt was preserved"):
        module.audit(
            manifest,
            repository="GlacierEQ/job-app-helix",
            token="token",
            output=receipt,
        )

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "READ_ONLY_WITH_FINDINGS"
    stale = next(item for item in payload["results"] if item["branch"] == "stale")
    assert stale["preflight"] == "FAILED"
    assert stale["outcome"] == "ACTIVE_IN_MESH"


def test_malformed_expected_files_becomes_findings_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    fake = FakeAPI()
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    stale = next(entry for entry in payload["branches"] if entry["name"] == "stale")
    stale["expected_files"] = None
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(module.CleanupError, match="receipt was preserved"):
        module.audit(
            manifest,
            repository="GlacierEQ/job-app-helix",
            token="token",
            output=receipt,
        )
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    stale_result = next(
        item for item in receipt_payload["results"] if item["branch"] == "stale"
    )
    assert stale_result["preflight"] == "FAILED"


def test_stale_dependency_with_current_cli_is_not_verified(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()

    class CurrentCliAPI(FakeAPI):
        def read_text_file(self, path: str, ref: str) -> str:
            return (
                '[project]\nname = "job-app-helix"\nversion = "0.2.0"\n'
                '[project.scripts]\njob-app-helix-portfolio = "job_app_helix.portfolio_cli:main"\n'
            )

    fake = CurrentCliAPI()
    monkeypatch.setattr(module, "GitHubAPI", lambda repository, token: fake)
    manifest = tmp_path / "branches.json"
    receipt = tmp_path / "receipt.json"
    _write_manifest(manifest)

    with pytest.raises(module.CleanupError, match="receipt was preserved"):
        module.audit(
            manifest,
            repository="GlacierEQ/job-app-helix",
            token="token",
            output=receipt,
        )
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    stale = next(item for item in payload["results"] if item["branch"] == "stale")
    assert stale["preflight"] == "FAILED"


def test_cli_defaults_preserve_receipt_and_safe_legacy_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setenv("GITHUB_REPOSITORY", "GlacierEQ/job-app-helix")
    monkeypatch.setattr(
        sys,
        "argv",
        ["cleanup_obsolete_branches.py", "--token", "test-token", "--apply"],
    )
    args = module._parse_args()
    assert args.repository == "GlacierEQ/job-app-helix"
    assert args.output == module.DEFAULT_OUTPUT
    assert args.token == "test-token"
    assert args.apply is True
    assert not hasattr(module.GitHubAPI, "delete_ref")


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
