#!/usr/bin/env python3
"""Validate the Helix live-link repository fabric.

This validator intentionally performs no network writes. It enforces that the
portfolio inventory and live-link manifest describe the same canonical child
repository set and that Helix remains a projection layer rather than a copied
source-code warehouse.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "manifests" / "portfolio_repositories.json"
LIVE_LINKS = ROOT / "manifests" / "live_repository_links.json"

FORBIDDEN_DIRECTORY_NAMES = {
    "vendor_repositories",
    "repository_copies",
    "repo_copies",
    "source_snapshots",
    "mirrored_sources",
}

REQUIRED_LINK_FIELDS = {
    "repository",
    "canonical_url",
    "default_branch",
    "head_sha",
    "visibility",
    "archived",
    "readme_url",
    "verification_state",
    "last_verified_at",
}


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def validate() -> list[str]:
    errors: list[str] = []
    inventory = _load(INVENTORY)
    links = _load(LIVE_LINKS)

    inventory_names = inventory.get("workspace_repositories")
    link_names = links.get("repositories")
    if not isinstance(inventory_names, list) or not all(
        isinstance(name, str) and name for name in inventory_names
    ):
        errors.append("portfolio inventory must contain non-empty repository names")
        inventory_names = []
    if not isinstance(link_names, list) or not all(
        isinstance(name, str) and name for name in link_names
    ):
        errors.append("live-link manifest must contain non-empty repository names")
        link_names = []

    if len(inventory_names) != len(set(inventory_names)):
        errors.append("portfolio inventory contains duplicate repository names")
    if len(link_names) != len(set(link_names)):
        errors.append("live-link manifest contains duplicate repository names")
    if set(inventory_names) != set(link_names):
        missing = sorted(set(inventory_names) - set(link_names))
        extra = sorted(set(link_names) - set(inventory_names))
        errors.append(
            "live-link set differs from portfolio inventory "
            f"(missing={missing}, extra={extra})"
        )

    expected_total = inventory.get("total_repositories")
    if expected_total != len(inventory_names) + 1:
        errors.append(
            "total_repositories must equal child repositories plus the Helix root"
        )

    if links.get("link_mode") != "live_canonical_repository":
        errors.append("link_mode must be live_canonical_repository")
    if links.get("source_code_copying_into_helix_forbidden") is not True:
        errors.append("source-code copying must be explicitly forbidden")
    if links.get("repository_updates_must_be_observed_from_canonical_origin") is not True:
        errors.append("canonical-origin update observation must be required")

    template = links.get("url_template")
    if template != "https://github.com/GlacierEQ/{repository}":
        errors.append("canonical GitHub URL template is invalid")

    required_projection_fields = links.get("required_projection_fields")
    if set(required_projection_fields or []) != REQUIRED_LINK_FIELDS:
        errors.append("required projection fields do not match the canonical contract")

    for path in ROOT.rglob("*"):
        if path.is_dir() and path.name.lower() in FORBIDDEN_DIRECTORY_NAMES:
            errors.append(f"forbidden copied-source directory exists: {path.relative_to(ROOT)}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: Helix portfolio is link-bound to canonical repositories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
