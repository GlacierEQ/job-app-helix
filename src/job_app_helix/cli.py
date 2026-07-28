from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .campaign import CampaignPolicy, LaunchScenario, run_campaign
from .models import CampaignReport


def _scenario(name: str) -> LaunchScenario:
    factories = {
        "nominal": LaunchScenario.nominal,
        "recoverable": LaunchScenario.recoverable,
        "hard-no-go": LaunchScenario.hard_no_go,
    }
    return factories[name]()


def _render_human(report: CampaignReport) -> str:
    lines = [
        "JOB-APP HELIX — CAMPAIGN PROOF",
        f"Scenario: {report.scenario}",
        f"Decision: {report.decision.value}",
        f"Recovered after refinement: {'yes' if report.recovered else 'no'}",
        "",
        "Initial verification",
    ]
    for result in report.initial_results:
        lines.append(f"  {result.status.value:5}  {result.name}: {result.summary}")
        for finding in result.findings:
            lines.append(f"         - {finding.code}: {finding.message}")

    if report.refinements:
        lines.extend(["", "Declared contingency stroke"])
        for refinement in report.refinements:
            lines.append(
                f"  {refinement.stage}: {refinement.action} — {refinement.rationale}"
            )

    lines.extend(["", "Final verification"])
    for result in report.final_results:
        lines.append(f"  {result.status.value:5}  {result.name}: {result.summary}")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix",
        description="Run a reproducible build-and-verify campaign demonstration.",
    )
    parser.add_argument(
        "scenario",
        choices=("nominal", "recoverable", "hard-no-go"),
        nargs="?",
        default="nominal",
        help="Built-in deterministic scenario to execute.",
    )
    parser.add_argument(
        "--no-refinement",
        action="store_true",
        help="Disable the single declared contingency stroke.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete machine-readable proof receipt.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the JSON proof receipt to this path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_campaign(
        _scenario(args.scenario),
        CampaignPolicy(allow_refinement=not args.no_refinement),
    )
    payload = report.to_dict()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(_render_human(report))

    return 0 if report.decision.value == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
