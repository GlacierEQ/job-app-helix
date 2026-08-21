"""Read-only freshness and re-verification planning for recruiter packet evidence.

Packet compilation already preserves opening-input digests and stale packet lineage. This
module adds an additive evidence-time lens: it never edits a packet, deletes history, or
claims a source was refreshed. Instead, it classifies the explicitly recorded upstream
source observation timestamp and yields an actionable re-verification plan when evidence
is absent, malformed, aging, or stale.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

INPUT_RECEIPT = "OPENING_INPUT_RECEIPT.json"
VALID_STATES = {
    "fresh",
    "aging",
    "stale",
    "source_observation_required",
    "invalid_source_observation",
}


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(
            "source evidence observation timestamp must include a timezone"
        )
    return parsed.astimezone(UTC)


def _read_receipt(packet_dir: Path) -> Mapping[str, Any] | None:
    path = packet_dir / INPUT_RECEIPT
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


@dataclass(frozen=True)
class OpeningEvidenceFreshness:
    application_id: str | None
    opening_id: str | None
    opening_digest: str | None
    state: str
    source_evidence_observed_at: str | None
    age_minutes: int | None
    action: str
    continuation: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OpeningEvidenceFreshnessCensus:
    schema: str
    max_age_minutes: int
    packet_count: int
    fresh_count: int
    attention_count: int
    decisions: tuple[OpeningEvidenceFreshness, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "max_age_minutes": self.max_age_minutes,
            "packet_count": self.packet_count,
            "fresh_count": self.fresh_count,
            "attention_count": self.attention_count,
            "decisions": [decision.as_dict() for decision in self.decisions],
        }


def plan_opening_evidence_reverification(
    packet_dir: Path,
    *,
    max_age_minutes: int = 24 * 60,
    now: datetime | None = None,
) -> OpeningEvidenceFreshness:
    """Classify one packet receipt without mutating it or contacting the opening source."""
    if max_age_minutes <= 0:
        raise ValueError("max_age_minutes must be positive")
    receipt = _read_receipt(packet_dir)
    application_id = packet_dir.name
    if receipt is None:
        return OpeningEvidenceFreshness(
            application_id=application_id,
            opening_id=None,
            opening_digest=None,
            state="source_observation_required",
            source_evidence_observed_at=None,
            age_minutes=None,
            action="bind_opening_source_observation",
            continuation=(
                "acquire_opening_source_evidence",
                "compile_freshness_aware_batch_with_observed_timestamp",
            ),
        )
    opening_id = str(receipt.get("opening_id")) if receipt.get("opening_id") else None
    opening_digest = (
        str(receipt.get("opening_digest")) if receipt.get("opening_digest") else None
    )
    observed_raw = receipt.get("source_evidence_observed_at")
    if not isinstance(observed_raw, str) or not observed_raw.strip():
        return OpeningEvidenceFreshness(
            application_id=application_id,
            opening_id=opening_id,
            opening_digest=opening_digest,
            state="source_observation_required",
            source_evidence_observed_at=None,
            age_minutes=None,
            action="record_upstream_source_observation",
            continuation=(
                "recheck_opening_source",
                "compile_freshness_aware_batch_with_observed_timestamp",
            ),
        )
    try:
        observed = _parse_timestamp(observed_raw)
    except ValueError:
        return OpeningEvidenceFreshness(
            application_id=application_id,
            opening_id=opening_id,
            opening_digest=opening_digest,
            state="invalid_source_observation",
            source_evidence_observed_at=observed_raw,
            age_minutes=None,
            action="correct_source_observation_timestamp",
            continuation=(
                "validate_upstream_observed_timestamp",
                "recompile_packet_with_verified_evidence",
            ),
        )
    clock = (now or datetime.now(UTC)).astimezone(UTC)
    age_minutes = max(0, int((clock - observed).total_seconds() // 60))
    if observed > clock:
        state = "invalid_source_observation"
        action = "correct_future_source_observation"
        continuation = (
            "validate_upstream_observed_timestamp",
            "recompile_packet_with_verified_evidence",
        )
    elif age_minutes > max_age_minutes:
        state = "stale"
        action = "reverify_opening_source"
        continuation = (
            "refresh_opening_source",
            "compare_opening_digest",
            "compile_freshness_aware_batch_with_observed_timestamp",
        )
    elif age_minutes > max_age_minutes // 2:
        state = "aging"
        action = "schedule_opening_reverification"
        continuation = (
            "recheck_opening_source_before_submission",
            "record_observed_timestamp",
        )
    else:
        state = "fresh"
        action = "retain_current_packet_evidence"
        continuation = ()
    return OpeningEvidenceFreshness(
        application_id=application_id,
        opening_id=opening_id,
        opening_digest=opening_digest,
        state=state,
        source_evidence_observed_at=observed.isoformat().replace("+00:00", "Z"),
        age_minutes=age_minutes,
        action=action,
        continuation=continuation,
    )


def census_opening_evidence_freshness(
    output_dir: Path,
    *,
    max_age_minutes: int = 24 * 60,
    now: datetime | None = None,
) -> OpeningEvidenceFreshnessCensus:
    """Build a non-mutating evidence-freshness census for active packet directories."""
    packet_dirs = (
        ()
        if not output_dir.is_dir()
        else tuple(
            path
            for path in sorted(output_dir.iterdir())
            if path.is_dir() and path.name != ".stale"
        )
    )
    decisions = tuple(
        plan_opening_evidence_reverification(
            path,
            max_age_minutes=max_age_minutes,
            now=now,
        )
        for path in packet_dirs
    )
    return OpeningEvidenceFreshnessCensus(
        schema="glaciereq.opening-evidence-freshness.v1",
        max_age_minutes=max_age_minutes,
        packet_count=len(decisions),
        fresh_count=sum(decision.state == "fresh" for decision in decisions),
        attention_count=sum(decision.state != "fresh" for decision in decisions),
        decisions=decisions,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-opening-evidence-freshness",
        description=(
            "Plan recruiter-packet opening-evidence re-verification without "
            "mutating packets or contacting sources."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-age-minutes", type=int, default=24 * 60)
    parser.add_argument(
        "--now",
        help="Optional ISO-8601 UTC evaluation timestamp for deterministic review",
    )
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    now = _parse_timestamp(args.now) if args.now else None
    result = census_opening_evidence_freshness(
        args.output_dir,
        max_age_minutes=args.max_age_minutes,
        now=now,
    )
    rendered = json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.attention_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
