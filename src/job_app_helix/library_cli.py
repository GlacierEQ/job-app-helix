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
from .repository_surface import (
    RepositorySurfaceError,
    compile_governed_surface_report,
    compile_surface_report,
)
from .surface_reconciliation import apply_surface_reconciliation

_PACKAGE_DIR = Path(__file__).resolve().parent
_SOURCE_ROOT = Path(__file__).resolve().parents[2]


def _default_manifest(filename: str) -> Path:
    """Resolve canonical data from a source checkout or the installed wheel."""

    source_path = _SOURCE_ROOT / "manifests" / filename
    if source_path.is_file():
        return source_path
    return _PACKAGE_DIR / "_library_manifests" / filename


DEFAULT_PROGRAM = _default_manifest("library_priority_spine.json")
DEFAULT_SURFACE_OBSERVATIONS = _default_manifest(
    "public_repository_surface_observations_2026-08-08.json"
)
DEFAULT_SURFACE_DECISIONS = _default_manifest(
    "public_repository_surface_decisions_2026-08-08.json"
)
DEFAULT_SURFACE_RECONCILIATIONS = (
    _default_manifest("public_repository_surface_reconciliation_2026-08-09.json"),
    _default_manifest("public_repository_surface_reconciliation_wave3_2026-08-09.json"),
    _default_manifest("public_repository_surface_reconciliation_wave4_2026-08-09.json"),
    _default_manifest("public_repository_surface_reconciliation_wave5_2026-08-09.json"),
    _default_manifest("public_repository_surface_reconciliation_wave6_2026-08-09.json"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-library",
        description="Validate, render, audit, and execute GlacierEQ library stewardship policy.",
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

    surface_parser = subparsers.add_parser(
        "surface-audit",
        help=(
            "Compile fail-closed public repository-surface admission from historical "
            "observations, governed decisions, and ordered current reconciliation."
        ),
    )
    surface_parser.add_argument(
        "--observations", type=Path, default=DEFAULT_SURFACE_OBSERVATIONS
    )
    surface_parser.add_argument(
        "--decisions", type=Path, default=DEFAULT_SURFACE_DECISIONS
    )
    surface_parser.add_argument(
        "--reconciliation",
        action="append",
        type=Path,
        help=(
            "Ordered reconciliation layer; repeat to override the default ordered layers."
        ),
    )
    history_group = surface_parser.add_mutually_exclusive_group()
    history_group.add_argument(
        "--historical-only",
        action="store_true",
        help="Reproduce the original observation report without later decisions.",
    )
    history_group.add_argument(
        "--decision-only",
        action="store_true",
        help="Reproduce the original governed-decision snapshot without reconciliation.",
    )
    surface_parser.add_argument("--expected-public-count", type=int, default=75)
    surface_parser.add_argument("--output", type=Path)
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


def _same_path(left: Path, right: Path) -> bool:
    return left.expanduser().resolve() == right.expanduser().resolve()


def _resolve_reconciliation_paths(args: argparse.Namespace) -> tuple[Path, ...]:
    if args.reconciliation:
        return tuple(args.reconciliation)
    custom_sources = not _same_path(
        args.observations, DEFAULT_SURFACE_OBSERVATIONS
    ) or not _same_path(args.decisions, DEFAULT_SURFACE_DECISIONS)
    if custom_sources:
        raise RepositorySurfaceError(
            "custom observations or decisions require explicit --reconciliation; "
            "use --decision-only when no reconciliation should be applied"
        )
    return DEFAULT_SURFACE_RECONCILIATIONS


def _surface_command(args: argparse.Namespace) -> int:
    observations = json.loads(args.observations.read_text(encoding="utf-8"))
    if args.historical_only:
        report = compile_surface_report(
            observations, expected_public_count=args.expected_public_count
        )
    else:
        decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
        report = compile_governed_surface_report(
            observations,
            decisions,
            expected_public_count=args.expected_public_count,
        )
        if not args.decision_only:
            for reconciliation_path in _resolve_reconciliation_paths(args):
                reconciliation = json.loads(
                    reconciliation_path.read_text(encoding="utf-8")
                )
                report = apply_surface_reconciliation(report, reconciliation)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "branches":
            return _branch_command(args)
        if args.command == "surface-audit":
            return _surface_command(args)

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
    except (
        OSError,
        json.JSONDecodeError,
        LibraryProgramError,
        BranchStewardError,
        RepositorySurfaceError,
    ) as exc:
        print(f"library program error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
