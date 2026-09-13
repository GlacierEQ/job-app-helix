from __future__ import annotations

from collections.abc import Iterable
from typing import Any

POLICY_REPOSITORY = "GlacierEQ/job-app-helix"
POLICY_PATH = "LICENSE_POLICY.json"
POLICY_ID = "glaciereq-proprietary-v1"
LICENSE_NAME = "GlacierEQ Proprietary License v1.0"
LICENSE_REF = "LicenseRef-GlacierEQ-Proprietary-1.0"

_LICENSE_NAMES = (
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "COPYING",
    "COPYING.md",
    "COPYING.txt",
)


def find_license_path(root_paths: Iterable[str]) -> str | None:
    by_casefold = {path.casefold(): path for path in root_paths}
    for candidate in _LICENSE_NAMES:
        hit = by_casefold.get(candidate.casefold())
        if hit:
            return hit
    return None


def infer_license_contract(
    root_paths: Iterable[str],
    *,
    fork: bool,
) -> dict[str, Any]:
    """Expose the controlling rights notice without inventing additional permissions."""

    controlling = find_license_path(root_paths)
    if fork:
        return {
            "status": "PRESERVE_EXISTING_RIGHTS",
            "controlling_path": controlling,
            "policy": f"{POLICY_REPOSITORY}/{POLICY_PATH}",
        }

    return {
        "status": "ALL_RIGHTS_RESERVED",
        "controlling_path": controlling or "LICENSE",
        "policy": f"{POLICY_REPOSITORY}/{POLICY_PATH}",
        "permission_required": True,
    }


def proprietary_contract() -> dict[str, Any]:
    return {
        "status": "ALL_RIGHTS_RESERVED",
        "controlling_path": "LICENSE",
        "policy": f"{POLICY_REPOSITORY}/{POLICY_PATH}",
        "license_name": LICENSE_NAME,
        "spdx_expression": LICENSE_REF,
        "permission_required": True,
    }


def human_notice() -> str:
    return (
        "Copyright (c) 2026 Casey Del Carpio Barton / GlacierEQ. "
        "**All rights reserved.** See [`LICENSE`](LICENSE)."
    )
