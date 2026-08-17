from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .portfolio_models import PortfolioProgramError
from .portfolio_productization import compile_productization_targets, productization_payload

DEFAULT_INVENTORY = Path("manifests/portfolio_repositories.json")
DEFAULT_ROLLOUT = Path("manifests/portfolio_rollout.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-productize",
        description=(
            "Compile the GlacierEQ job-engineering estate into concrete productization "
            "targets based on each repository's executable stack and delivery surface."
        ),
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Directory containing the job-engineering repository checkouts.",
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=DEFAULT_INVENTORY,
        help="Exact portfolio inventory manifest.",
    )
    parser.add_argument(
        "--rollout",
        type=Path,
        default=DEFAULT_ROLLOUT,
        help="Historical/current rollout manifest compiled through the APEX adapter.",
    )
    parser.add_argument(
        "--wave",
        action="append",
        dest="waves",
        help="Limit compilation to one or more rollout wave IDs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the productization manifest atomically to this path.",
    )
    parser.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="Exit nonzero when one or more repositories have execution blockers.",
    )
    return parser


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    try:
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        targets = compile_productization_targets(
            workspace=args.workspace,
            inventory_path=args.inventory,
            rollout_path=args.rollout,
            wave_ids=set(args.waves) if args.waves else None,
        )
        payload = productization_payload(targets)
    except (OSError, json.JSONDecodeError, PortfolioProgramError) as exc:
        print(f"productization program error: {exc}", file=sys.stderr)
        return 2

    if args.output:
        _write_json(args.output, payload)
        print(args.output)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))

    blockers = int(payload["summary"]["blocked"])
    print(
        f"productized={payload['summary']['repositories']} blockers={blockers}",
        file=sys.stderr,
    )
    return 1 if args.fail_on_blockers and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
