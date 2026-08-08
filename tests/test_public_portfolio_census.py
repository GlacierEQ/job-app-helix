from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "census_public_portfolio.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("public_portfolio_census", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _manifest() -> dict:
    return {
        "total_repositories": 3,
        "workspace_repositories": ["AKOS", "job-application"],
    }


def _repo(name: str, repository_id: int, *, fork: bool = False) -> dict:
    return {
        "full_name": f"GlacierEQ/{name}",
        "id": repository_id,
        "visibility": "public",
        "private": False,
        "default_branch": "main",
        "archived": False,
        "fork": fork,
    }


def test_public_census_contains_only_governed_public_repositories() -> None:
    module = _module()
    payload = module.build_census(
        manifest=_manifest(),
        owner="GlacierEQ",
        repositories=[
            _repo("job-application", 2),
            _repo("unrelated-public-repo", 99),
            _repo("job-app-helix", 3),
            _repo("AKOS", 1),
        ],
        generated_at="2026-08-08T16:00:00+00:00",
    )

    assert payload["state"] == "VERIFIED_INVENTORY"
    assert payload["scope"] == "PUBLIC_ADMITTED_PORTFOLIO_ONLY"
    assert payload["repository_count"] == 3
    assert payload["native_repository_count"] == 3
    assert payload["fork_repository_count"] == 0
    assert payload["private_repository_count"] == 0
    assert [row["repository"] for row in payload["repositories"]] == [
        "GlacierEQ/AKOS",
        "GlacierEQ/job-app-helix",
        "GlacierEQ/job-application",
    ]
    assert payload["boundary"]["authenticated_private_estate_not_queried"] is True
    assert payload["boundary"]["raw_owned_estate_cardinality_not_inferred"] is True


def test_public_census_rejects_missing_governed_repository() -> None:
    module = _module()
    with pytest.raises(module.PublicPortfolioCensusError, match="incomplete"):
        module.build_census(
            manifest=_manifest(),
            owner="GlacierEQ",
            repositories=[_repo("AKOS", 1), _repo("job-app-helix", 3)],
        )


def test_public_census_rejects_non_public_governed_repository() -> None:
    module = _module()
    private = _repo("AKOS", 1)
    private["visibility"] = "private"
    private["private"] = True
    with pytest.raises(module.PublicPortfolioCensusError, match="non-public"):
        module.build_census(
            manifest=_manifest(),
            owner="GlacierEQ",
            repositories=[
                private,
                _repo("job-app-helix", 3),
                _repo("job-application", 2),
            ],
        )


def test_public_census_rejects_manifest_cardinality_drift() -> None:
    module = _module()
    manifest = _manifest()
    manifest["total_repositories"] = 4
    with pytest.raises(module.PublicPortfolioCensusError, match="cardinality"):
        module.build_census(
            manifest=manifest,
            owner="GlacierEQ",
            repositories=[],
        )
