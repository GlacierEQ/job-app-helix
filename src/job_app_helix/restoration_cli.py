"""Command-line surface for exact-source capability archaeology and restoration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .capability_archaeology import excavate
from .cross_file_restoration import apply_cross_file_packet, build_cross_file_packet
from .restoration_executor import apply_packet, build_packet
from .symbol_restoration import (
    apply_symbol_packet,
    build_symbol_packet,
    excavate_python_symbols,
)


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

    symbol_arch = sub.add_parser(
        "symbol-archaeology",
        help="find missing/changed Python functions, classes, and methods",
    )
    symbol_arch.add_argument("--donor", required=True)
    symbol_arch.add_argument("--target", default="HEAD")
    symbol_arch.add_argument("--path", required=True)

    symbol_packet = sub.add_parser(
        "symbol-packet",
        help="build a dependency-aware surgical symbol restoration packet",
    )
    symbol_packet.add_argument("--donor", required=True)
    symbol_packet.add_argument("--target", default="HEAD")
    symbol_packet.add_argument("--path", required=True)
    symbol_packet.add_argument("--select-symbol", action="append", required=True)
    symbol_packet.add_argument("--allow-replace", action="store_true")
    symbol_packet.add_argument("--no-dependencies", action="store_true")

    symbol_apply = sub.add_parser(
        "symbol-apply",
        help="surgically compose exact donor symbols into the current target file",
    )
    symbol_apply.add_argument("--donor", required=True)
    symbol_apply.add_argument("--target", default="HEAD")
    symbol_apply.add_argument("--path", required=True)
    symbol_apply.add_argument("--select-symbol", action="append", required=True)
    symbol_apply.add_argument("--allow-replace", action="store_true")
    symbol_apply.add_argument("--no-dependencies", action="store_true")

    semantic_packet = sub.add_parser(
        "semantic-packet",
        help="build recursive cross-file imported-symbol restoration closure",
    )
    semantic_packet.add_argument("--donor", required=True)
    semantic_packet.add_argument("--target", default="HEAD")
    semantic_packet.add_argument("--path", required=True)
    semantic_packet.add_argument("--select-symbol", action="append", required=True)
    semantic_packet.add_argument("--allow-replace", action="store_true")
    semantic_packet.add_argument("--max-depth", type=int, default=8)

    semantic_apply = sub.add_parser(
        "semantic-apply",
        help="transactionally apply a recursive cross-file restoration closure",
    )
    semantic_apply.add_argument("--donor", required=True)
    semantic_apply.add_argument("--target", default="HEAD")
    semantic_apply.add_argument("--path", required=True)
    semantic_apply.add_argument("--select-symbol", action="append", required=True)
    semantic_apply.add_argument("--allow-replace", action="store_true")
    semantic_apply.add_argument("--max-depth", type=int, default=8)
    return parser


def _symbol_report(args: argparse.Namespace):
    return excavate_python_symbols(
        args.repo,
        donor_ref=args.donor,
        target_ref=args.target,
        path=args.path,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command.startswith("semantic-"):
        packet = build_cross_file_packet(
            args.repo,
            donor_ref=args.donor,
            target_ref=args.target,
            root_path=args.path,
            selected_symbols=tuple(args.select_symbol),
            allow_replace=args.allow_replace,
            max_depth=args.max_depth,
        )
        if args.command == "semantic-packet":
            print(json.dumps(packet.to_dict(), indent=2, sort_keys=True))
            return 0
        receipt = apply_cross_file_packet(args.repo, packet)
        print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command.startswith("symbol-"):
        report = _symbol_report(args)
        if args.command == "symbol-archaeology":
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0
        packet = build_symbol_packet(
            report,
            selected_symbols=tuple(args.select_symbol),
            allow_replace=args.allow_replace,
            include_dependencies=not args.no_dependencies,
        )
        if args.command == "symbol-packet":
            print(json.dumps(packet.to_dict(), indent=2, sort_keys=True))
            return 0
        receipt = apply_symbol_packet(args.repo, packet)
        print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
        return 0

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
