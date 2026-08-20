#!/usr/bin/env python3
"""Validate the 112-company innovation expansion and P0 execution queue."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "manifests" / "company_dossiers.json"
SHARD = (
    ROOT
    / "manifests"
    / "company_dossiers"
    / "innovation_expansion_2026_08_09.json"
)
MASTER = (
    ROOT
    / "manifests"
    / "application_intelligence"
    / "company_innovation_hypotheses.v1.json"
)
QUEUE = (
    ROOT
    / "manifests"
    / "application_intelligence"
    / "company_innovation_execution_queue.v1.json"
)


class ExpansionValidationError(ValueError):
    pass


def load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ExpansionValidationError(f"{path} must contain an object")
    return payload


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExpansionValidationError(message)


def unique_strings(value: object, label: str) -> list[str]:
    require(isinstance(value, list), f"{label} must be an array")
    items = value
    require(
        all(isinstance(item, str) and item for item in items),
        f"{label} contains invalid ids",
    )
    require(len(items) == len(set(items)), f"{label} contains duplicates")
    return items


def main() -> int:
    index = load(INDEX)
    shard = load(SHARD)
    master = load(MASTER)
    queue = load(QUEUE)

    require(
        index.get("schema") == "glaciereq.company-dossiers-index.v2",
        "company index schema drift",
    )
    require(
        shard.get("schema") == "glaciereq.company-dossiers-shard.v2",
        "innovation shard schema drift",
    )
    require(
        master.get("schema") == "glaciereq.company-innovation-hypotheses.v1",
        "master hypothesis schema drift",
    )
    require(
        queue.get("schema") == "glaciereq.company-innovation-execution-queue.v1",
        "execution queue schema drift",
    )

    tracks = unique_strings(
        index.get("required_company_tracks"),
        "required_company_tracks",
    )
    require(
        len(tracks) == 166,
        f"expected 166 governed tracks, observed {len(tracks)}",
    )
    require(
        "manifests/company_dossiers/innovation_expansion_2026_08_09.json"
        in index.get("dossier_files", []),
        "innovation expansion shard is not indexed",
    )

    companies = shard.get("companies")
    require(
        isinstance(companies, list),
        "innovation expansion companies must be an array",
    )
    new_ids = [
        item.get("company_id")
        for item in companies
        if isinstance(item, dict)
    ]
    require(
        len(companies) == 90,
        f"expected 90 net-new company records, observed {len(companies)}",
    )
    require(
        len(new_ids) == 90
        and all(isinstance(item, str) and item for item in new_ids),
        "invalid net-new company ids",
    )
    require(
        len(new_ids) == len(set(new_ids)),
        "innovation expansion contains duplicate company ids",
    )
    require(
        set(new_ids) <= set(tracks),
        "net-new expansion contains a company absent from governed tracks",
    )
    require(
        shard.get("defaults", {}).get("track_state")
        == "CANDIDATE_TARGET_REQUIRES_DIRECT_EVIDENCE",
        "net-new tracks must remain candidate/evidence-gated",
    )

    existing = unique_strings(
        master.get("existing_track_ids"),
        "existing_track_ids",
    )
    net_new = unique_strings(
        master.get("net_new_track_ids"),
        "net_new_track_ids",
    )
    p0 = unique_strings(master.get("p0_track_ids"), "p0_track_ids")
    require(master.get("record_count") == 112, "master record_count must be 112")
    require(
        len(existing) == 22,
        f"expected 22 existing-track enrichments, observed {len(existing)}",
    )
    require(
        len(net_new) == 90,
        f"expected 90 net-new tracks, observed {len(net_new)}",
    )
    require(len(p0) == 25, f"expected 25 P0 tracks, observed {len(p0)}")
    require(
        set(existing).isdisjoint(net_new),
        "existing and net-new track sets overlap",
    )
    require(
        set(net_new) == set(new_ids),
        "master net-new set differs from dossier expansion shard",
    )

    families = master.get("families", {})
    require(isinstance(families, dict), "families must be an object")
    family_sets = [set(value) for value in families.values()]
    require(
        set(existing) | set(net_new) == set().union(*family_sets),
        "family membership does not equal the 112-company hypothesis set",
    )
    require(
        sum(len(value) for value in families.values()) == 112,
        "family membership must contain exactly 112 unique placements",
    )
    require(
        set(existing) | set(net_new) <= set(tracks),
        "master hypothesis registry references an ungoverned track",
    )

    dedupe = master.get("dedupe", {})
    expected_counts = {
        "reference_tracks_before_expansion": 76,
        "already_reference_tracks": 22,
        "net_new_tracks": 90,
        "reference_tracks_after_expansion": 166,
        "p0_total": 25,
        "p0_existing_tracks": 9,
        "p0_net_new_tracks": 16,
    }
    for field, expected in expected_counts.items():
        require(
            dedupe.get(field) == expected,
            f"dedupe.{field} expected {expected}, observed {dedupe.get(field)!r}",
        )

    boundary = master.get("truth_boundary", {})
    require(
        boundary.get("company_affiliation_claimed") is False,
        "affiliation boundary must remain false",
    )
    require(
        boundary.get("internal_company_conditions_claimed") is False,
        "internal-condition boundary must remain false",
    )
    require(
        boundary.get("bottlenecks_are_glaciereq_hypotheses") is True,
        "bottleneck hypothesis boundary drift",
    )
    require(
        boundary.get("innovations_are_candidate_mechanisms_not_proven_results")
        is True,
        "candidate-mechanism boundary drift",
    )
    require(
        boundary.get("proof_gates_must_be_measured_before_promotion") is True,
        "proof gate boundary drift",
    )

    require(
        queue.get("source")
        == "manifests/application_intelligence/company_innovation_hypotheses.v1.json",
        "queue source binding drift",
    )
    items = queue.get("queue")
    require(
        isinstance(items, list) and len(items) == 25,
        "execution queue must contain 25 targets",
    )
    queue_ids = [item.get("company_id") for item in items]
    ranks = [item.get("rank") for item in items]
    require(
        len(queue_ids) == len(set(queue_ids)),
        "execution queue contains duplicate company ids",
    )
    require(queue_ids == p0, "P0 queue order differs from reference p0_track_ids")
    require(ranks == list(range(1, 26)), "P0 queue ranks must be contiguous 1..25")
    require(
        queue.get("existing_track_deepen_count") == 9,
        "P0 existing-track count drift",
    )
    require(
        queue.get("net_new_admission_count") == 16,
        "P0 net-new count drift",
    )
    require(
        sum(item.get("track_action") == "DEEPEN_EXISTING" for item in items)
        == 9,
        "P0 DEEPEN_EXISTING count drift",
    )
    require(
        sum(item.get("track_action") == "ADMIT_NET_NEW" for item in items)
        == 16,
        "P0 ADMIT_NET_NEW count drift",
    )
    require(
        all(item.get("next_gate") == "CURRENT_SOURCE_VALIDATION" for item in items),
        "P0 entries must begin at current-source validation",
    )
    require(
        all(
            isinstance(item.get("lead_innovation"), dict)
            and item["lead_innovation"].get("name")
            and item["lead_innovation"].get("mechanism")
            for item in items
        ),
        "P0 entries require an executable lead innovation",
    )

    print("company innovation expansion: PASS")
    print("tracks=166 hypotheses=112 existing_enrich=22 net_new=90 p0=25")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
