#!/usr/bin/env python3
"""Turn a raw crystallization crawl receipt into a compact code-uplift routing digest.

The crawler is an observation engine. This module keeps that strength and changes
what gets promoted into Monolith: compact, evidence-bounded lift signals instead
of the entire per-file crawl body.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "glaciereq.crystallization-source-crawl.v1"
OUTPUT_SCHEMA = "glaciereq.crystallization-uplift-digest.v1"


class DigestError(RuntimeError):
    pass


def _as_int(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _signals(repo: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    if repo.get("scaffold_findings"):
        signals.append("SCAFFOLD_MARKERS")
    if repo.get("incomplete_findings"):
        signals.append("INCOMPLETE_MARKERS")
    if _as_int(repo.get("unresolved_content_count")):
        signals.append("UNRESOLVED_CONTENT")
    if _as_int(repo.get("text_fetch_failure_count")):
        signals.append("TEXT_FETCH_FAILURE")
    if repo.get("status") == "INCOMPLETE":
        signals.append("SOURCE_INSPECTION_INCOMPLETE")
    if repo.get("fork"):
        signals.append("FORK_LINEAGE_REVIEW")
    if repo.get("archived"):
        signals.append("ARCHIVE_SUCCESSOR_REVIEW")
    return signals


def _lane(repo: dict[str, Any], signals: list[str]) -> str:
    if repo.get("archived"):
        return "VERIFY_ARCHIVE_OR_SUCCESSOR"
    if repo.get("fork"):
        return "VERIFY_FORK_DELTA_OR_UPSTREAM"
    if "SCAFFOLD_MARKERS" in signals or "INCOMPLETE_MARKERS" in signals:
        return "LIFT_IMPLEMENTATION_GAPS"
    if "UNRESOLVED_CONTENT" in signals or "TEXT_FETCH_FAILURE" in signals:
        return "RESOLVE_SOURCE_UNCERTAINTY"
    surfaces = repo.get("surface_counts") if isinstance(repo.get("surface_counts"), dict) else {}
    if _as_int(surfaces.get("execution")) or _as_int(surfaces.get("deployment")):
        return "VERIFY_RUNTIME_AND_LIFT"
    return "VERIFY_PURPOSE_AND_COMPOSITION"


def _score(repo: dict[str, Any], signals: list[str]) -> int:
    score = 0
    if "SCAFFOLD_MARKERS" in signals:
        score += 50
    if "INCOMPLETE_MARKERS" in signals:
        score += 45
    if "SOURCE_INSPECTION_INCOMPLETE" in signals:
        score += 30
    score += min(25, _as_int(repo.get("unresolved_content_count")) * 2)
    score += min(15, _as_int(repo.get("text_fetch_failure_count")) * 5)
    surfaces = repo.get("surface_counts") if isinstance(repo.get("surface_counts"), dict) else {}
    if _as_int(surfaces.get("execution")):
        score += 12
    if _as_int(surfaces.get("deployment")):
        score += 12
    if _as_int(surfaces.get("test")):
        score += 6
    if _as_int(surfaces.get("workflow")):
        score += 4
    if repo.get("fork"):
        score = max(1, score - 15)
    if repo.get("archived"):
        score = max(1, score - 20)
    return score


def _compact_repository(repo: dict[str, Any]) -> dict[str, Any]:
    name = repo.get("repository")
    if not isinstance(name, str) or "/" not in name:
        raise DigestError("repository entry missing owner/name identity")
    signals = _signals(repo)
    surfaces = repo.get("surface_counts") if isinstance(repo.get("surface_counts"), dict) else {}
    lane = _lane(repo, signals)
    actions = {
        "LIFT_IMPLEMENTATION_GAPS": "Inspect repository-native intent and implementation paths; repair material partial/broken/missing capability while preserving working code.",
        "RESOLVE_SOURCE_UNCERTAINTY": "Resolve unread/oversized/failed source evidence before capability promotion; do not infer completion from partial coverage.",
        "VERIFY_RUNTIME_AND_LIFT": "Exercise repository-native test/build/runtime/deployment surfaces, then lift verified gaps rather than adding governance-only work.",
        "VERIFY_PURPOSE_AND_COMPOSITION": "Resolve purpose, lineage, consumers, and Monolith composition before deciding whether code changes are warranted.",
        "VERIFY_ARCHIVE_OR_SUCCESSOR": "Verify intentional archive reason or canonical successor; preserve unique capability and lineage.",
        "VERIFY_FORK_DELTA_OR_UPSTREAM": "Compare fork with upstream; preserve unique local capability or bind cleanly to upstream without duplication.",
    }
    return {
        "repository": name,
        "position": _as_int(repo.get("position")),
        "source_status": str(repo.get("status") or "UNKNOWN"),
        "lift_priority_score": _score(repo, signals),
        "lane": lane,
        "signals": signals,
        "metrics": {
            "file_count": _as_int(repo.get("file_count")),
            "text_inspected_count": _as_int(repo.get("text_inspected_count")),
            "unresolved_content_count": _as_int(repo.get("unresolved_content_count")),
            "function_definition_count": _as_int(repo.get("function_definition_count")),
            "surface_counts": {str(k): _as_int(v) for k, v in sorted(surfaces.items())},
            "scaffold_finding_count": len(repo.get("scaffold_findings") or []),
            "incomplete_finding_count": len(repo.get("incomplete_findings") or []),
        },
        "next_action": actions[lane],
    }


def build_digest(receipt: dict[str, Any]) -> dict[str, Any]:
    if receipt.get("schema") != SOURCE_SCHEMA:
        raise DigestError(f"unsupported crawl schema: {receipt.get('schema')!r}")
    repositories = receipt.get("repositories")
    if not isinstance(repositories, list):
        raise DigestError("crawl receipt repositories must be a list")
    compact = [_compact_repository(repo) for repo in repositories if isinstance(repo, dict)]
    compact.sort(
        key=lambda item: (
            -int(item["lift_priority_score"]),
            int(item["position"]),
            str(item["repository"]).casefold(),
        )
    )
    source_digest = receipt.get("receipt_digest")
    if not isinstance(source_digest, str) or not source_digest:
        raw = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        source_digest = hashlib.sha256(raw).hexdigest()
    return {
        "schema": OUTPUT_SCHEMA,
        "mandate": "CRYSTALLIZATION-MANDATE",
        "mode": "CODE_UPLIFT_ROUTING",
        "principle": "Preserve the crawler's exhaustive observation power; promote compact verified lift signals, not raw per-file crawl bodies, into the integration fabric.",
        "source_receipt_digest": source_digest,
        "content_mode": receipt.get("content_mode"),
        "accessible_repository_count": _as_int(receipt.get("accessible_repository_count")),
        "selected_repository_count": _as_int(receipt.get("selected_repository_count")),
        "repository_crawled_count": _as_int(receipt.get("repository_crawled_count")),
        "repository_failure_count": _as_int(receipt.get("repository_failure_count")),
        "selection_start": receipt.get("selection_start"),
        "selection_limit": receipt.get("selection_limit"),
        "hourly_shard_index": receipt.get("hourly_shard_index"),
        "raw_receipt_policy": {
            "promotion_to_monolith_main": False,
            "preserve_as_private_workflow_artifact": True,
            "reason": "Raw per-file evidence is high-volume source telemetry; Monolith main should receive reusable routing intelligence rather than hourly bulk snapshots.",
        },
        "queue": compact,
        "queue_count": len(compact),
        "top_lift_targets": compact[:10],
        "proof_boundary": {
            "source_observation_is_not_runtime_proof": True,
            "lift_priority_is_routing_not_factual_authority": True,
            "repository_native_source_remains_implementation_authority": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise DigestError("crawl receipt must be an object")
        digest = build_digest(receipt)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(digest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, DigestError) as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}))
        return 2
    print(
        f"Crystallization uplift digest: queue={digest['queue_count']} "
        f"source={digest['source_receipt_digest'][:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
