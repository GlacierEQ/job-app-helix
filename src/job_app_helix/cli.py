from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .application_engine import (
    build_application_kit,
    find_target,
    load_targets,
    render_markdown,
    write_application_kit,
)
from .campaign import CampaignPolicy, LaunchScenario, run_campaign
from .models import CampaignReport

SCENARIOS = ("nominal", "recoverable", "hard-no-go")


def _scenario(name: str) -> LaunchScenario:
    factories = {
        "nominal": LaunchScenario.nominal,
        "recoverable": LaunchScenario.recoverable,
        "hard-no-go": LaunchScenario.hard_no_go,
    }
    return factories[name]()


def _render_demo(report: CampaignReport) -> str:
    lines = [
        "JOB-APP HELIX — LEGACY CAMPAIGN DEMO",
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
            lines.append(f"  {refinement.stage}: {refinement.action} — {refinement.rationale}")
    lines.extend(["", "Final verification"])
    for result in report.final_results:
        lines.append(f"  {result.status.value:5}  {result.name}: {result.summary}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix",
        description="Compile evidence-bound job application outcomes from the GlacierEQ portfolio.",
    )
    sub = parser.add_subparsers(dest="command")

    targets = sub.add_parser("targets", help="list mapped company targets and readiness")
    targets.add_argument("--json", action="store_true")

    application = sub.add_parser("application", help="compile a role-specific application kit")
    application.add_argument("company", help="company id or unambiguous display name")
    application.add_argument("--role", help="mapped target role; defaults to the first role")
    application.add_argument("--output-dir", type=Path, help="write JSON and Markdown kit")
    application.add_argument("--json", action="store_true", help="print machine-readable kit")

    demo = sub.add_parser("demo", help="run the legacy deterministic spacecraft campaign fixture")
    demo.add_argument("scenario", choices=SCENARIOS, nargs="?", default="nominal")
    demo.add_argument("--no-refinement", action="store_true")
    demo.add_argument("--json", action="store_true")
    demo.add_argument("--output", type=Path)
    return parser


def _run_targets(as_json: bool) -> int:
    targets = load_targets()
    rows = [
        {
            "company_id": target.company_id,
            "company": target.display_name,
            "track_state": target.track_state,
            "target_roles": list(target.target_roles),
            "public_proof_count": len(target.recruiter_proofs),
            "readiness": (
                "READY_WITH_PUBLIC_PROOF"
                if target.recruiter_proofs
                else "INCOMPLETE_NO_ADMITTED_PUBLIC_PROOF"
            ),
        }
        for target in targets
    ]
    if as_json:
        print(json.dumps({"schema": "glaciereq.job-target-index.v1", "targets": rows}, indent=2))
    else:
        for row in rows:
            print(
                f"{row['company_id']:24} {row['readiness']:36} "
                f"proofs={row['public_proof_count']:2}  {row['company']}"
            )
    return 0


def _run_application(company: str, role: str | None, output_dir: Path | None, as_json: bool) -> int:
    target = find_target(company, load_targets())
    kit = build_application_kit(target, role)
    if output_dir:
        json_path, markdown_path = write_application_kit(kit, output_dir)
        print(f"WROTE {json_path}")
        print(f"WROTE {markdown_path}")
    if as_json:
        print(json.dumps(kit.as_dict(), indent=2, sort_keys=True))
    else:
        print(render_markdown(kit), end="")
    return 0 if kit.readiness == "READY_WITH_PUBLIC_PROOF" else 2


def _run_demo(args: argparse.Namespace) -> int:
    report = run_campaign(
        _scenario(args.scenario),
        CampaignPolicy(allow_refinement=not args.no_refinement),
    )
    payload = report.to_dict()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else _render_demo(report))
    return 0 if report.decision.value == "GO" else 1


def main(argv: Sequence[str] | None = None) -> int:
    values = list(argv) if argv is not None else None
    # Preserve historical `job-app-helix nominal` calls, but never make a synthetic
    # launch scenario the default product behavior again.
    if values and values[0] in SCENARIOS:
        values = ["demo", *values]
    parser = build_parser()
    args = parser.parse_args(values)
    try:
        if args.command in {None, "targets"}:
            return _run_targets(bool(getattr(args, "json", False)))
        if args.command == "application":
            return _run_application(args.company, args.role, args.output_dir, args.json)
        if args.command == "demo":
            return _run_demo(args)
        parser.error(f"unknown command: {args.command}")
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"job-app-helix: {exc}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
