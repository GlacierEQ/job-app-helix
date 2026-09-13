from __future__ import annotations

from collections.abc import Iterable
from typing import Any

POLICY_REPOSITORY = "GlacierEQ/job-app-helix"
POLICY_PATH = "LICENSE_POLICY.json"
POLICY_ID = "glaciereq-proprietary-copyright-v1.1"
LICENSE_NAME = "GlacierEQ Proprietary Copyright License and Enforcement Notice v1.1"
LICENSE_REF = "LicenseRef-GlacierEQ-Proprietary-Copyright-1.1"

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
        "status": "ALL_RIGHTS_RESERVED_TITLE_17",
        "controlling_path": controlling or "LICENSE",
        "policy": f"{POLICY_REPOSITORY}/{POLICY_PATH}",
        "federal_basis": [
            "17 U.S.C. § 102",
            "17 U.S.C. § 106",
            "17 U.S.C. §§ 501-505",
            "17 U.S.C. §§ 411-412",
            "17 U.S.C. § 401(d)",
        ],
        "permission_required": True,
    }


def proprietary_contract() -> dict[str, Any]:
    return {
        "status": "ALL_RIGHTS_RESERVED_TITLE_17",
        "controlling_path": "LICENSE",
        "policy": f"{POLICY_REPOSITORY}/{POLICY_PATH}",
        "license_name": LICENSE_NAME,
        "spdx_expression": LICENSE_REF,
        "federal_basis": [
            "17 U.S.C. § 102",
            "17 U.S.C. § 106",
            "17 U.S.C. §§ 501-505",
            "17 U.S.C. §§ 411-412",
            "17 U.S.C. § 401(d)",
        ],
        "permission_required": True,
    }


def human_notice() -> str:
    return (
        "Copyright © 2026 Casey Del Carpio Barton / GlacierEQ. "
        "**All rights reserved under U.S. copyright law.** "
        "Unauthorized exercise of GlacierEQ's exclusive rights may constitute "
        "copyright infringement under 17 U.S.C. § 501. See [`LICENSE`](LICENSE)."
    )
