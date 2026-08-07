from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from .branch_steward import BranchStewardError, assess_repository, write_receipt
from .library_program import (
    LibraryProgramError,
    render_library_program,
    validate_latest_execution_receipt,
    validate_library_program,
)

DEFAULT_PROGRAM = Path("manifests/library_priority_spine.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-library",
        description="Validate, render, and execute GlacierEQ library stewardship policy.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--program", type=Path, default=DEFAULT_PROGRAM)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--program", type=Path, default=DEFAULT_PROGRAM)
    render_parser.add_argument("--output", type=Path)

    branch_parser = subparsers.add_parser(
        "branches",
        help="Analyze remote branches by ancestry and patch-equivalent unique value.",
    )
    branch_parser.add_argument("repository", type=Path)
    branch_parser.add_argument("--canonical", default="main")
    branch_parser.add_argument("--remote", default="origin")
    branch_parser.add_argument("--fetch", action="store_true")
    branch_parser.add_argument("--receipt", type=Path)
    return parser


def _branch_command(args: argparse.Namespace) -> int:
    repository = args.repository.resolve()
    if args.fetch:
        completed = subprocess.run(
            ["git", "fetch", "--all", "--prune"],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise BranchStewardError(
                f"git fetch failed ({completed.returncode}): {completed.stderr.strip()}"
            )

    payload = assess_repository(repository, canonical=args.canonical, remote=args.remote)
    payload["timestamp"] = datetime.now(UTC).isoformat()
    payload["policy"] = {
        "never_merge_stale_tip_directly": True,
        "preserve_unique_value_before_retirement": True,
        "patch_equivalence_checked": True,
        "remote_ref_deletion_requires_separate_receipt": True,
    }
    if args.receipt:
        write_receipt(payload, args.receipt)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "branches":
            return _branch_command(args)

        payload = validate_library_program(args.program)
        if args.command == "validate":
            receipt = validate_latest_execution_receipt(args.program, payload)
            print(
                json.dumps(
                    {
                        "schema": payload["schema"],
                        "repositories": len(payload["repositories"]),
                        "canonical_control_plane": payload["canonical_control_plane"],
                        "latest_execution_receipt": payload["latest_execution_receipt"],
                        "receipt_program": receipt["program"],
                        "status": "VALID",
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "render":
            rendered = render_library_program(payload)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(rendered, encoding="utf-8")
                print(args.output)
            else:
                print(rendered, end="")
            return 0
    except (OSError, json.JSONDecodeError, LibraryProgramError, BranchStewardError) as exc:
        print(f"library program error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
