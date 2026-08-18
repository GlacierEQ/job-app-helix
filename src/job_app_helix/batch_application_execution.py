"""Compile ranked Helix opportunities into deduplicated recruiter-ready packets.

The opportunity queue decides *what should be worked next*. This module closes the
execution gap by compiling only actionable queue lanes into the existing tracked
application lifecycle. It deliberately prepares submission artifacts without claiming
or performing external submission.
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
    deduplicated: bool
    ranking_receipt: str
    calibration_id: str | None

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
    calibration_id: str | None
    packets: tuple[BatchPacketResult, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "queue": self.queue.as_dict(),
            "selected_count": self.selected_count,
            "compiled_count": self.compiled_count,
            "deduplicated_count": self.deduplicated_count,
            "skipped_count": self.skipped_count,
            "calibration_id": self.calibration_id,
            "packets": [packet.as_dict() for packet in self.packets],
        }


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _calibration_identity(calibration: OutcomeCalibration | None) -> str | None:
    if calibration is None:
        return None
    digest = hashlib.sha256(_canonical_json(calibration.as_dict()).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _load_calibration(path: Path) -> OutcomeCalibration:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping) or value.get("schema") != "glaciereq.outcome-calibration.v1":
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
        "RANKING_RECEIPT.json",
        "submission/SUBMISSION_PACKET.json",
    )
    return all((packet_dir / relative).is_file() for relative in required)


def _item_by_opening(queue: ApplicationExecutionQueue) -> dict[str, ApplicationQueueItem]:
    return {item.opening_id: item for item in queue.items}


def _ranking_receipt(
    item: ApplicationQueueItem,
    baseline_item: ApplicationQueueItem,
    calibration: OutcomeCalibration | None,
) -> dict[str, object]:
    calibration_id = _calibration_identity(calibration)
    receipt: dict[str, object] = {
        "schema": "glaciereq.application-ranking-receipt.v1",
        "opening_id": item.opening_id,
        "company_id": item.company_id,
        "lane": item.lane,
        "queue_rank": item.rank,
        "baseline_priority_score": baseline_item.priority_score,
        "final_priority_score": item.priority_score,
        "required_coverage": item.required_coverage,
        "hard_gap_count": item.hard_gap_count,
        "company_fit_score": item.company_fit_score,
        "company_freshness": item.company_freshness,
        "queue_reasons": list(item.reasons),
        "calibration_id": calibration_id,
        "calibration": None,
    }
    if calibration is not None:
        fit = (
            baseline_item.company_fit_score
            if baseline_item.company_fit_score is not None
            else baseline_item.opportunity_score
        )
        freshness = 100.0 * (
            baseline_item.company_freshness
            if baseline_item.company_freshness is not None
            else 0.0
        )
        weights = calibration.learned_weights
        components = {
            "opportunity": round(float(weights["opportunity"]) * baseline_item.opportunity_score, 6),
            "company_fit": round(float(weights["company_fit"]) * fit, 6),
            "freshness": round(float(weights["freshness"]) * freshness, 6),
        }
        raw_score = round(sum(components.values()), 6)
        receipt["calibration"] = {
            "schema": calibration.schema,
            "status": calibration.status,
            "sample_count": calibration.sample_count,
            "effective_sample_count": calibration.effective_sample_count,
            "learned_weights": dict(calibration.learned_weights),
            "feature_signal": dict(calibration.feature_signal),
            "shrinkage": calibration.shrinkage,
            "max_weight_shift": calibration.max_weight_shift,
            "score_components": components,
            "raw_calibrated_score": raw_score,
            "lane_cap_applied": raw_score > item.priority_score,
        }
    receipt_payload = dict(receipt)
    receipt["receipt_sha256"] = hashlib.sha256(
        _canonical_json(receipt_payload).encode("utf-8")
    ).hexdigest()
    return receipt


def _persist_ranking_receipt(packet_dir: Path, receipt: Mapping[str, object]) -> Path:
    packet_dir.mkdir(parents=True, exist_ok=True)
    path = packet_dir / "RANKING_RECEIPT.json"
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)
    return path


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
    """Compile top actionable queue items and persist exact ranking rationale.

    Deduplication is keyed by the deterministic strategy application id. Existing
    application records are reused only when the packet directory still contains the
    complete recruiter packet, including the ranking receipt. Incomplete records are
    repaired by recompilation. Outcome calibration can change ordering but cannot alter
    candidate evidence or bypass the queue's existing safety lanes and caps.
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

    baseline_queue = build_application_execution_queue(candidates, profile)
    queue = calibrate_queue(baseline_queue, calibration) if calibration is not None else baseline_queue
    baseline_by_opening = _item_by_opening(baseline_queue)
    candidate_by_opening = {candidate[0].opening_id: candidate for candidate in candidates}
    existing_by_id = {
        str(row["application_id"]): row for row in store.list_applications()
    }
    selected = [item for item in queue.items if item.lane in normalized_lanes]
    if limit is not None:
        selected = selected[:limit]

    calibration_id = _calibration_identity(calibration)
    packets: list[BatchPacketResult] = []
    compiled_count = 0
    deduplicated_count = 0
    for item in selected:
        opening, target, intelligence, role = candidate_by_opening[item.opening_id]
        baseline_item = baseline_by_opening[item.opening_id]
        application_id = _project_application_id(
            opening,
            target,
            profile,
            intelligence,
            role,
        )
        expected_dir = output_dir / application_id
        ranking_receipt = _ranking_receipt(item, baseline_item, calibration)
        ranking_path = expected_dir / "RANKING_RECEIPT.json"
        existing = existing_by_id.get(application_id)
        if existing is not None and _packet_is_complete(expected_dir):
            current_receipt = json.loads(ranking_path.read_text(encoding="utf-8"))
            if current_receipt == ranking_receipt:
                deduplicated_count += 1
                packets.append(
                    BatchPacketResult(
                        queue_rank=item.rank,
                        opening_id=item.opening_id,
                        company_id=item.company_id,
                        lane=item.lane,
                        priority_score=item.priority_score,
                        application_id=application_id,
                        status=str(existing["status"]),
                        packet_dir=str(expected_dir),
                        deduplicated=True,
                        ranking_receipt=str(ranking_path),
                        calibration_id=calibration_id,
                    )
                )
                continue

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
        ranking_path = _persist_ranking_receipt(expected_dir, ranking_receipt)
        compiled_count += 1
        record = store.get_application(compiled_id)
        packets.append(
            BatchPacketResult(
                queue_rank=item.rank,
                opening_id=item.opening_id,
                company_id=item.company_id,
                lane=item.lane,
                priority_score=item.priority_score,
                application_id=compiled_id,
                status=str(record["status"]),
                packet_dir=str(expected_dir),
                deduplicated=False,
                ranking_receipt=str(ranking_path),
                calibration_id=calibration_id,
            )
        )

    return BatchExecutionResult(
        schema="glaciereq.batch-application-execution.v2",
        queue=queue,
        selected_count=len(selected),
        compiled_count=compiled_count,
        deduplicated_count=deduplicated_count,
        skipped_count=queue.candidate_count - len(selected),
        calibration_id=calibration_id,
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
            raise ValueError(
                f"batch candidates[{index}] requires company and opening"
            )
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
            "Rank openings and compile the top actionable candidates into tracked, "
            "deduplicated recruiter packets without performing submission."
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--lane", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--calibration",
        type=Path,
        help="optional glaciereq.outcome-calibration.v1 artifact used for queue ordering",
    )
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    profile = load_candidate_profile(args.profile)
    candidates = resolve_batch_candidates(load_batch_manifest(args.manifest))
    lanes = tuple(args.lane) if args.lane else DEFAULT_ACTIONABLE_LANES
    calibration = _load_calibration(args.calibration) if args.calibration else None
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
