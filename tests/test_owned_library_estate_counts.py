from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "census_owned_library.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("census_owned_library_estate", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_payload_splits_total_holdings_native_repositories_and_forks() -> None:
    module = _load_module()
    record = module.RepositoryRecord
    records = [
        record(
            position=0,
            repository="GlacierEQ/native-public",
            repository_id=1,
            visibility="public",
            default_branch="main",
            archived=False,
            fork=False,
            classification="UNGOVERNED_PUBLIC_INVENTORY",
        ),
        record(
            position=1,
            repository="GlacierEQ/native-archive",
            repository_id=2,
            visibility="private",
            default_branch="main",
            archived=True,
            fork=False,
            classification="ARCHIVE_BACKUP_OR_FORK",
        ),
        record(
            position=2,
            repository="GlacierEQ/upstream-fork",
            repository_id=3,
            visibility="public",
            default_branch="main",
            archived=False,
            fork=True,
            classification="UPSTREAM_OR_FORK_REVIEW",
        ),
    ]

    payload = module.build_payload(records, "GlacierEQ")

    assert payload["repository_count"] == 3
    assert payload["native_repository_count"] == 2
    assert payload["fork_repository_count"] == 1
    assert payload["active_native_repository_count"] == 1
    assert payload["archived_native_repository_count"] == 1
    assert payload["fork_count"] == 1
    assert payload["native_visibility_counts"] == {"private": 1, "public": 1}
    assert payload["fork_visibility_counts"] == {"public": 1}
    assert any(
        "Native repository count excludes forks" in item
        for item in payload["nonclaims"]
    )
