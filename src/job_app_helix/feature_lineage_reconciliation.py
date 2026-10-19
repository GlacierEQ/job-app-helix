"""Feature-level historical reconciliation for the existing Estate Evolution Engine.

Pure compiler: accepts source-linked feature observations; does not modify repositories,
activate historical code, discover credentials, or infer runtime success from metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA = "glaciereq.feature-lineage.v1"
OUTPUT_SCHEMA = "glaciereq.feature-reconciliation.v1"
SHA = re.compile(r"^[a-f0-9]{40}$")
STATES = ("symbolic", "declared", "discovered", "observed", "verified")
RANK = {value: i for i, value in enumerate(STATES)}
ROLES = {"historical", "current", "successor", "sibling", "backup"}
TRAIT_STATES = {"declared", "observed", "verified"}
SENSITIVITIES = {"ENGINEERING", "PRIVATE", "LEGAL_PRIVATE"}


class LineageError(ValueError):
    """Input cannot support a truthful feature-level reconciliation."""


def _required_str(mapping: Mapping[str, Any], field: str, loc: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise LineageError(f"{loc}.{field} must be a nonempty string")
    return value


def _refs(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v.strip() for v in value):
        raise LineageError(f"{location} needs nonempty evidence_refs")
    return sorted(set(value))


def _source(row: Mapping[str, Any], location: str) -> dict[str, str]:
    raw = row.get("source")
    if not isinstance(raw, dict):
        raise LineageError(f"{location}.source missing")
    source = {k: _required_str(raw, k, location + ".source") for k in ("repository", "commit", "path", "blob_sha")}
    if "/" not in source["repository"]:
        raise LineageError(f"{location}.source.repository needs owner/name")
    if not SHA.fullmatch(source["commit"]) or not SHA.fullmatch(source["blob_sha"]):
        raise LineageError(f"{location}.source must have exact 40-hex commit and blob SHA")
    return source


def _trait(raw: Any, location: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise LineageError(f"{location} must be an object")
    name = _required_str(raw, "trait_id", location)
    description = _required_str(raw, "description", location)
    truth = raw.get("truth")
    if truth not in TRAIT_STATES:
        raise LineageError(f"{location}.truth is not permitted")
    return {"trait_id": name, "description": description, "truth": truth,
            "evidence_refs": _refs(raw.get("evidence_refs"), location)}


def _observation(raw: Any, index: int) -> dict[str, Any]:
    location = f"observations[{index}]"
    if not isinstance(raw, dict):
        raise LineageError(f"{location} must be an object")
    row = {k: _required_str(raw, k, location) for k in ("observation_id", "capability_id", "facet_id", "outcome_id", "intent", "implementation", "observed_at")}
    row["source"] = _source(raw, location)
    if raw.get("role") not in ROLES or raw.get("truth") not in STATES:
        raise LineageError(f"{location} has invalid role or source truth")
    if raw.get("sensitivity") not in SENSITIVITIES:
        raise LineageError(f"{location} needs explicit sensitivity")
    row["role"] = raw["role"]
    row["truth"] = raw["truth"]
    row["sensitivity"] = raw["sensitivity"]
    row["evidence_refs"] = _refs(raw.get("evidence_refs"), location)
    if not isinstance(raw.get("traits", []), list):
        raise LineageError(f"{location}.traits must be a list")
    row["traits"] = [_trait(t, f"{location}.traits[{i}]") for i, t in enumerate(raw.get("traits", []))]
    if any(RANK[trait["truth"]] > RANK[row["truth"]] for trait in row["traits"]):
        raise LineageError(f"{location} cannot promote a trait beyond its source truth")
    if len({x["trait_id"] for x in row["traits"]}) != len(row["traits"]):
        raise LineageError(f"{location} repeats a trait")
    negatives = raw.get("failures", [])
    if not isinstance(negatives, list):
        raise LineageError(f"{location}.failures must be a list")
    row["failures"] = []
    for i, failure in enumerate(negatives):
        label = f"{location}.failures[{i}]"
        if not isinstance(failure, dict) or failure.get("truth") not in ("observed", "verified"):
            raise LineageError(f"{label} requires observed/verified failure evidence")
        row["failures"].append({"trait_id": _required_str(failure, "trait_id", label),
                                "description": _required_str(failure, "description", label),
                                "truth": failure["truth"], "evidence_refs": _refs(failure.get("evidence_refs"), label)})
    return row


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def reconcile_features(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Horizontally group features, vertically compare sources, and expose evidence gaps.

    Never calls GitHub, executes code, promotes capability, mutates sources or guesses
    that an omitted trait is absent. Verified/observed traits remain candidate donors.
    """
    if payload.get("schema") != SCHEMA:
        raise LineageError("unsupported lineage input schema")
    _required_str(payload, "estate_snapshot", "input")
    inputs = payload.get("observations")
    if not isinstance(inputs, list) or not inputs:
        raise LineageError("observations must be a nonempty list")
    rows = [_observation(raw, i) for i, raw in enumerate(inputs)]
    seen: set[str] = set()
    for row in rows:
        if row["observation_id"] in seen:
            raise LineageError("duplicate observation_id")
        seen.add(row["observation_id"])

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["capability_id"], row["facet_id"])].append(row)
    features: list[dict[str, Any]] = []
    for (capability, facet), family in sorted(grouped.items()):
        family.sort(key=lambda row: (row["observed_at"], row["source"]["repository"], row["observation_id"]))
        current = [row for row in family if row["role"] == "current"]
        current_refs = [row["observation_id"] for row in current]
        current_traits = {trait["trait_id"] for row in current for trait in row["traits"] if trait["truth"] in ("observed", "verified")}
        historical_proven: dict[str, list[dict[str, Any]]] = defaultdict(list)
        candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
        failures: list[dict[str, Any]] = []
        for row in family:
            for trait in row["traits"]:
                donor = {"observation_id": row["observation_id"], "source": row["source"], "truth": trait["truth"], "evidence_refs": trait["evidence_refs"], "description": trait["description"]}
                candidates[trait["trait_id"]].append(donor)
                if row["role"] != "current" and trait["truth"] in ("observed", "verified"):
                    historical_proven[trait["trait_id"]].append(donor)
            for failure in row["failures"]:
                failures.append({"observation_id": row["observation_id"], "role": row["role"], **failure})
        gaps = []
        for trait_id, donors in sorted(historical_proven.items()):
            if trait_id not in current_traits:
                gaps.append({"trait_id": trait_id, "classification": "CURRENT_PRESERVATION_UNVERIFIED",
                             "message": "No current observed/verified evidence for historical trait; not proof of removal",
                             "donor_observations": sorted({donor["observation_id"] for donor in donors})})
        for failure in failures:
            if failure["role"] == "current":
                gaps.append({"trait_id": failure["trait_id"], "classification": "CURRENT_FAILURE_EVIDENCED",
                             "message": failure["description"], "donor_observations": [failure["observation_id"]],
                             "failure_evidence_refs": failure["evidence_refs"]})
        selected = []
        for trait_id, donors in sorted(candidates.items()):
            best_rank = max(RANK[donor["truth"]] for donor in donors)
            leaders = [d for d in donors if RANK[d["truth"]] == best_rank]
            selected.append({"trait_id": trait_id, "candidate_truth": STATES[best_rank],
                             "coequal_donors": sorted(leaders, key=lambda donor: (donor["source"]["repository"], donor["observation_id"])),
                             "promotion_state": "not_promoted_requires_comparative_tests_and_readback"})
        sensitive = sorted({row["sensitivity"] for row in family})
        features.append({"capability_id": capability, "facet_id": facet,
                         "sensitivity": "INTERNAL_ONLY" if any(s != "ENGINEERING" for s in sensitive) else "ENGINEERING",
                         "historical_objectives": [{"observation_id": row["observation_id"], "intent": row["intent"]} for row in family],
                         "vertical_history": [{"observation_id": row["observation_id"], "role": row["role"],
                                              "observed_at": row["observed_at"], "source": row["source"],
                                              "truth": row["truth"], "implementation": row["implementation"],
                                              "evidence_refs": row["evidence_refs"]} for row in family],
                         "current_observation_ids": sorted(current_refs),
                         "substantive_outcome_ids": sorted({row["outcome_id"] for row in family}),
                         "synthesis_candidates": selected,
                         "hidden_harm_candidates": sorted(gaps, key=lambda gap: (gap["trait_id"], gap["classification"])),
                         "failure_evidence": failures,
                         "status": "COMPOSITION_REVIEW_REQUIRED" if gaps else "SOURCE_LINKED_REVIEW_REQUIRED",
                         "effects_performed": False})
    result = {"schema": OUTPUT_SCHEMA, "estate_snapshot": payload["estate_snapshot"],
              "capability_facet_count": len(features), "observation_count": len(rows),
              "distinct_substantive_outcome_count": len({row["outcome_id"] for row in rows}),
              "features": features, "mutation_performed": False,
              "truth_boundary": "source/metadata analysis only; requires runtime tests and provider readback for promotion"}
    result["receipt_sha256"] = _fingerprint(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only estate feature lineage compiler")
    parser.add_argument("input", type=Path, help="Source-linked, sensitivity-classified observation JSON")
    parser.add_argument("--output", type=Path, help="Optional receipt path; defaults to stdout")
    args = parser.parse_args()
    result = reconcile_features(json.loads(args.input.read_text(encoding="utf-8")))
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
