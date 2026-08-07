"""Build a coverage-complete work queue from an owned-library census receipt."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


class QueueError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route every owned repository into one deterministic estate lane"
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
        fork = _require(raw, "fork", bool)
        archived = _require(raw, "archived", bool)
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
    expected = {
        "repository_count": total,
        "native_repository_count": native,
        "fork_repository_count": forks,
    }
    for key, observed in expected.items():
        recorded = _require(payload, key, int)
        if recorded != observed:
            raise QueueError(
                f"Census cardinality mismatch for {key}: {recorded} != {observed}"
            )
    return records


def route_record(record: dict[str, Any]) -> dict[str, Any]:
    repository = record["repository"]
    classification = record["classification"]
    visibility = record["visibility"]
    fork = record["fork"]
    archived = record["archived"]

    if archived or classification == "ARCHIVE_BACKUP_OR_FORK":
        lane = "PRESERVE_ARCHIVE_BACKUP"
        priority = 90
        actionable = False
        reason = "Archived or backup-classified holdings stay preserved by default."
    elif fork:
        lane = "FORK_REFERENCE_REVIEW"
        priority = 60
        actionable = True
        reason = "Forks are reviewed separately for upstream value or verified local delta."
    elif classification == "PRIORITY_SPINE":
        lane = "PRESERVE_GOVERNED_PRIORITY"
        priority = 100
        actionable = False
        reason = "Priority-spine repositories already have an explicit governance lane."
    elif classification == "RECRUITER_PORTFOLIO":
        lane = "PRESERVE_GOVERNED_RECRUITER"
        priority = 100
        actionable = False
        reason = "Recruiter-portfolio repositories remain governed by their existing gates."
    elif classification == "CANDIDATE_EXPANSION":
        lane = "NATIVE_CANDIDATE_AUDIT"
        priority = 10
        actionable = True
        reason = "Explicit candidate expansion should receive repository-native audit first."
    elif visibility == "public":
        lane = "NATIVE_PUBLIC_AUDIT"
        priority = 20
        actionable = True
        reason = "Ungoverned public native repository requires provenance and value review."
    elif visibility in {"private", "internal"}:
        lane = "NATIVE_PRIVATE_AUDIT"
        priority = 30
        actionable = True
        reason = "Ungoverned private native repository requires internal-only review."
    else:
        lane = "MANUAL_TRIAGE"
        priority = 0
        actionable = True
        reason = "Repository metadata did not match a known deterministic routing rule."

    return {
        "position": record["position"],
        "repository": repository,
        "classification": classification,
        "visibility": visibility,
        "archived": archived,
        "fork": fork,
        "lane": lane,
        "priority": priority,
        "actionable": actionable,
        "reason": reason,
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

    native_work = [
        item for item in routed if item["actionable"] and not item["fork"]
    ]
    fork_work = [item for item in routed if item["actionable"] and item["fork"]]
    preserve = [item for item in routed if not item["actionable"]]
    lane_counts = Counter(item["lane"] for item in routed)

    covered = {item["repository"] for item in routed}
    if len(covered) != len(records):
        raise QueueError("Estate routing failed to cover each repository exactly once")

    return {
        "schema": "glaciereq.estate-work-queue.v1",
        "owner": payload.get("owner"),
        "state": "ROUTED_FROM_VERIFIED_INVENTORY",
        "source_schema": payload["schema"],
        "source_repository_count": payload["repository_count"],
        "source_native_repository_count": payload["native_repository_count"],
        "source_fork_repository_count": payload["fork_repository_count"],
        "coverage_count": len(routed),
        "lane_counts": dict(sorted(lane_counts.items())),
        "native_work_count": len(native_work),
        "fork_reference_work_count": len(fork_work),
        "preserve_count": len(preserve),
        "native_work_queue": native_work,
        "fork_reference_queue": fork_work,
        "preserve_queue": preserve,
        "routing_nonclaims": [
            "Routing is not a claim of authorship, originality, quality, or maturity.",
            "Repository names are not used to infer technical provenance or subject matter.",
            "A work-queue lane does not promote a repository into recruiter evidence.",
        ],
    }


def main() -> int:
    args = parse_args()
    try:
        result = build_queue(load_receipt(args.input.resolve()))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except QueueError as exc:
        print(f"Estate work queue failed closed: {exc}")
        return 1
    print(
        "Estate work queue VERIFIED: "
        f"coverage={result['coverage_count']} "
        f"native_work={result['native_work_count']} "
        f"fork_work={result['fork_reference_work_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
