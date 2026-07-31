from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

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
        description="Validate and render the GlacierEQ library README and branch program.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--program", type=Path, default=DEFAULT_PROGRAM)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--program", type=Path, default=DEFAULT_PROGRAM)
    render_parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
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
    except (OSError, json.JSONDecodeError, LibraryProgramError) as exc:
        print(f"library program error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
