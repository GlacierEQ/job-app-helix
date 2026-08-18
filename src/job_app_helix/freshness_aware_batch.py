"""Recompile recruiter packets when their live opening inputs materially change.

The existing batch compiler intentionally deduplicates complete application packets. This
adapter makes that optimization content-aware: each compiled packet is bound to the
``JobOpening.digest`` that produced it. A changed digest quarantines the stale packet
before compilation, preserving rollback evidence while forcing the proven batch runtime
to regenerate the recruiter materials from fresh opening content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .application_operations import ApplicationStore, CandidateProfile, load_candidate_profile
from .batch_application_execution import (
    DEFAULT_ACTIONABLE_LANES,
    BatchExecutionResult,
    QueueCandidate,
    _project_application_id,
    compile_ranked_application_batch,
    load_batch_manifest,
    load_outcome_calibration,
    resolve_batch_candidates,
)
from .outcome_calibration import OutcomeCalibration

INPUT_RECEIPT = "OPENING_INPUT_RECEIPT.json"


@dataclass(frozen=True)
class FreshnessDecision:
    application_id: str
    opening_id: str
    opening_digest: str
    previous_digest: str | None
    action: str
    quarantine_path: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "application_id": self.application_id,
            "opening_id": self.opening_id,
            "opening_digest": self.opening_digest,
            "previous_digest": self.previous_digest,
            "action": self.action,
            "quarantine_path": self.quarantine_path,
        }


@dataclass(frozen=True)
class FreshnessAwareBatchResult:
    schema: str
    refreshed_count: int
    reused_count: int
    decisions: tuple[FreshnessDecision, ...]
    batch: BatchExecutionResult

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "refreshed_count": self.refreshed_count,
            "reused_count": self.reused_count,
            "decisions": [decision.as_dict() for decision in self.decisions],
            "batch": self.batch.as_dict(),
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_previous_digest(packet_dir: Path) -> str | None:
    receipt = packet_dir / INPUT_RECEIPT
    if not receipt.is_file():
        return None
    try:
        payload = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("opening_digest") if isinstance(payload, Mapping) else None
    return str(value) if value else None


def _quarantine(packet_dir: Path, *, output_dir: Path, application_id: str, digest: str) -> Path:
    stale_root = output_dir / ".stale"
    stale_root.mkdir(parents=True, exist_ok=True)
    base = stale_root / f"{application_id}-{digest[:12]}"
    target = base
    suffix = 1
    while target.exists():
        suffix += 1
        target = stale_root / f"{base.name}-{suffix}"
    packet_dir.replace(target)
    return target


def _write_input_receipt(
    packet_dir: Path,
    *,
    application_id: str,
    opening_id: str,
    digest: str,
) -> None:
    payload: dict[str, object] = {
        "schema": "glaciereq.opening-input-receipt.v1",
        "application_id": application_id,
        "opening_id": opening_id,
        "opening_digest": digest,
    }
    payload["receipt_sha256"] = _canonical_sha256(payload)
    target = packet_dir / INPUT_RECEIPT
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def compile_freshness_aware_batch(
    candidates: Sequence[QueueCandidate],
    profile: CandidateProfile,
    *,
    output_dir: Path,
    store: ApplicationStore,
    actionable_lanes: Sequence[str] = DEFAULT_ACTIONABLE_LANES,
    limit: int | None = None,
    calibration: OutcomeCalibration | None = None,
) -> FreshnessAwareBatchResult:
    """Compile ranked packets while invalidating packets built from stale opening content."""
    if not candidates:
        raise ValueError("freshness-aware batch requires at least one candidate")

    decisions: list[FreshnessDecision] = []
    identity_by_opening: dict[str, tuple[str, str]] = {}
    for opening, target, intelligence, role in candidates:
        application_id = _project_application_id(opening, target, profile, intelligence, role)
        identity_by_opening[opening.opening_id] = (application_id, opening.digest)
        packet_dir = output_dir / application_id
        previous_digest = _load_previous_digest(packet_dir)
        quarantine_path: str | None = None
        action = "NO_PACKET"
        if packet_dir.is_dir():
            if previous_digest == opening.digest:
                action = "REUSE_CURRENT"
            else:
                previous_identity = previous_digest or "unbound"
                quarantined = _quarantine(
                    packet_dir,
                    output_dir=output_dir,
                    application_id=application_id,
                    digest=previous_identity,
                )
                quarantine_path = str(quarantined)
                action = "REFRESH_STALE"
        decisions.append(
            FreshnessDecision(
                application_id=application_id,
                opening_id=opening.opening_id,
                opening_digest=opening.digest,
                previous_digest=previous_digest,
                action=action,
                quarantine_path=quarantine_path,
            )
        )

    batch = compile_ranked_application_batch(
        candidates,
        profile,
        output_dir=output_dir,
        store=store,
        actionable_lanes=actionable_lanes,
        limit=limit,
        calibration=calibration,
    )

    for packet in batch.packets:
        identity = identity_by_opening.get(packet.opening_id)
        if identity is None:
            raise RuntimeError(f"batch returned unknown opening: {packet.opening_id}")
        application_id, digest = identity
        if packet.application_id != application_id:
            raise RuntimeError(
                "application identity changed during freshness-aware compilation: "
                f"{application_id} != {packet.application_id}"
            )
        _write_input_receipt(
            Path(packet.packet_dir),
            application_id=application_id,
            opening_id=packet.opening_id,
            digest=digest,
        )

    return FreshnessAwareBatchResult(
        schema="glaciereq.freshness-aware-batch.v1",
        refreshed_count=sum(decision.action == "REFRESH_STALE" for decision in decisions),
        reused_count=sum(decision.action == "REUSE_CURRENT" for decision in decisions),
        decisions=tuple(decisions),
        batch=batch,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-freshness-batch",
        description=(
            "Rank openings and rebuild recruiter packets only when their bound opening "
            "content has changed, quarantining stale packet state for rollback."
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
    calibration = load_outcome_calibration(args.calibration) if args.calibration else None
    lanes = tuple(args.lane) if args.lane else DEFAULT_ACTIONABLE_LANES
    with ApplicationStore(args.database) as store:
        result = compile_freshness_aware_batch(
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
    return 0 if result.batch.selected_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
