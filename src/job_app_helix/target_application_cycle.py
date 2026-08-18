"""Promote the strongest complete target-company packet into an application-ready release.

The target intelligence cycle already owns live ATS discovery, material-change gating,
company intelligence, ranking, and recruiter-packet compilation. This module closes the
last internal execution gap: it verifies the recruiter-facing packet on disk, binds every
required artifact to an integrity digest, and publishes one deterministic release pointer
for the strongest complete application. It never submits an application or contacts an
employer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .application_operations import ApplicationStore, CandidateProfile, load_candidate_profile
from .batch_application_execution import DEFAULT_ACTIONABLE_LANES
from .company_intelligence_acquisition import Transport, fetch_http_source
from .outcome_calibration import OutcomeCalibration
from .target_intelligence_cycle import (
    TargetIntelligenceCycleResult,
    TargetIntelligenceSource,
    execute_target_intelligence_cycle,
    load_target_intelligence_manifest,
)
from .target_opening_discovery import JsonTransport, _fetch_json

REQUIRED_APPLICATION_ARTIFACTS = (
    "RESUME.md",
    "COVER_LETTER.md",
    "OUTREACH.md",
    "PROJECTION_RECEIPT.json",
    "OPPORTUNITY_ASSESSMENT.json",
    "STRATEGY_RECEIPT.json",
    "PRIORITY_RECEIPT.json",
    "OPENING_INPUT_RECEIPT.json",
    "submission/SUBMISSION_PACKET.json",
)


class ApplicationReadinessError(RuntimeError):
    """Raised when no recruiter packet can satisfy the application-ready contract."""


@dataclass(frozen=True)
class ApplicationReadyCandidate:
    application_id: str
    opening_id: str
    company_id: str
    lane: str
    queue_rank: int
    priority_score: float
    packet_dir: str
    opening_digest: str | None
    artifact_sha256: Mapping[str, str]
    artifact_bytes: Mapping[str, int]
    bundle_sha256: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ApplicationReadyRelease:
    schema: str
    target_cycle_receipt_sha256: str
    selected: ApplicationReadyCandidate
    rejected_higher_priority_packets: tuple[Mapping[str, object], ...]
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "target_cycle_receipt_sha256": self.target_cycle_receipt_sha256,
            "selected": self.selected.as_dict(),
            "rejected_higher_priority_packets": [
                dict(row) for row in self.rejected_higher_priority_packets
            ],
            "receipt_sha256": self.receipt_sha256,
        }


@dataclass(frozen=True)
class TargetApplicationCycleResult:
    schema: str
    target_cycle: TargetIntelligenceCycleResult
    application_ready: ApplicationReadyRelease | None
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "target_cycle": self.target_cycle.as_dict(),
            "application_ready": (
                self.application_ready.as_dict() if self.application_ready is not None else None
            ),
            "receipt_sha256": self.receipt_sha256,
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_object(path: Path, *, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationReadinessError(f"invalid {label} at {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ApplicationReadinessError(f"{label} must be a JSON object: {path}")
    return value


def _required_string(value: Mapping[str, object], field: str, *, path: Path) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise ApplicationReadinessError(f"{path} requires non-empty {field}")
    return result.strip()


def _inspect_packet(packet_dir: Path) -> ApplicationReadyCandidate:
    missing = [
        relative
        for relative in REQUIRED_APPLICATION_ARTIFACTS
        if not (packet_dir / relative).is_file()
    ]
    if missing:
        raise ApplicationReadinessError(
            f"packet {packet_dir.name} is incomplete; missing {', '.join(missing)}"
        )

    priority_path = packet_dir / "PRIORITY_RECEIPT.json"
    opening_path = packet_dir / "OPENING_INPUT_RECEIPT.json"
    priority = _read_object(priority_path, label="priority receipt")
    opening = _read_object(opening_path, label="opening input receipt")

    application_id = _required_string(priority, "application_id", path=priority_path)
    if application_id != packet_dir.name:
        raise ApplicationReadinessError(
            f"packet directory identity drift: {packet_dir.name} != {application_id}"
        )
    opening_id = _required_string(priority, "opening_id", path=priority_path)
    company_id = _required_string(priority, "company_id", path=priority_path)
    lane = _required_string(priority, "lane", path=priority_path)
    if lane not in DEFAULT_ACTIONABLE_LANES:
        raise ApplicationReadinessError(
            f"packet {application_id} is not application-ready; lane={lane}"
        )

    queue_rank = priority.get("queue_rank")
    priority_score = priority.get("priority_score")
    if not isinstance(queue_rank, int) or queue_rank <= 0:
        raise ApplicationReadinessError(f"{priority_path} has invalid queue_rank")
    if not isinstance(priority_score, (int, float)):
        raise ApplicationReadinessError(f"{priority_path} has invalid priority_score")

    opening_receipt_id = _required_string(opening, "opening_id", path=opening_path)
    if opening_receipt_id != opening_id:
        raise ApplicationReadinessError(
            f"opening receipt identity drift: {opening_receipt_id} != {opening_id}"
        )
    opening_digest_value = opening.get("opening_digest")
    opening_digest = (
        opening_digest_value.strip()
        if isinstance(opening_digest_value, str) and opening_digest_value.strip()
        else None
    )

    artifact_sha256: dict[str, str] = {}
    artifact_bytes: dict[str, int] = {}
    for relative in REQUIRED_APPLICATION_ARTIFACTS:
        artifact = packet_dir / relative
        artifact_sha256[relative] = _file_sha256(artifact)
        artifact_bytes[relative] = artifact.stat().st_size

    bundle_sha = _canonical_sha256(
        {
            "application_id": application_id,
            "opening_id": opening_id,
            "company_id": company_id,
            "artifact_sha256": artifact_sha256,
        }
    )
    return ApplicationReadyCandidate(
        application_id=application_id,
        opening_id=opening_id,
        company_id=company_id,
        lane=lane,
        queue_rank=queue_rank,
        priority_score=float(priority_score),
        packet_dir=str(packet_dir),
        opening_digest=opening_digest,
        artifact_sha256=artifact_sha256,
        artifact_bytes=artifact_bytes,
        bundle_sha256=bundle_sha,
    )


def _candidate_directories(output_dir: Path) -> tuple[Path, ...]:
    if not output_dir.is_dir():
        return ()
    return tuple(
        sorted(
            (
                path
                for path in output_dir.iterdir()
                if path.is_dir() and not path.name.startswith(".")
            ),
            key=lambda path: path.name.casefold(),
        )
    )


def promote_strongest_application_ready_packet(
    output_dir: Path,
    *,
    target_cycle_receipt_sha256: str,
    release_path: Path,
) -> ApplicationReadyRelease:
    """Verify packet artifacts and publish the strongest complete actionable release.

    Higher-ranked incomplete packets are never silently treated as ready. They remain in
    the release receipt as rejected candidates so a damaged top packet cannot disappear
    behind a lower-ranked fallback.
    """
    inspected: list[ApplicationReadyCandidate] = []
    rejected: list[dict[str, object]] = []
    for packet_dir in _candidate_directories(output_dir):
        try:
            inspected.append(_inspect_packet(packet_dir))
        except ApplicationReadinessError as exc:
            priority_path = packet_dir / "PRIORITY_RECEIPT.json"
            rank: int | None = None
            score: float | None = None
            if priority_path.is_file():
                try:
                    priority = _read_object(priority_path, label="priority receipt")
                    rank_value = priority.get("queue_rank")
                    score_value = priority.get("priority_score")
                    rank = rank_value if isinstance(rank_value, int) else None
                    score = float(score_value) if isinstance(score_value, (int, float)) else None
                except ApplicationReadinessError:
                    pass
            rejected.append(
                {
                    "packet_dir": str(packet_dir),
                    "queue_rank": rank,
                    "priority_score": score,
                    "reason": str(exc),
                }
            )

    if not inspected:
        reasons = "; ".join(str(row["reason"]) for row in rejected[:3])
        suffix = f": {reasons}" if reasons else ""
        raise ApplicationReadinessError(f"no complete actionable recruiter packet found{suffix}")

    inspected.sort(key=lambda row: (row.queue_rank, -row.priority_score, row.application_id))
    selected = inspected[0]
    higher_rejected = tuple(
        row
        for row in rejected
        if isinstance(row.get("queue_rank"), int) and int(row["queue_rank"]) < selected.queue_rank
    )
    base: dict[str, object] = {
        "schema": "glaciereq.application-ready-release.v1",
        "target_cycle_receipt_sha256": target_cycle_receipt_sha256,
        "selected": selected.as_dict(),
        "rejected_higher_priority_packets": [dict(row) for row in higher_rejected],
    }
    receipt_sha = _canonical_sha256(base)
    release = ApplicationReadyRelease(
        schema=str(base["schema"]),
        target_cycle_receipt_sha256=target_cycle_receipt_sha256,
        selected=selected,
        rejected_higher_priority_packets=higher_rejected,
        receipt_sha256=receipt_sha,
    )
    payload = release.as_dict()
    _write_json(release_path, payload)
    _write_json(Path(selected.packet_dir) / "APPLICATION_READY.json", payload)
    return release


def execute_target_application_cycle(
    targets: Sequence[TargetIntelligenceSource],
    profile: CandidateProfile,
    *,
    state_dir: Path,
    output_dir: Path,
    store: ApplicationStore,
    discovery_transport: JsonTransport = _fetch_json,
    intelligence_transport: Transport = fetch_http_source,
    actionable_lanes: Sequence[str] = DEFAULT_ACTIONABLE_LANES,
    limit: int | None = None,
    calibration: OutcomeCalibration | None = None,
    continue_on_error: bool = True,
) -> TargetApplicationCycleResult:
    """Run live target intelligence and promote the strongest complete application packet."""
    target_cycle = execute_target_intelligence_cycle(
        targets,
        profile,
        state_dir=state_dir,
        output_dir=output_dir,
        store=store,
        discovery_transport=discovery_transport,
        intelligence_transport=intelligence_transport,
        actionable_lanes=actionable_lanes,
        limit=limit,
        calibration=calibration,
        continue_on_error=continue_on_error,
    )

    release: ApplicationReadyRelease | None = None
    try:
        release = promote_strongest_application_ready_packet(
            output_dir,
            target_cycle_receipt_sha256=target_cycle.receipt_sha256,
            release_path=state_dir / "APPLICATION_READY_TARGET.json",
        )
    except ApplicationReadinessError:
        if target_cycle.candidate_count:
            raise

    base: dict[str, object] = {
        "schema": "glaciereq.target-application-cycle.v1",
        "target_cycle_receipt_sha256": target_cycle.receipt_sha256,
        "application_ready_receipt_sha256": release.receipt_sha256 if release else None,
    }
    receipt_sha = _canonical_sha256(base)
    result = TargetApplicationCycleResult(
        schema=str(base["schema"]),
        target_cycle=target_cycle,
        application_ready=release,
        receipt_sha256=receipt_sha,
    )
    _write_json(state_dir / "TARGET_APPLICATION_CYCLE_RECEIPT.json", result.as_dict())
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-target-application",
        description=(
            "Discover live target-company openings, run material candidates through Helix, "
            "and publish one integrity-checked application-ready recruiter packet."
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--lane", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    targets = load_target_intelligence_manifest(args.manifest)
    profile = load_candidate_profile(args.profile)
    lanes = tuple(args.lane) if args.lane else DEFAULT_ACTIONABLE_LANES
    with ApplicationStore(args.database) as store:
        result = execute_target_application_cycle(
            targets,
            profile,
            state_dir=args.state_dir,
            output_dir=args.output_dir,
            store=store,
            actionable_lanes=lanes,
            limit=args.limit,
            continue_on_error=not args.fail_fast,
        )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.application_ready is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
