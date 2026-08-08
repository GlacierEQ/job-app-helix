#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from job_app_helix.innovation_engine import (
    adversarial_gate,
    assert_expected_head,
    compile_engineering_ledger,
    compile_estate_target_queue,
    compile_hypothesis_tournament,
    load_json,
    novelty_gate,
    promotion_gate,
    transition_run,
    validate_payload,
)


def emit(value: object, output: Path | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Frontier repository innovation runtime")
    commands = root.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("schema")
    validate.add_argument("payload", type=Path)

    transition = commands.add_parser("transition")
    transition.add_argument("run", type=Path)
    transition.add_argument("target")
    transition.add_argument("--evidence-ref", action="append", required=True)
    transition.add_argument("--output", type=Path)

    gate = commands.add_parser("gate")
    gate.add_argument("promotion", type=Path)

    queue = commands.add_parser("queue")
    queue.add_argument("estate_bundle", type=Path)
    queue.add_argument("assessments", type=Path)
    queue.add_argument("--expected-estate-hash", required=True)
    queue.add_argument("--output", type=Path)

    tournament = commands.add_parser("tournament")
    tournament.add_argument("assessments", type=Path)
    tournament.add_argument("--output", type=Path)

    adversarial = commands.add_parser("adversarial-gate")
    adversarial.add_argument("review", type=Path)

    novelty = commands.add_parser("novelty-gate")
    novelty.add_argument("review", type=Path)

    head = commands.add_parser("expected-head")
    head.add_argument("expected")
    head.add_argument("observed")

    ledger = commands.add_parser("ledger")
    ledger.add_argument("run", type=Path)
    ledger.add_argument("--output", type=Path)
    return root


def load_list(path: Path, label: str) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{label} must be a JSON list of objects")
    return payload


def main() -> int:
    args = parser().parse_args()
    if args.command == "validate":
        payload = load_json(args.payload)
        validate_payload(payload, args.schema)
        emit({"status": "VERIFIED", "schema": args.schema}, None)
    elif args.command == "transition":
        run = load_json(args.run)
        validate_payload(run, "engineering-run")
        updated = transition_run(run, args.target, args.evidence_ref)
        validate_payload(updated, "engineering-run")
        emit(updated, args.output)
    elif args.command == "gate":
        promotion = load_json(args.promotion)
        validate_payload(promotion, "promotion")
        decision = promotion_gate(promotion)
        emit({"ready": decision.ready, "failures": list(decision.failures)}, None)
        return 0 if decision.ready else 3
    elif args.command == "queue":
        assessments = load_list(args.assessments, "assessments")
        estate = load_json(args.estate_bundle)
        queue = compile_estate_target_queue(
            estate,
            assessments,
            args.expected_estate_hash,
        )
        emit(queue, args.output)
    elif args.command == "tournament":
        assessments = load_list(args.assessments, "hypothesis assessments")
        emit(compile_hypothesis_tournament(assessments), args.output)
    elif args.command == "adversarial-gate":
        decision = adversarial_gate(load_json(args.review))
        emit({"survives": decision.survives, "blockers": list(decision.blockers)}, None)
        return 0 if decision.survives else 4
    elif args.command == "novelty-gate":
        decision = novelty_gate(load_json(args.review))
        emit({"survives": decision.survives, "blockers": list(decision.blockers)}, None)
        return 0 if decision.survives else 5
    elif args.command == "expected-head":
        assert_expected_head(args.expected, args.observed)
        emit({"status": "MATCH", "head": args.expected}, None)
    elif args.command == "ledger":
        run = load_json(args.run)
        validate_payload(run, "engineering-run")
        emit(compile_engineering_ledger(run), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
