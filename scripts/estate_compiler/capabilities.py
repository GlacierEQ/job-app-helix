from __future__ import annotations

from collections import defaultdict
from typing import Any

from discover_experience_graph import digest

from .common import EstateCompilerError, flagship_map


def _evidence_text(
    flagship: dict[str, Any] | None,
    assessment: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    text: list[str] = []
    refs: set[str] = set()
    if flagship:
        text.extend(str(flagship.get(key, "")) for key in ("role", "evidence"))
    dimensions = assessment.get("dimensions", {}) if assessment else {}
    if isinstance(dimensions, dict):
        for dimension in dimensions.values():
            if (
                not isinstance(dimension, dict)
                or dimension.get("state") not in {"VERIFIED", "PARTIALLY_VERIFIED"}
            ):
                continue
            text.extend(
                item for item in dimension.get("findings", []) if isinstance(item, str)
            )
            refs.update(
                item for item in dimension.get("receipts", []) if isinstance(item, str)
            )
    return "\n".join(text), sorted(refs)


def build_capability_registry(
    canonical: dict[str, Any],
    flagships: dict[str, Any],
    assessment_by_repo: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    taxonomy = policy.get("capability_taxonomy", {})
    if not isinstance(taxonomy, dict):
        raise EstateCompilerError("capability_taxonomy must be an object")
    flagship_by_repo = flagship_map(flagships)
    donors: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_system: dict[str, list[str]] = {}

    for system in canonical["systems"]:
        repo = system["canonical_repository"]
        text, refs = _evidence_text(
            flagship_by_repo.get(repo), assessment_by_repo.get(repo)
        )
        matched = []
        for capability, config in taxonomy.items():
            signals = config.get("signals", []) if isinstance(config, dict) else []
            if not isinstance(signals, list):
                raise EstateCompilerError(f"Invalid capability signals: {capability}")
            if any(
                isinstance(signal, str) and signal.casefold() in text.casefold()
                for signal in signals
            ):
                matched.append(capability)
                donors[capability].append(
                    {"system_id": system["system_id"], "evidence_refs": refs}
                )
        by_system[system["system_id"]] = sorted(matched)

    records = []
    for capability, rows in sorted(donors.items()):
        count = len({row["system_id"] for row in rows})
        records.append(
            {
                "capability": capability,
                "donor_system_count": count,
                "repetition_state": (
                    "MULTI_SYSTEM_PATTERN" if count >= 2 else "SINGLE_SYSTEM_SIGNAL"
                ),
                "donors": rows,
            }
        )
    result = {
        "schema": "glaciereq.capability-donor-registry.v1",
        "truth_boundary": {
            "repository_names_are_not_capability_evidence": True,
            "repetition_requires_distinct_canonical_systems": True,
        },
        "capabilities": records,
    }
    result["registry_id"] = digest(result)
    return result, by_system
