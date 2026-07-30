from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from .portfolio_contract import validate_program
from .portfolio_discovery import build_plan
from .portfolio_execution import (
    atomic_write_json,
    execute_plan,
    plan_payload,
    receipt_payload,
    render_plan_markdown,
    render_program_markdown,
)
from .portfolio_models import PortfolioProgramError, VerificationState

DEFAULT_INVENTORY = Path("manifests/portfolio_repositories.json")
DEFAULT_ROLLOUT = Path("manifests/portfolio_rollout.json")


def _add_contract_paths(parser: argparse.ArgumentParser) -> None:
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
        help="Portfolio rollout program manifest.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-portfolio",
        description=(
            "Validate, discover, and execute evidence-bound verification waves "
            "across the exact GlacierEQ job-application portfolio."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate that rollout waves partition the exact portfolio inventory.",
    )
    _add_contract_paths(validate_parser)

    render_parser = subparsers.add_parser(
        "render-program",
        help="Render the high-level rollout program as Markdown.",
    )
    _add_contract_paths(render_parser)
    render_parser.add_argument("--output", type=Path)

    plan_parser = subparsers.add_parser(
        "plan",
        help="Discover repository stacks and emit deterministic low-level proof commands.",
    )
    _add_contract_paths(plan_parser)
    plan_parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Directory containing the 65 child repositories.",
    )
    plan_parser.add_argument(
        "--wave",
        action="append",
        dest="waves",
        help="Limit discovery to one or more rollout wave IDs.",
    )
    plan_parser.add_argument("--json-output", type=Path)
    plan_parser.add_argument("--markdown-output", type=Path)
    plan_parser.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="Return a nonzero status when the generated plan contains blockers.",
    )

    execute_parser = subparsers.add_parser(
        "execute",
        help="Execute discovered commands without shell interpolation and write a receipt.",
    )
    _add_contract_paths(execute_parser)
    execute_parser.add_argument("--workspace", type=Path, required=True)
    execute_parser.add_argument("--wave", action="append", dest="waves")
    execute_parser.add_argument(
        "--receipt",
        type=Path,
        default=Path("artifacts/portfolio_execution_receipt.json"),
    )
    execute_parser.add_argument(
        "--allow-mutating",
        action="store_true",
        help="Explicitly authorize build commands that write workspace artifacts.",
    )

    return parser


def _write_text(path: Path | None, text: str) -> None:
    if path is None:
        print(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(path)


def _validate(args: argparse.Namespace) -> int:
    program = validate_program(
        inventory_path=args.inventory,
        rollout_path=args.rollout,
    )
    print(
        json.dumps(
            {
                "schema": program.schema,
                "portfolio_root": program.portfolio_root,
                "waves": len(program.waves),
                "repositories": len(program.repositories),
                "status": "VALID",
            },
            indent=2,
        )
    )
    return 0


def _render_program(args: argparse.Namespace) -> int:
    program = validate_program(
        inventory_path=args.inventory,
        rollout_path=args.rollout,
    )
    _write_text(args.output, render_program_markdown(program))
    return 0


def _plan(args: argparse.Namespace) -> int:
    plans = build_plan(
        workspace=args.workspace,
        inventory_path=args.inventory,
        rollout_path=args.rollout,
        wave_ids=set(args.waves) if args.waves else None,
    )
    payload = plan_payload(plans)

    if args.json_output:
        atomic_write_json(args.json_output, payload)
        print(args.json_output)
    else:
        print(json.dumps(payload, indent=2))

    if args.markdown_output:
        _write_text(args.markdown_output, render_plan_markdown(plans))

    blockers = sum(bool(plan.blockers) for plan in plans)
    print(
        f"planned={len(plans)} blockers={blockers} "
        f"waves={','.join(payload['summary']['waves'])}",
        file=sys.stderr,
    )
    return 1 if args.fail_on_blockers and blockers else 0


def _execute(args: argparse.Namespace) -> int:
    started_at_epoch_ms = int(time.time() * 1000)
    running = {
        "schema": "glaciereq.portfolio.execution-receipt.v1",
        "started_at_epoch_ms": started_at_epoch_ms,
        "conclusion": "RUNNING",
        "repositories": [],
    }
    atomic_write_json(args.receipt, running)

    try:
        plans = build_plan(
            workspace=args.workspace,
            inventory_path=args.inventory,
            rollout_path=args.rollout,
            wave_ids=set(args.waves) if args.waves else None,
        )
        receipts = execute_plan(plans, allow_mutating=args.allow_mutating)
        payload = receipt_payload(
            receipts,
            started_at_epoch_ms=started_at_epoch_ms,
        )
    except Exception as exc:
        failed = {
            **running,
            "completed_at_epoch_ms": int(time.time() * 1000),
            "conclusion": VerificationState.FAILED.value,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
        atomic_write_json(args.receipt, failed)
        raise

    atomic_write_json(args.receipt, payload)
    print(args.receipt)
    return 0 if payload["conclusion"] == VerificationState.VERIFIED.value else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args)
        if args.command == "render-program":
            return _render_program(args)
        if args.command == "plan":
            return _plan(args)
        if args.command == "execute":
            return _execute(args)
    except (OSError, json.JSONDecodeError, PortfolioProgramError) as exc:
        print(f"portfolio program error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
