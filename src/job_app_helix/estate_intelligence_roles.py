from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def validate_role_rules(policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = policy.get("role_capability_rules", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("role_capability_rules must be a non-empty list")
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"role rule {index} must be an object")
        matches = row.get("match_any")
        capabilities = row.get("capabilities")
        if (
            not isinstance(matches, list)
            or not all(isinstance(item, str) and item for item in matches)
            or not isinstance(capabilities, list)
            or not all(isinstance(item, str) and item for item in capabilities)
        ):
            raise ValueError(f"role rule {index} is invalid")
        result.append(
            {
                "match_any": [item.casefold() for item in matches],
                "capabilities": list(dict.fromkeys(capabilities)),
            }
        )
    return result


def role_profile(role: str, policy: Mapping[str, Any]) -> list[str]:
    text = role.casefold()
    desired = {
        capability
        for rule in validate_role_rules(policy)
        if any(token in text for token in rule["match_any"])
        for capability in rule["capabilities"]
    }
    return sorted(desired)


def role_fit(
    capabilities: Sequence[str],
    role: str,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    profile = role_profile(role, policy)
    if not profile:
        return {
            "fit_score": 0.0,
            "coverage_state": "UNMAPPED_ROLE",
            "profile_capabilities": [],
            "matched_capabilities": [],
        }
    matched = sorted(set(capabilities) & set(profile))
    return {
        "fit_score": round(100.0 * len(matched) / len(profile), 2),
        "coverage_state": "MAPPED_ROLE",
        "profile_capabilities": profile,
        "matched_capabilities": matched,
    }
