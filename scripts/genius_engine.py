#!/usr/bin/env python3
"""CLI for the Genius Engine."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from job_app_helix.genius_engine import (  # noqa: E402
    invent,
    invent_estate,
    invent_restoration,
    render_markdown,
)


def emit(data: object, output: Path | None, as_markdown: bool = False, run=None) -> None:
    if as_markdown and run is not None:
        text = render_markdown(run)
    else:
        text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def main() -> int:
    p = argparse.ArgumentParser(description="GlacierEQ Genius Engine (APEX)")
    sub = p.add_subparsers(dest="cmd", required=True)

    inv = sub.add_parser("invent", help="Invent genius solutions for one subject")
    inv.add_argument("--repository", required=True)
    inv.add_argument("--company")
    inv.add_argument("--domain")
    inv.add_argument("--bottleneck")
    inv.add_argument("--neutralization-stamps", type=int, default=0)
    inv.add_argument("--paper-recovery", action="store_true")
    inv.add_argument("--limit", type=int, default=3)
    inv.add_argument("--markdown", action="store_true")
    inv.add_argument("--output", type=Path)

    rest = sub.add_parser("restore", help="Invent restoration genius for neutralized leaf")
    rest.add_argument("--repository", required=True)
    rest.add_argument("--limit", type=int, default=3)
    rest.add_argument("--markdown", action="store_true")
    rest.add_argument("--output", type=Path)

    est = sub.add_parser("estate", help="Run genius invent over a JSON list of subjects")
    est.add_argument("subjects", type=Path, help="JSON list of subject objects")
    est.add_argument("--limit-per", type=int, default=1)
    est.add_argument("--output", type=Path)

    args = p.parse_args()
    if args.cmd == "invent":
        subject = {
            "repository": args.repository,
            "company": args.company,
            "domain": args.domain,
            "bottleneck": args.bottleneck,
            "neutralization_stamps": args.neutralization_stamps,
            "paper_recovery_only": args.paper_recovery,
        }
        run = invent(subject, limit=args.limit)
        emit(run.to_dict(), args.output, as_markdown=args.markdown, run=run)
        return 0
    if args.cmd == "restore":
        run = invent_restoration({"repository": args.repository}, limit=args.limit)
        emit(run.to_dict(), args.output, as_markdown=args.markdown, run=run)
        return 0
    if args.cmd == "estate":
        payload = json.loads(args.subjects.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise SystemExit("subjects file must be a JSON list")
        out = invent_estate(payload, limit_per=args.limit_per)
        emit(out, args.output)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
