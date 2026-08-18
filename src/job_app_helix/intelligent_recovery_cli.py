"""CLI for the intelligent multi-engine restoration planner and executor."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .intelligent_recovery import (
    build_intelligent_recovery_plan,
    execute_automatic_recovery,
    summarize_recovery_plan,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-recover",
        description=(
            "Analyze multiple exact donor revisions, rank displaced capability, "
            "route risky changes to surgical review, and optionally restore only "
            "high-confidence target-absent source/test artifacts."
        ),
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("plan", "apply"):
        command = sub.add_parser(name)
        command.add_argument("--donor", action="append", required=True)
        command.add_argument("--target", default="HEAD")
        command.add_argument("--path", action="append", default=[])
        command.add_argument("--max-auto-actions", type=int, default=8)
        command.add_argument("--output", type=Path)
        if name == "plan":
            command.add_argument("--summary", action="store_true")
        else:
            command.add_argument(
                "--select",
                action="append",
                default=[],
                help="candidate id to apply; omit to execute the bounded automatic batch",
            )
    return parser


def _write(payload: dict[str, object], output: Path | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(rendered, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    plan = build_intelligent_recovery_plan(
        args.repo,
        donor_refs=tuple(args.donor),
        target_ref=args.target,
        include_paths=tuple(args.path),
        max_auto_actions=args.max_auto_actions,
    )
    if args.command == "plan":
        payload = summarize_recovery_plan(plan) if args.summary else plan.to_dict()
        _write(payload, args.output)
        return 0

    selected = tuple(args.select) if args.select else None
    receipt = execute_automatic_recovery(args.repo, plan, selected_ids=selected)
    _write(receipt.to_dict(), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
