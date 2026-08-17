from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.estate_visibility import (
    compile_estate_visibility,
    estate_visibility_payload,
)
from job_app_helix.portfolio_models import PortfolioProgramError


def _write_projection(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "glaciereq.portfolio.inventory.v1",
                "owner": "GlacierEQ",
                "portfolio_root": "job-app-helix",
                "scope": "ADMITTED_JOB_ENGINEERING_ROLLOUT_PROJECTION",
                "is_full_estate_inventory": False,
                "total_repositories": 2,
                "workspace_repositories": ["alpha"],
            }
        ),
        encoding="utf-8",
    )


def _write_census(path: Path) -> None:
    rows = [
        {
            "position": 0,
            "repository": "GlacierEQ/job-app-helix",
            "repository_id": 1,
            "visibility": "public",
            "default_branch": "main",
            "archived": False,
            "fork": False,
            "classification": "ADMITTED_JOB_ROLLOUT",
        },
        {
            "position": 1,
            "repository": "GlacierEQ/alpha",
            "repository_id": 2,
            "visibility": "public",
            "default_branch": "main",
            "archived": False,
            "fork": False,
            "classification": "ADMITTED_JOB_ROLLOUT",
        },
        {
            "position": 2,
            "repository": "GlacierEQ/private-power",
            "repository_id": 3,
            "visibility": "private",
            "default_branch": "main",
            "archived": False,
            "fork": False,
            "classification": "VISIBLE_PRIVATE_INVENTORY",
        },
        {
            "position": 3,
            "repository": "GlacierEQ/archive-donor",
            "repository_id": 4,
            "visibility": "private",
            "default_branch": "main",
            "archived": True,
            "fork": False,
            "classification": "VISIBLE_ARCHIVE_BACKUP",
        },
        {
            "position": 4,
            "repository": "GlacierEQ/upstream-donor",
            "repository_id": 5,
            "visibility": "public",
            "default_branch": "main",
            "archived": False,
            "fork": True,
            "classification": "VISIBLE_UPSTREAM_FORK",
        },
    ]
    path.write_text(
        json.dumps(
            {
                "schema": "glaciereq.owned-library-census-receipt.v2",
                "owner": "GlacierEQ",
                "distribution": "INTERNAL_FULL_CENSUS",
                "visibility_policy": "DISCOVER_ALL_ROUTE_AFTER",
                "repository_count": len(rows),
                "hidden_repository_count": 0,
                "repositories": rows,
            }
        ),
        encoding="utf-8",
    )


def test_full_estate_is_visible_before_rollout_admission(tmp_path: Path) -> None:
    census = tmp_path / "census.json"
    projection = tmp_path / "projection.json"
    _write_census(census)
    _write_projection(projection)

    candidates = compile_estate_visibility(
        census_path=census,
        rollout_projection_path=projection,
    )
    payload = estate_visibility_payload(candidates)

    assert len(candidates) == 5
    assert payload["repository_count"] == 5
    assert payload["hidden_repository_count"] == 0
    by_repo = {candidate.repository: candidate for candidate in candidates}
    assert by_repo["GlacierEQ/alpha"].route == "ADMITTED_JOB_ROLLOUT"
    assert by_repo["GlacierEQ/private-power"].route == "DISCOVERED_PRIVATE_CANDIDATE"
    assert by_repo["GlacierEQ/archive-donor"].route == "DISCOVERED_ARCHIVE_DONOR"
    assert by_repo["GlacierEQ/upstream-donor"].route == "DISCOVERED_UPSTREAM_DONOR"


def test_projection_cannot_impersonate_full_estate(tmp_path: Path) -> None:
    census = tmp_path / "census.json"
    projection = tmp_path / "projection.json"
    _write_census(census)
    _write_projection(projection)
    payload = json.loads(projection.read_text(encoding="utf-8"))
    payload["is_full_estate_inventory"] = True
    projection.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PortfolioProgramError, match="is_full_estate_inventory=false"):
        compile_estate_visibility(
            census_path=census,
            rollout_projection_path=projection,
        )


def test_compiler_rejects_any_hidden_repository_count(tmp_path: Path) -> None:
    census = tmp_path / "census.json"
    projection = tmp_path / "projection.json"
    _write_census(census)
    _write_projection(projection)
    payload = json.loads(census.read_text(encoding="utf-8"))
    payload["hidden_repository_count"] = 1
    census.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PortfolioProgramError, match="hidden repositories"):
        compile_estate_visibility(
            census_path=census,
            rollout_projection_path=projection,
        )
