from __future__ import annotations

from collections.abc import Iterable
from typing import Any

POLICY_REPOSITORY = "GlacierEQ/job-app-helix"
POLICY_PATH = "LICENSE_POLICY.json"
POLICY_ID = "glaciereq-proprietary-evaluation-partnership-v1"
LICENSE_NAME = "GlacierEQ Proprietary Evaluation and Partnership License v1.0"
LICENSE_REF = "LicenseRef-GlacierEQ-Proprietary-Evaluation-Partnership-1.0"

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
    """Return a safe license posture without pretending to have read license text.

    Root-path presence is enough to route the next action, but never enough to
    silently relicense a repository. Content inspection/provenance must happen
    before changing a controlling license.
    """

    controlling = find_license_path(root_paths)
    policy = f"{POLICY_REPOSITORY}/{POLICY_PATH}"

    if fork:
        return {
            "class": "FORK_OR_UPSTREAM_DERIVED",
            "status": (
                "UPSTREAM_LICENSE_PRESENT_REVIEW_REQUIRED"
                if controlling
                else "UPSTREAM_LICENSE_DISCOVERY_REQUIRED"
            ),
            "controlling_path": controlling,
            "policy": policy,
            "may_relicense_automatically": False,
            "upstream_rights_must_be_preserved": True,
        }

    if controlling:
        return {
            "class": "EXISTING_LICENSE",
            "status": "CONTROLLING_LICENSE_CONTENT_REVIEW_REQUIRED",
            "controlling_path": controlling,
            "policy": policy,
            "may_relicense_automatically": False,
            "upstream_rights_must_be_preserved": False,
        }

    return {
        "class": "NO_ROOT_LICENSE_DETECTED",
        "status": "ORIGINALITY_AND_PROVENANCE_REVIEW_REQUIRED",
        "controlling_path": None,
        "policy": policy,
        "may_relicense_automatically": False,
        "upstream_rights_must_be_preserved": False,
    }


def proprietary_contract() -> dict[str, Any]:
    """Exact machine projection after ownership/provenance has been established."""

    return {
        "class": "GLACIEREQ_ORIGINAL_PROPRIETARY",
        "status": "CONTROLLING",
        "controlling_path": "LICENSE",
        "policy": f"{POLICY_REPOSITORY}/{POLICY_PATH}",
        "license_name": LICENSE_NAME,
        "spdx_expression": LICENSE_REF,
        "may_relicense_automatically": False,
        "upstream_rights_must_be_preserved": False,
    }


def human_notice() -> str:
    return (
        "**Open door, not open source.** You are welcome to inspect this work for "
        "hiring, partnership, research, procurement, investment, collaboration, or "
        "licensing evaluation. Public visibility is not permission to copy, redistribute, "
        "deploy, train on, commercialize, or create derivative works. If you want to "
        "build with it, talk to GlacierEQ — there is a path for that."
    )
