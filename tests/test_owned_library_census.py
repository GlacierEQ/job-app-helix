from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "census_owned_library.py"
SNAPSHOT = ROOT / "manifests" / "owned_library_census_2026-07-31.json"
PACKAGE = ROOT / "hire_package" / "casey-barton"
STATUS = ROOT / "status" / "owned-library-census-2026-07-31.json"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("census_owned_library", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


class FakeSource:
    def __init__(self, pages: dict[int, list[dict[str, Any]]]) -> None:
        self.pages = pages
        self.calls: list[tuple[int, int]] = []

    def list_page(self, page: int, per_page: int) -> list[dict[str, Any]]:
        self.calls.append((page, per_page))
        return self.pages.get(page, [])


def _repository(
    name: str,
    repository_id: int,
    *,
    visibility: str = "public",
    default_branch: str = "main",
    archived: bool = False,
    fork: bool = False,
) -> dict[str, Any]:
    return {
        "full_name": f"GlacierEQ/{name}",
        "id": repository_id,
        "visibility": visibility,
        "default_branch": default_branch,
        "archived": archived,
        "fork": fork,
    }


def test_checked_in_snapshot_preserves_exact_scope_boundaries() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    assert snapshot["schema"] == "glaciereq.owned-library-census-summary.v1"
    assert snapshot["kind"] == "PUBLIC_SAFE_CURATED_SUMMARY"
    assert snapshot["generated_receipt"]["schema"] == (
        "glaciereq.owned-library-census-receipt.v1"
    )
    assert snapshot["discovery"]["exact_repository_count"] == 1171
    assert snapshot["discovery"]["highest_present_offset"] == 1170
    assert snapshot["discovery"]["first_absent_offset"] == 1171
    assert snapshot["scopes"]["recruiter_portfolio"]["repository_count"] == 66
    assert snapshot["scopes"]["priority_spine"]["repository_count"] == 9
    assert len(snapshot["candidate_expansion"]) == 5
    assert snapshot["mutation_policy"]["blind_pull_push_sync"] is False


def test_expansion_map_is_truth_bounded_and_public_safe() -> None:
    text = (PACKAGE / "PORTFOLIO_EXPANSION_MAP.md").read_text(encoding="utf-8")

    assert "1,171 owner-accessible repositories" in text
    assert "Exact recruiter boundary: **66 repositories**" in text
    assert "Blind mass mutation performed: **none**" in text
    assert "1,171 production systems" in text
    assert "does not establish authorship" in text
    assert "name withheld" in text


def test_public_census_surfaces_withhold_private_candidate_name() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    machine = json.loads(
        (PACKAGE / "owned_library_census.json").read_text(encoding="utf-8")
    )
    status = json.loads(STATUS.read_text(encoding="utf-8"))

    private_summary = snapshot["candidate_expansion"][2]
    assert private_summary["opaque_id"] == "private-candidate-1"
    assert "repository" not in private_summary
    assert "PRIVATE_CANDIDATE_NAME_WITHHELD" in machine["candidate_expansion"]
    assert status["new_entries"][2]["opaque_id"] == "private-candidate-1"
    assert "repository" not in status["new_entries"][2]


def test_discovery_classifies_governed_candidate_and_excluded_repositories() -> None:
    module = _load_module()
    source = FakeSource(
        {
            1: [
                _repository("AKOS", 1),
                _repository("Kimi-K3", 2),
            ],
            2: [
                _repository("private-dashboard", 3, visibility="private"),
                _repository("Z-BACKUP-example", 4, visibility="private"),
            ],
        }
    )

    records = module.discover(
        source,
        recruiter_portfolio={"GlacierEQ/AKOS"},
        priority_spine=set(),
        per_page=2,
    )

    by_repository = {record.repository: record for record in records}
    assert by_repository["GlacierEQ/AKOS"].classification == "RECRUITER_PORTFOLIO"
    assert by_repository["GlacierEQ/Kimi-K3"].classification == "CANDIDATE_EXPANSION"
    assert (
        by_repository["GlacierEQ/private-dashboard"].classification
        == "PRIVATE_REVIEW_REQUIRED"
    )
    assert (
        by_repository["GlacierEQ/Z-BACKUP-example"].classification
        == "ARCHIVE_BACKUP_OR_FORK"
    )
    assert source.calls == [(1, 2), (2, 2), (3, 2)]


def test_discovery_rejects_duplicate_repository_identity() -> None:
    module = _load_module()
    source = FakeSource(
        {
            1: [_repository("duplicate", 1)],
            2: [_repository("duplicate", 1)],
        }
    )

    with pytest.raises(module.CensusError, match="Duplicate repository"):
        module.discover(
            source,
            recruiter_portfolio=set(),
            priority_spine=set(),
            per_page=1,
        )


def test_github_api_error_does_not_echo_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    token = "sensitive-token-value"

    def fail_request(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise urllib.error.URLError(f"request rejected with {token}")

    monkeypatch.setattr(module.urllib.request, "urlopen", fail_request)
    api = module.GitHubAPI("GlacierEQ", token)

    with pytest.raises(module.CensusError) as caught:
        api.list_page(1, 100)

    assert token not in str(caught.value)
    assert str(caught.value) == "GitHub census request failed for page 1"


def test_payload_separates_inventory_from_proof() -> None:
    module = _load_module()
    record = module.RepositoryRecord(
        position=0,
        repository="GlacierEQ/example",
        repository_id=1,
        visibility="public",
        default_branch="main",
        archived=False,
        fork=False,
        classification="UNGOVERNED_PUBLIC_INVENTORY",
    )

    payload = module.build_payload([record], "GlacierEQ")

    assert payload["state"] == "VERIFIED_INVENTORY"
    assert payload["distribution"] == "INTERNAL_FULL_CENSUS"
    assert payload["repository_count"] == 1
    assert payload["classification_counts"] == {
        "UNGOVERNED_PUBLIC_INVENTORY": 1
    }
    assert any("does not establish authorship" in item for item in payload["nonclaims"])
