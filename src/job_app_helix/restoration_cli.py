"""Command-line surface for exact-source capability archaeology and restoration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .capability_archaeology import excavate
from .restoration_executor import apply_packet, build_packet


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-app-helix-restore")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)

    archaeology = sub.add_parser("archaeology", help="rank changed/deleted donor capability")
    archaeology.add_argument("--donor", required=True)
    archaeology.add_argument("--target", default="HEAD")
    archaeology.add_argument("--path", action="append", default=[])

    packet = sub.add_parser("packet", help="build a deterministic restoration packet")
    packet.add_argument("--donor", required=True)
    packet.add_argument("--target", default="HEAD")
    packet.add_argument("--select", action="append", required=True)
    packet.add_argument("--allow-replace", action="store_true")

    apply_cmd = sub.add_parser("apply", help="apply selected donor files with drift guards")
    apply_cmd.add_argument("--donor", required=True)
    apply_cmd.add_argument("--target", default="HEAD")
    apply_cmd.add_argument("--select", action="append", required=True)
    apply_cmd.add_argument("--allow-replace", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = excavate(
        args.repo,
        donor_ref=args.donor,
        target_ref=args.target,
        include_paths=tuple(getattr(args, "path", ())),
    )
    if args.command == "archaeology":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0

    packet = build_packet(
        report.candidates,
        selected_paths=tuple(args.select),
        allow_replace=args.allow_replace,
    )
    if args.command == "packet":
        print(json.dumps(packet.to_dict(), indent=2, sort_keys=True))
        return 0

    receipt = apply_packet(args.repo, packet)
    print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
