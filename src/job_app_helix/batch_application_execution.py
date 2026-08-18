"""Compile ranked Helix opportunities into deduplicated recruiter-ready packets.

The opportunity queue decides *what should be worked next*. This module closes the
execution gap by compiling actionable queue lanes into the existing tracked application
lifecycle. Optional outcome calibration can re-rank inside the existing safety lanes,
and every selected packet receives a content-addressed priority receipt explaining why
it was selected. External submission is never claimed or performed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .application_engine import CompanyTarget, find_target, load_targets
from .application_operations import (
    ApplicationStore,
    CandidateProfile,
    JobOpening,
    load_candidate_profile,
    load_job_opening,
)
from .application_strategy import (
    compile_requirement_aware_lifecycle,
    project_company_aware_application,
    project_requirement_aware_application,
)
from .company_intelligence import CompanyIntelligence, load_company_intelligence
from .opportunity_queue import (
    ApplicationExecutionQueue,
    ApplicationQueueItem,
    QueueCandidate,
    build_application_execution_queue,
)
from .outcome_calibration import OutcomeCalibration, calibrate_queue

DEFAULT_ACTIONABLE_LANES = ("APPLY_NOW", "APPLY_NEXT")


@dataclass(frozen=True)
class BatchCandidate:
    company: str
    opening_path: Path
    intelligence_path: Path | None = None
    role: str | None = None


@dataclass(frozen=True)
class BatchPacketResult:
    queue_rank: int
    opening_id: str
    company_id: str
    lane: str
    priority_score: float
    application_id: str
    status: str
    packet_dir: str
    priority_receipt: str
    calibration_sha256: str | None
    deduplicated: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BatchExecutionResult:
    schema: str
    queue: ApplicationExecutionQueue
    selected_count: int
    compiled_count: int
    deduplicated_count: int
    skipped_count: int
    calibration_sha256: str | None
    packets: tuple[BatchPacketResult, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "queue": self.queue.as_dict(),
            "selected_count": self.selected_count,
            "compiled_count": self.compiled_count,
            "deduplicated_count": self.deduplicated_count,
            "skipped_count": self.skipped_count,
            "calibration_sha256": self.calibration_sha256,
            "packets": [packet.as_dict() for packet in self.packets],
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_outcome_calibration(path: Path) -> OutcomeCalibration:
    """Load and validate a persisted outcome-calibration model."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, Mapping)
        or value.get("schema") != "glaciereq.outcome-calibration.v1"
    ):
        raise ValueError("invalid outcome calibration artifact")
    return OutcomeCalibration(
        schema=str(value["schema"]),
        sample_count=int(value["sample_count"]),
        effective_sample_count=int(value["effective_sample_count"]),
        status=str(value["status"]),
        baseline_weights=dict(value["baseline_weights"]),
        learned_weights=dict(value["learned_weights"]),
        feature_signal=dict(value["feature_signal"]),
        shrinkage=float(value["shrinkage"]),
        max_weight_shift=float(value["max_weight_shift"]),
    )


def _calibration_sha256(calibration: OutcomeCalibration | None) -> str | None:
    return _canonical_sha256(calibration.as_dict()) if calibration is not None else None


def _score_decomposition(
    item: ApplicationQueueItem,
    calibration: OutcomeCalibration | None,
) -> dict[str, object]:
    if calibration is None:
        return {
            "mode": "BASE_QUEUE",
            "final_priority_score": item.priority_score,
            "reasons": list(item.reasons),
        }

    fit_score = (
        item.company_fit_score
        if item.company_fit_score is not None
        else item.opportunity_score
    )
    freshness_score = 100.0 * (
        item.company_freshness if item.company_freshness is not None else 0.0
    )
    weights = calibration.learned_weights
    contributions = {
        "opportunity": round(float(weights["opportunity"]) * item.opportunity_score, 4),
        "company_fit": round(float(weights["company_fit"]) * fit_score, 4),
        "freshness": round(float(weights["freshness"]) * freshness_score, 4),
    }
    return {
        "mode": "OUTCOME_CALIBRATED",
        "calibration_status": calibration.status,
        "weights": dict(weights),
        "feature_signal": dict(calibration.feature_signal),
        "inputs": {
            "opportunity_score": item.opportunity_score,
            "company_fit_score": fit_score,
            "freshness_score": round(freshness_score, 4),
            "required_coverage": item.required_coverage,
            "hard_gap_count": item.hard_gap_count,
        },
        "weighted_contributions": contributions,
        "uncapped_weighted_score": round(sum(contributions.values()), 4),
        "final_priority_score": item.priority_score,
        "lane": item.lane,
        "reasons": list(item.reasons),
    }


def _write_priority_receipt(
    packet_dir: Path,
    *,
    item: ApplicationQueueItem,
    application_id: str,
    calibration: OutcomeCalibration | None,
    calibration_sha256: str | None,
) -> Path:
    payload: dict[str, object] = {
        "schema": "glaciereq.application-priority-receipt.v1",
        "application_id": application_id,
        "opening_id": item.opening_id,
        "company_id": item.company_id,
        "queue_rank": item.rank,
        "lane": item.lane,
        "priority_score": item.priority_score,
        "calibration_sha256": calibration_sha256,
        "score_decomposition": _score_decomposition(item, calibration),
    }
    payload["receipt_sha256"] = _canonical_sha256(payload)
    target = packet_dir / "PRIORITY_RECEIPT.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def _project_application_id(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    intelligence: CompanyIntelligence | None,
    role: str | None,
) -> str:
    if intelligence is None:
        *_, projection = project_requirement_aware_application(
            opening,
            target,
            profile,
            role=role,
        )
    else:
        *_, projection = project_company_aware_application(
            opening,
            target,
            profile,
            intelligence,
            role=role,
        )
    return projection.application_id


def _packet_is_complete(packet_dir: Path) -> bool:
    required = (
        "RESUME.md",
        "COVER_LETTER.md",
        "OUTREACH.md",
        "PROJECTION_RECEIPT.json",
        "OPPORTUNITY_ASSESSMENT.json",
        "STRATEGY_RECEIPT.json",
        "submission/SUBMISSION_PACKET.json",
    )
    return all((packet_dir / relative).is_file() for relative in required)


def compile_ranked_application_batch(
    candidates: Sequence[QueueCandidate],
    profile: CandidateProfile,
    *,
    output_dir: Path,
    store: ApplicationStore,
    actionable_lanes: Sequence[str] = DEFAULT_ACTIONABLE_LANES,
    limit: int | None = None,
    calibration: OutcomeCalibration | None = None,
) -> BatchExecutionResult:
    """Compile top actionable items with deduplication and ranking provenance.

    Calibration is allowed to re-rank only through the existing ``calibrate_queue``
    safety contract. The priority receipt is regenerated even for deduplicated packets,
    so a new model can explain a changed rank without duplicating lifecycle records.
    """
    normalized_lanes = tuple(dict.fromkeys(lane.upper() for lane in actionable_lanes))
    invalid = set(normalized_lanes) - {
        "APPLY_NOW",
        "APPLY_NEXT",
        "PREPARE_GAPS",
        "DEFER",
        "BLOCKED_PROOF",
    }
    if invalid:
        raise ValueError(f"unknown application queue lane(s): {sorted(invalid)}")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when provided")

    queue = build_application_execution_queue(candidates, profile)
    if calibration is not None:
        queue = calibrate_queue(queue, calibration)
    calibration_sha256 = _calibration_sha256(calibration)

    candidate_by_opening = {candidate[0].opening_id: candidate for candidate in candidates}
    existing_by_id = {
        str(row["application_id"]): row for row in store.list_applications()
    }
    selected = [item for item in queue.items if item.lane in normalized_lanes]
    if limit is not None:
        selected = selected[:limit]

    packets: list[BatchPacketResult] = []
    compiled_count = 0
    deduplicated_count = 0
    for item in selected:
        opening, target, intelligence, role = candidate_by_opening[item.opening_id]
        application_id = _project_application_id(
            opening,
            target,
            profile,
            intelligence,
            role,
        )
        expected_dir = output_dir / application_id
        existing = existing_by_id.get(application_id)
        deduplicated = existing is not None and _packet_is_complete(expected_dir)
        if deduplicated:
            deduplicated_count += 1
            status = str(existing["status"])
        else:
            packet = compile_requirement_aware_lifecycle(
                opening,
                target,
                profile,
                output_dir=output_dir,
                store=store,
                role=role,
                company_intelligence=intelligence,
            )
            compiled_id = str(packet["application_id"])
            if compiled_id != application_id:
                raise RuntimeError(
                    "strategy projection changed between planning and compilation: "
                    f"{application_id} != {compiled_id}"
                )
            compiled_count += 1
            status = str(store.get_application(compiled_id)["status"])

        receipt = _write_priority_receipt(
            expected_dir,
            item=item,
            application_id=application_id,
            calibration=calibration,
            calibration_sha256=calibration_sha256,
        )
        packets.append(
            BatchPacketResult(
                queue_rank=item.rank,
                opening_id=item.opening_id,
                company_id=item.company_id,
                lane=item.lane,
                priority_score=item.priority_score,
                application_id=application_id,
                status=status,
                packet_dir=str(expected_dir),
                priority_receipt=str(receipt),
                calibration_sha256=calibration_sha256,
                deduplicated=deduplicated,
            )
        )

    return BatchExecutionResult(
        schema="glaciereq.batch-application-execution.v2",
        queue=queue,
        selected_count=len(selected),
        compiled_count=compiled_count,
        deduplicated_count=deduplicated_count,
        skipped_count=queue.candidate_count - len(selected),
        calibration_sha256=calibration_sha256,
        packets=tuple(packets),
    )


def load_batch_manifest(path: Path) -> tuple[BatchCandidate, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("batch manifest must be an object")
    raw = payload.get("candidates")
    if not isinstance(raw, list) or not raw:
        raise ValueError("batch manifest requires a non-empty candidates list")

    root = path.parent
    rows: list[BatchCandidate] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"batch candidates[{index}] must be an object")
        opening_value = item.get("opening")
        company_value = item.get("company")
        if not opening_value or not company_value:
            raise ValueError(f"batch candidates[{index}] requires company and opening")
        intelligence_value = item.get("company_intelligence")
        rows.append(
            BatchCandidate(
                company=str(company_value),
                opening_path=root / str(opening_value),
                intelligence_path=(
                    root / str(intelligence_value) if intelligence_value else None
                ),
                role=str(item["role"]) if item.get("role") else None,
            )
        )
    return tuple(rows)


def resolve_batch_candidates(
    manifest: Sequence[BatchCandidate],
) -> tuple[QueueCandidate, ...]:
    targets = load_targets()
    rows: list[QueueCandidate] = []
    for item in manifest:
        target = find_target(item.company, targets)
        opening = load_job_opening(item.opening_path)
        intelligence = (
            load_company_intelligence(item.intelligence_path)
            if item.intelligence_path is not None
            else None
        )
        rows.append((opening, target, intelligence, item.role))
    return tuple(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-batch",
        description=(
            "Rank openings and compile actionable candidates into tracked recruiter "
            "packets with explainable priority provenance and no external submission."
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--lane", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    profile = load_candidate_profile(args.profile)
    candidates = resolve_batch_candidates(load_batch_manifest(args.manifest))
    lanes = tuple(args.lane) if args.lane else DEFAULT_ACTIONABLE_LANES
    calibration = (
        load_outcome_calibration(args.calibration) if args.calibration is not None else None
    )
    with ApplicationStore(args.database) as store:
        result = compile_ranked_application_batch(
            candidates,
            profile,
            output_dir=args.output_dir,
            store=store,
            actionable_lanes=lanes,
            limit=args.limit,
            calibration=calibration,
        )

    rendered = json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.selected_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
