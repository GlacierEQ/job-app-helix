#!/usr/bin/env python3
"""Crawl an authenticated GitHub estate with explicit coverage receipts."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from job_app_helix.crystallization_crawler import (
    CrawlError,
    GitHubApi,
    crawl_estate,
    list_accessible_repositories,
)


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build completeness-accounted source evidence for every accessible GitHub repository"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GLACIEREQ_ESTATE_TOKEN") or os.environ.get("GITHUB_TOKEN", ""),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--content-mode", choices=("tree-only", "priority", "all-text"), default="tree-only")
    parser.add_argument("--max-text-bytes", type=int, default=1_000_000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--start", type=int, default=0, help="zero-based repository position after sorted accessible census")
    parser.add_argument("--limit", type=int, help="maximum repositories in this shard")
    parser.add_argument("--repository", action="append", default=[], help="exact owner/name; repeatable")
    parser.add_argument("--require-semantic-complete", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.start < 0:
            raise CrawlError("--start must be non-negative")
        if args.limit is not None and args.limit <= 0:
            raise CrawlError("--limit must be positive")

        api = GitHubApi(args.token)
        all_repositories = list_accessible_repositories(api)
        selected = all_repositories
        if args.repository:
            requested = set(args.repository)
            selected = [repo for repo in all_repositories if repo.repository in requested]
            missing = sorted(requested - {repo.repository for repo in selected})
            if missing:
                raise CrawlError(f"requested repositories are not accessible: {missing}")
        else:
            stop = None if args.limit is None else args.start + args.limit
            selected = all_repositories[args.start:stop]

        receipt = crawl_estate(
            api,
            selected,
            content_mode=args.content_mode,
            max_text_bytes=args.max_text_bytes,
            workers=args.workers,
        )
        receipt["accessible_repository_count"] = len(all_repositories)
        receipt["selected_repository_count"] = len(selected)
        receipt["selection_start"] = args.start if not args.repository else None
        receipt["selection_limit"] = args.limit if not args.repository else None
        receipt["explicit_repositories"] = sorted(args.repository)
        receipt["full_estate_selection"] = (
            not args.repository and args.start == 0 and args.limit is None
        )
        receipt["estate_exit_eligible"] = bool(
            receipt["full_estate_selection"]
            and receipt["semantic_text_inspection_complete"]
            and receipt["repository_failure_count"] == 0
            and receipt["repository_crawled_count"] == len(all_repositories)
        )
        _atomic_write(args.output.resolve(), receipt)
    except (CrawlError, OSError) as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, indent=2))
        return 2

    print(
        "Crystallization crawl receipt: "
        f"accessible={receipt['accessible_repository_count']} "
        f"selected={receipt['selected_repository_count']} "
        f"crawled={receipt['repository_crawled_count']} "
        f"files={receipt['file_accounted_count']} "
        f"unresolved={receipt['unresolved_content_count']} "
        f"failures={receipt['repository_failure_count']} "
        f"estate_exit_eligible={receipt['estate_exit_eligible']}"
    )
    if receipt["repository_failure_count"] or not receipt["all_repository_trees_complete"]:
        return 3
    if args.require_semantic_complete and not receipt["semantic_text_inspection_complete"]:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
