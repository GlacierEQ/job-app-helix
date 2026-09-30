from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path
from types import ModuleType

import pytest

from job_app_helix.crystallization_crawler import Repository

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "crawl_crystallization_estate.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("crawl_crystallization_estate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _repos(count: int) -> list[Repository]:
    return [
        Repository(
            position=index,
            repository=f"GlacierEQ/repo-{index:03d}",
            repository_id=index + 1,
            default_branch="main",
            visibility="private",
            archived=False,
            fork=False,
            can_push=True,
            can_admin=True,
            parent=None,
        )
        for index in range(count)
    ]


def _args(**overrides) -> Namespace:
    values = {
        "repository": [],
        "hourly_shard_size": None,
        "start": 0,
        "limit": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_hourly_shards_cover_each_range_in_cycle() -> None:
    module = _load()
    repositories = _repos(53)
    starts = []

    for hour in range(3):
        selected, start, limit, shard_index = module.select_repositories(
            repositories,
            _args(hourly_shard_size=25),
            epoch_seconds=hour * 3600,
        )
        starts.append(start)
        assert shard_index == hour
        assert limit == 25
        assert [repo.position for repo in selected] == list(
            range(start, min(start + 25, len(repositories)))
        )

    assert starts == [0, 25, 50]


def test_hourly_shard_wraps_after_last_shard() -> None:
    module = _load()
    repositories = _repos(53)
    _, start, _, shard_index = module.select_repositories(
        repositories,
        _args(hourly_shard_size=25),
        epoch_seconds=3 * 3600,
    )

    assert shard_index == 0
    assert start == 0


def test_explicit_repository_selection_preserves_accessible_order() -> None:
    module = _load()
    repositories = _repos(5)
    selected, start, limit, shard_index = module.select_repositories(
        repositories,
        _args(repository=["GlacierEQ/repo-003", "GlacierEQ/repo-001"]),
    )

    assert [repo.position for repo in selected] == [1, 3]
    assert start is None
    assert limit is None
    assert shard_index is None


def test_missing_explicit_repository_fails_closed() -> None:
    module = _load()
    with pytest.raises(module.CrawlError, match="not accessible"):
        module.select_repositories(
            _repos(2),
            _args(repository=["GlacierEQ/missing"]),
        )


def test_hourly_sharding_rejects_manual_offset_mixture() -> None:
    module = _load()
    with pytest.raises(module.CrawlError, match="cannot be combined"):
        module.select_repositories(
            _repos(10),
            _args(hourly_shard_size=5, start=1),
        )
