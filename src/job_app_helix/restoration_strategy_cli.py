"""CLI for deterministic restoration priority routing."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .restoration_strategy_router import compile_restoration_decision


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-route-restoration",
        description=(
            "Rank executable JOB_RESTORE candidates using the Megamind tournament contract."
        ),
    )
    parser.add_argument("input", type=Path, help="JSON payload with a candidates array")
    parser.add_argument("--output", type=Path, help="Optional decision receipt path")
    args = parser.parse_args(argv)

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("restoration routing input must be a JSON object")
    result = compile_restoration_decision(payload)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
