"""Build the Crystallization Mandate work queue from a verified estate census.

Every repository is routed exactly once. Nothing is exempt merely because it is
important, governed, archived, or inconvenient. Archived/forked repositories
receive verification lanes rather than disappearing from the work estate.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

KNOWN_CLASSIFICATIONS = {
    "PRIORITY_SPINE",
    "RECRUITER_PORTFOLIO",
    "ARCHIVE_BACKUP_OR_FORK",
    "UPSTREAM_OR_FORK_REVIEW",
    "PRIVATE_REVIEW_REQUIRED",
    "CANDIDATE_EXPANSION",
    "UNGOVERNED_PUBLIC_INVENTORY",
}


class QueueError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route every owned repository into one Crystallization Mandate lane"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _require(payload: dict[str, Any], key: str, expected: type) -> Any:
    value = payload.get(key)
    if not isinstance(value, expected):
        raise QueueError(f"Census field {key!r} must be {expected.__name__}")
    return value


def load_receipt(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QueueError(f"Unable to load census receipt {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise QueueError("Census receipt must be a JSON object")
    if payload.get("schema") != "glaciereq.owned-library-census-receipt.v1":
        raise QueueError("Unsupported owned-library census schema")
    return payload


def validate_receipt(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_records = _require(payload, "repositories", list)
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise QueueError("Every census repository entry must be an object")
        repository = _require(raw, "repository", str)
        _require(raw, "classification", str)
        visibility = _require(raw, "visibility", str)
        _require(raw, "fork", bool)
        _require(raw, "archived", bool)
        position = _require(raw, "position", int)
        if visibility not in {"public", "private", "internal"}:
            raise QueueError(f"Invalid visibility for {repository}: {visibility}")
        if position < 0:
            raise QueueError(f"Invalid position for {repository}: {position}")
        if repository in seen:
            raise QueueError(f"Duplicate census repository: {repository}")
        seen.add(repository)
        records.append(raw)

    total = len(records)
    native = sum(not record["fork"] for record in records)
    forks = sum(record["fork"] for record in records)
    for key, observed in {
        "repository_count": total,
        "native_repository_count": native,
        "fork_repository_count": forks,
    }.items():
        recorded = _require(payload, key, int)
        if recorded != observed:
            raise QueueError(f"Census cardinality mismatch for {key}: {recorded} != {observed}")
    return records


def route_record(record: dict[str, Any]) -> dict[str, Any]:
    repository = record["repository"]
    classification = record["classification"]
    visibility = record["visibility"]
    fork = record["fork"]
    archived = record["archived"]

    if classification not in KNOWN_CLASSIFICATIONS:
        lane = "CRYSTALLIZE_MANUAL_TRIAGE"
        priority = 0
        reason = "Unknown classification cannot escape semantic reconstruction."
    elif archived or classification == "ARCHIVE_BACKUP_OR_FORK":
        lane = "VERIFY_ARCHIVE_OR_SUCCESSOR"
        priority = 8
        reason = (
            "Archive/backup status is not an exemption; verify intentional archive reason "
            "or canonical successor before resolving it from the active estate."
        )
    elif fork:
        lane = "VERIFY_FORK_DELTA_OR_UPSTREAM"
        priority = 12
        reason = (
            "Fork must be inspected for unique local capability, intentional reference value, "
            "or safe canonicalization to upstream."
        )
    elif classification == "PRIORITY_SPINE":
        lane = "CRYSTALLIZE_PRIORITY"
        priority = 1
        reason = "Priority systems are first in line for full purpose realization, not exempt."
    elif classification == "RECRUITER_PORTFOLIO":
        lane = "CRYSTALLIZE_RECRUITER"
        priority = 2
        reason = "Recruiter-facing systems must prove real capability before presentation."
    elif classification == "CANDIDATE_EXPANSION":
        lane = "CRYSTALLIZE_CANDIDATE"
        priority = 10
        reason = "Candidate repository requires full intention and capability reconstruction."
    elif visibility == "public":
        lane = "CRYSTALLIZE_NATIVE_PUBLIC"
        priority = 20
        reason = "Public native repository requires source-level purpose and capability completion."
    elif visibility in {"private", "internal"}:
        lane = "CRYSTALLIZE_NATIVE_PRIVATE"
        priority = 30
        reason = "Private native repository requires internal source-level metamorphosis."
    else:
        lane = "CRYSTALLIZE_MANUAL_TRIAGE"
        priority = 0
        reason = "Repository metadata did not match a deterministic lane."

    return {
        "position": record["position"],
        "repository": repository,
        "classification": classification,
        "visibility": visibility,
        "archived": archived,
        "fork": fork,
        "lane": lane,
        "priority": priority,
        "actionable": True,
        "reason": reason,
        "required_exit": (
            "CRYSTALLIZED_OR_VERIFIED_ARCHIVE_OR_VERIFIED_SUCCESSOR"
            if archived or fork
            else "CRYSTALLIZED"
        ),
    }


def build_queue(payload: dict[str, Any]) -> dict[str, Any]:
    records = validate_receipt(payload)
    routed = [route_record(record) for record in records]
    routed.sort(
        key=lambda item: (
            item["priority"],
            item["position"],
            item["repository"].casefold(),
        )
    )

    native_work = [item for item in routed if not item["fork"]]
    fork_work = [item for item in routed if item["fork"]]
    lane_counts = Counter(item["lane"] for item in routed)

    covered = {item["repository"] for item in routed}
    if len(covered) != len(records):
        raise QueueError("Estate routing failed to cover each repository exactly once")
    if any(not item["actionable"] for item in routed):
        raise QueueError("Crystallization queue contains a non-actionable repository exemption")

    return {
        "schema": "glaciereq.crystallization-work-queue.v1",
        "mandate": "CRYSTALLIZATION-MANDATE",
        "owner": payload.get("owner"),
        "state": "EVERY_REPOSITORY_ACTIONABLE",
        "source_schema": payload["schema"],
        "source_repository_count": payload["repository_count"],
        "source_native_repository_count": payload["native_repository_count"],
        "source_fork_repository_count": payload["fork_repository_count"],
        "coverage_count": len(routed),
        "actionable_count": len(routed),
        "unrouted_count": len(records) - len(routed),
        "exempt_count": 0,
        "lane_counts": dict(sorted(lane_counts.items())),
        "native_work_count": len(native_work),
        "fork_reference_work_count": len(fork_work),
        "work_queue": routed,
        "native_work_queue": native_work,
        "fork_reference_queue": fork_work,
        "acceptance": {
            "unknown_allowed": 0,
            "broken_allowed": 0,
            "materially_incomplete_allowed": 0,
            "representative_sampling_allowed": False,
        },
    }


def main() -> int:
    args = parse_args()
    try:
        result = build_queue(load_receipt(args.input.resolve()))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        args.output.write_text(rendered, encoding="utf-8")
    except QueueError as exc:
        print(f"Crystallization work queue failed closed: {exc}")
        return 1
    print(
        "Crystallization work queue VERIFIED: "
        f"coverage={result['coverage_count']} actionable={result['actionable_count']} "
        f"exempt={result['exempt_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
