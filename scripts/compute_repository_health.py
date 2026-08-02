#!/usr/bin/env python3
"""Compute one SHA-bound repository-health assessment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from job_app_helix.repository_health import (  # noqa: E402
    RepositoryHealthError,
    assess_repository_health,
    load_policy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute a fail-closed repository-health assessment."
    )
    parser.add_argument("input", type=Path, help="Repository evidence JSON input")
    parser.add_argument(
        "--policy",
        type=Path,
        help="Optional repository-health policy JSON; defaults to the installed policy",
    )
    parser.add_argument("--output", type=Path, help="Optional assessment output path")
    parser.add_argument(
        "--require-elite",
        action="store_true",
        help="Return a nonzero exit code unless the assessment is ELITE_VERIFIED",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        policy = load_policy(args.policy)
        assessment = assess_repository_health(payload, policy)
    except (OSError, json.JSONDecodeError, RepositoryHealthError) as exc:
        print(json.dumps({"state": "FAILED", "error": str(exc)}), file=sys.stderr)
        return 2

    rendered = json.dumps(assessment, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    if args.require_elite and assessment["health_state"] != "ELITE_VERIFIED":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
