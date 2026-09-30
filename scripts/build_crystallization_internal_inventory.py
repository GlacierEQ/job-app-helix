#!/usr/bin/env python3
"""Build a complete path-classified internal inventory from a crystallization receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from job_app_helix.internal_discovery import build_estate_internal_inventory


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify every accounted repository path into groups and semantic discovery roles"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("crawl receipt must be an object")
        inventory = build_estate_internal_inventory(receipt)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(inventory, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}))
        return 2

    harnesses = sum(
        int(repo.get("harness_count", 0))
        for repo in inventory["repositories"]
    )
    unusual = sum(
        int(repo.get("unusual_high_value_count", 0))
        for repo in inventory["repositories"]
    )
    classified = sum(
        int(repo.get("classified_path_count", 0))
        for repo in inventory["repositories"]
    )
    print(
        "Crystallization internal discovery: "
        f"repositories={inventory['repository_inventory_count']} "
        f"paths={classified} harnesses={harnesses} unusual_high_value={unusual} "
        f"complete={inventory['structural_discovery_complete_for_selected_repositories']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
