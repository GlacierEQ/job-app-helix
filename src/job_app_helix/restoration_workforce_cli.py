"""Executable surface for Megamind + Make-It-Heavy restoration intelligence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .restoration_workforce_intelligence import compile_staffed_restoration_decision


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-prioritize",
        description=(
            "Rank JOB_RESTORE candidates with Megamind v2 and compose an "
            "evidence-aware Make-It-Heavy worker portfolio."
        ),
    )
    parser.add_argument("input", type=Path, help="JSON restoration queue and worker evidence")
    parser.add_argument("--output", type=Path, help="Optional deterministic decision receipt")
    args = parser.parse_args(argv)

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("restoration intelligence input must be a JSON object")
    result = compile_staffed_restoration_decision(payload)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
