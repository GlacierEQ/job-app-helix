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
from .application_operations import (
    ApplicationStore,
    compile_application_lifecycle,
    ingest_job_opening_url,
    load_candidate_profile,
    load_job_opening,
)
from .campaign import CampaignPolicy, LaunchScenario, run_campaign
from .models import CampaignReport

SCENARIOS = ("nominal", "recoverable", "hard-no-go")
DEFAULT_APPLICATION_DB = Path(
    "artifacts/application-operations.sqlite3"
)


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
        (
            "Recovered after refinement: "
            f"{'yes' if report.recovered else 'no'}"
        ),
        "",
        "Initial verification",
    ]
    for result in report.initial_results:
        lines.append(
            f"  {result.status.value:5}  "
            f"{result.name}: {result.summary}"
        )
        for finding in result.findings:
            lines.append(
                f"         - {finding.code}: "
                f"{finding.message}"
            )
    if report.refinements:
        lines.extend(
            ["", "Declared contingency stroke"]
        )
        for refinement in report.refinements:
            lines.append(
                f"  {refinement.stage}: "
                f"{refinement.action} — "
                f"{refinement.rationale}"
            )
    lines.extend(["", "Final verification"])
    for result in report.final_results:
        lines.append(
            f"  {result.status.value:5}  "
            f"{result.name}: {result.summary}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix",
        description=(
            "Run evidence-bound job targeting "
            "and application operations."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    targets = sub.add_parser(
        "targets",
        help="list mapped company targets and readiness",
    )
    targets.add_argument(
        "--json",
        action="store_true",
    )

    application = sub.add_parser(
        "application",
        help="compile a role-specific application kit",
    )
    application.add_argument(
        "company",
        help="company id or unambiguous display name",
    )
    application.add_argument(
        "--role",
        help="mapped target role; defaults to the first role",
    )
    application.add_argument(
        "--output-dir",
        type=Path,
        help="write JSON and Markdown kit",
    )
    application.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable kit",
    )

    ingest = sub.add_parser(
        "ingest",
        help="ingest a job opening from JSON or a live URL",
    )
    source = ingest.add_mutually_exclusive_group(
        required=True
    )
    source.add_argument(
        "--file",
        type=Path,
        help="JSON job-opening record",
    )
    source.add_argument(
        "--url",
        help="URL containing JSON or JSON-LD JobPosting data",
    )
    ingest.add_argument(
        "--output",
        type=Path,
        help="write normalized opening JSON",
    )
    ingest.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_APPLICATION_DB,
    )
    ingest.add_argument(
        "--json",
        action="store_true",
    )

    project = sub.add_parser(
        "project",
        help=(
            "match a real opening and compile resume, "
            "cover letter, outreach, and packet"
        ),
    )
    project.add_argument(
        "company",
        help="mapped company id or display name",
    )
    project.add_argument(
        "--opening",
        type=Path,
        required=True,
        help="normalized job opening JSON",
    )
    project.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="evidence-only candidate profile",
    )
    project.add_argument(
        "--role",
        help="mapped target role",
    )
    project.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/applications"),
    )
    project.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_APPLICATION_DB,
    )
    project.add_argument(
        "--json",
        action="store_true",
    )

    applications = sub.add_parser(
        "applications",
        help="list persisted application state",
    )
    applications.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_APPLICATION_DB,
    )
    applications.add_argument(
        "--json",
        action="store_true",
    )

    transition = sub.add_parser(
        "transition",
        help="move a persisted application state",
    )
    transition.add_argument("application_id")
    transition.add_argument("status")
    transition.add_argument(
        "--external-reference"
    )
    transition.add_argument(
        "--note",
        default="",
    )
    transition.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_APPLICATION_DB,
    )

    response = sub.add_parser(
        "response",
        help="record a response and update lifecycle state",
    )
    response.add_argument("application_id")
    response.add_argument(
        "kind",
        choices=(
            "interview",
            "offer",
            "rejection",
            "other",
        ),
    )
    response.add_argument(
        "--note",
        required=True,
    )
    response.add_argument(
        "--source-reference"
    )
    response.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_APPLICATION_DB,
    )

    feedback = sub.add_parser(
        "feedback",
        help="record outcome feedback for future iteration",
    )
    feedback.add_argument("application_id")
    feedback.add_argument("outcome")
    feedback.add_argument(
        "--note",
        required=True,
    )
    feedback.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_APPLICATION_DB,
    )

    summary = sub.add_parser(
        "feedback-summary",
        help="show lifecycle outcome counts",
    )
    summary.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_APPLICATION_DB,
    )

    demo = sub.add_parser(
        "demo",
        help="run the legacy deterministic campaign fixture",
    )
    demo.add_argument(
        "scenario",
        choices=SCENARIOS,
        nargs="?",
        default="nominal",
    )
    demo.add_argument(
        "--no-refinement",
        action="store_true",
    )
    demo.add_argument(
        "--json",
        action="store_true",
    )
    demo.add_argument(
        "--output",
        type=Path,
    )
    return parser


def _run_targets(as_json: bool) -> int:
    targets = load_targets()
    rows = [
        {
            "company_id": target.company_id,
            "company": target.display_name,
            "track_state": target.track_state,
            "target_roles": list(
                target.target_roles
            ),
            "public_proof_count": len(
                target.recruiter_proofs
            ),
            "readiness": (
                "READY_WITH_PUBLIC_PROOF"
                if target.recruiter_proofs
                else (
                    "INCOMPLETE_"
                    "NO_ADMITTED_PUBLIC_PROOF"
                )
            ),
        }
        for target in targets
    ]
    if as_json:
        print(
            json.dumps(
                {
                    "schema": (
                        "glaciereq."
                        "job-target-index.v1"
                    ),
                    "targets": rows,
                },
                indent=2,
            )
        )
    else:
        for row in rows:
            print(
                f"{row['company_id']:24} "
                f"{row['readiness']:36} "
                f"proofs={row['public_proof_count']:2}  "
                f"{row['company']}"
            )
    return 0


def _run_application(
    company: str,
    role: str | None,
    output_dir: Path | None,
    as_json: bool,
) -> int:
    target = find_target(
        company,
        load_targets(),
    )
    kit = build_application_kit(
        target,
        role,
    )
    if output_dir:
        json_path, markdown_path = (
            write_application_kit(
                kit,
                output_dir,
            )
        )
        print(f"WROTE {json_path}")
        print(f"WROTE {markdown_path}")
    if as_json:
        print(
            json.dumps(
                kit.as_dict(),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            render_markdown(kit),
            end="",
        )
    return (
        0
        if kit.readiness
        == "READY_WITH_PUBLIC_PROOF"
        else 2
    )


def _run_ingest(args: argparse.Namespace) -> int:
    opening = (
        load_job_opening(args.file)
        if args.file
        else ingest_job_opening_url(args.url)
    )
    with ApplicationStore(
        args.db
    ) as store:
        store.save_opening(opening)
    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            json.dumps(
                opening.as_dict(),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(
            json.dumps(
                opening.as_dict(),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            f"INGESTED {opening.opening_id} | "
            f"{opening.company} | {opening.title} | "
            f"digest={opening.digest}"
        )
    return 0


def _run_project(args: argparse.Namespace) -> int:
    target = find_target(
        args.company,
        load_targets(),
    )
    opening = load_job_opening(
        args.opening
    )
    profile = load_candidate_profile(
        args.profile
    )
    with ApplicationStore(
        args.db
    ) as store:
        packet = compile_application_lifecycle(
            opening,
            target,
            profile,
            output_dir=args.output_dir,
            store=store,
            role=args.role,
        )
    if args.json:
        print(
            json.dumps(
                packet,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            f"READY {packet['application_id']} | "
            f"match="
            f"{packet['match']['overall_score']:.3f} | "
            f"adapter="
            f"{packet['adapter_receipt']['adapter']}"
        )
        for name, path in (
            packet["artifacts"].items()
        ):
            print(f"  {name}: {path}")
    return 0


def _run_applications(
    args: argparse.Namespace,
) -> int:
    with ApplicationStore(
        args.db
    ) as store:
        rows = store.list_applications()
    if args.json:
        print(
            json.dumps(
                {"applications": rows},
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for row in rows:
            print(
                f"{row['application_id']} "
                f"{row['status']:10} "
                f"{row['company_id']} | "
                f"{row['role']}"
            )
    return 0


def _run_transition(
    args: argparse.Namespace,
) -> int:
    with ApplicationStore(
        args.db
    ) as store:
        store.transition(
            args.application_id,
            args.status,
            external_reference=(
                args.external_reference
            ),
            note=args.note,
        )
        row = store.get_application(
            args.application_id
        )
    print(
        json.dumps(
            row,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _run_response(
    args: argparse.Namespace,
) -> int:
    with ApplicationStore(
        args.db
    ) as store:
        store.record_response(
            args.application_id,
            args.kind,
            args.note,
            source_reference=(
                args.source_reference
            ),
        )
        row = store.get_application(
            args.application_id
        )
    print(
        json.dumps(
            row,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _run_feedback(
    args: argparse.Namespace,
) -> int:
    with ApplicationStore(
        args.db
    ) as store:
        store.record_feedback(
            args.application_id,
            args.outcome,
            args.note,
        )
        events = store.events(
            args.application_id
        )
    print(
        json.dumps(
            events[-1],
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _run_feedback_summary(
    args: argparse.Namespace,
) -> int:
    with ApplicationStore(
        args.db
    ) as store:
        value = store.feedback_summary()
    print(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _run_demo(
    args: argparse.Namespace,
) -> int:
    report = run_campaign(
        _scenario(args.scenario),
        CampaignPolicy(
            allow_refinement=(
                not args.no_refinement
            )
        ),
    )
    payload = report.to_dict()
    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            json.dumps(
                payload,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            payload,
            indent=2,
        )
        if args.json
        else _render_demo(report)
    )
    return (
        0
        if report.decision.value == "GO"
        else 1
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    values = (
        list(argv)
        if argv is not None
        else None
    )
    if values and values[0] in SCENARIOS:
        values = ["demo", *values]

    parser = build_parser()
    args = parser.parse_args(values)
    try:
        if args.command in {None, "targets"}:
            return _run_targets(
                bool(
                    getattr(
                        args,
                        "json",
                        False,
                    )
                )
            )
        if args.command == "application":
            return _run_application(
                args.company,
                args.role,
                args.output_dir,
                args.json,
            )
        if args.command == "ingest":
            return _run_ingest(args)
        if args.command == "project":
            return _run_project(args)
        if args.command == "applications":
            return _run_applications(args)
        if args.command == "transition":
            return _run_transition(args)
        if args.command == "response":
            return _run_response(args)
        if args.command == "feedback":
            return _run_feedback(args)
        if args.command == "feedback-summary":
            return _run_feedback_summary(args)
        if args.command == "demo":
            return _run_demo(args)
        parser.error(
            f"unknown command: {args.command}"
        )
    except (
        FileNotFoundError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        parser.exit(
            2,
            f"job-app-helix: {exc}\n",
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
