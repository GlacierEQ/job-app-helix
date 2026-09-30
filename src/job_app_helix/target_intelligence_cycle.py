"""Run target-company discovery through the full job-intelligence pipeline.

This is the vertical composition layer above target_opening_discovery. A target company is
configured once with its ATS source and company-intelligence acquisition plan. Each run
refreshes the attributable ATS inventory, preserves inventory/watch history, and sends only
NEW or recruiter-material openings through company intelligence, ranking, freshness-aware
packet lineage, and recruiter-packet generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .application_operations import (
    ApplicationStore,
    CandidateProfile,
    JobOpening,
    load_candidate_profile,
)
from .batch_application_execution import DEFAULT_ACTIONABLE_LANES
from .company_intelligence_acquisition import Transport, fetch_http_source
from .intelligence_cycle import IntelligenceCycleCandidate
from .opening_watch_cycle import OpeningWatchCycleResult, execute_opening_watch_cycle
from .outcome_calibration import OutcomeCalibration
from .target_opening_discovery import (
    JsonTransport,
    TargetOpeningDiscoveryResult,
    TargetOpeningSource,
    _fetch_json,
    execute_target_opening_discovery,
)


@dataclass(frozen=True)
class TargetIntelligenceSource:
    discovery: TargetOpeningSource
    acquisition_plan_path: Path
    current_intelligence_path: Path | None = None
    role: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "discovery": self.discovery.as_dict(),
            "acquisition_plan_path": str(self.acquisition_plan_path),
            "current_intelligence_path": (
                str(self.current_intelligence_path)
                if self.current_intelligence_path is not None
                else None
            ),
            "role": self.role,
        }


@dataclass(frozen=True)
class TargetIntelligenceCycleResult:
    schema: str
    discovery: TargetOpeningDiscoveryResult
    candidate_count: int
    watch_cycle: OpeningWatchCycleResult | None
    receipt_sha256: str

    @property
    def selected_count(self) -> int:
        return self.watch_cycle.selected_count if self.watch_cycle is not None else 0

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "discovery": self.discovery.as_dict(),
            "candidate_count": self.candidate_count,
            "watch_cycle": self.watch_cycle.as_dict() if self.watch_cycle is not None else None,
            "receipt_sha256": self.receipt_sha256,
        }


def _sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _validate_targets(
    targets: Sequence[TargetIntelligenceSource],
) -> dict[tuple[str, str], TargetIntelligenceSource]:
    if not targets:
        raise ValueError("target intelligence cycle requires at least one target")
    by_identity: dict[tuple[str, str], TargetIntelligenceSource] = {}
    for target in targets:
        identity = (target.discovery.provider, target.discovery.board_key)
        if identity in by_identity:
            raise ValueError(
                "target intelligence sources must be unique by provider/board_key: "
                f"{identity[0]}/{identity[1]}"
            )
        by_identity[identity] = target
    return by_identity


def _candidate_for_opening(
    target: TargetIntelligenceSource,
    opening: JobOpening,
) -> IntelligenceCycleCandidate:
    if opening.company.casefold() != target.discovery.company.casefold():
        raise ValueError(
            "discovered opening company does not match target configuration: "
            f"{opening.company!r} != {target.discovery.company!r}"
        )
    if not opening.source_url:
        raise ValueError(f"discovered opening has no source_url: {opening.opening_id}")
    return IntelligenceCycleCandidate(
        company=target.discovery.company,
        acquisition_plan_path=target.acquisition_plan_path,
        opening_url=opening.source_url,
        current_intelligence_path=target.current_intelligence_path,
        role=target.role,
    )


def execute_target_intelligence_cycle(
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
) -> TargetIntelligenceCycleResult:
    """Discover live openings and advance material changes through full intelligence."""
    by_identity = _validate_targets(targets)
    discovery = execute_target_opening_discovery(
        tuple(target.discovery for target in targets),
        state_dir=state_dir,
        transport=discovery_transport,
        continue_on_source_error=continue_on_error,
        run_watch=False,
    )

    candidates: list[IntelligenceCycleCandidate] = []
    opening_cache: dict[str, JobOpening] = {}
    for source_result in discovery.sources:
        identity = (source_result.provider, source_result.board_key)
        target = by_identity[identity]
        for opening in source_result.openings:
            candidate = _candidate_for_opening(target, opening)
            url = candidate.opening_url
            if url is None:
                raise AssertionError("live discovered candidate unexpectedly lacks opening_url")
            if url in opening_cache:
                raise ValueError(f"duplicate discovered opening URL across target sources: {url}")
            opening_cache[url] = opening
            candidates.append(candidate)

    def discovered_fetcher(url: str) -> JobOpening:
        try:
            return opening_cache[url]
        except KeyError as exc:
            raise ValueError(f"opening URL was not discovered in this cycle: {url}") from exc

    watch_cycle: OpeningWatchCycleResult | None = None
    if candidates:
        watch_cycle = execute_opening_watch_cycle(
            tuple(candidates),
            profile,
            state_dir=state_dir,
            output_dir=output_dir,
            store=store,
            opening_fetcher=discovered_fetcher,
            transport=intelligence_transport,
            actionable_lanes=actionable_lanes,
            limit=limit,
            calibration=calibration,
            continue_on_error=continue_on_error,
        )

    base: dict[str, object] = {
        "schema": "glaciereq.target-intelligence-cycle.v1",
        "discovery_receipt_sha256": discovery.receipt_sha256,
        "candidate_count": len(candidates),
        "watch_cycle_receipt_sha256": (
            watch_cycle.receipt_sha256 if watch_cycle is not None else None
        ),
        "selected_count": watch_cycle.selected_count if watch_cycle is not None else 0,
    }
    receipt_sha = _sha256(base)
    result = TargetIntelligenceCycleResult(
        schema=str(base["schema"]),
        discovery=discovery,
        candidate_count=len(candidates),
        watch_cycle=watch_cycle,
        receipt_sha256=receipt_sha,
    )
    _write_json(state_dir / "TARGET_INTELLIGENCE_CYCLE_RECEIPT.json", result.as_dict())
    return result


def _strings(value: object, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return tuple(str(item).strip() for item in value if str(item).strip())


def load_target_intelligence_manifest(path: Path) -> tuple[TargetIntelligenceSource, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or not isinstance(payload.get("sources"), list):
        raise ValueError("target intelligence manifest requires sources list")
    root = path.parent
    targets: list[TargetIntelligenceSource] = []
    for index, row in enumerate(payload["sources"]):
        if not isinstance(row, Mapping):
            raise ValueError(f"sources[{index}] must be an object")
        acquisition_plan = str(row.get("acquisition_plan") or "").strip()
        if not acquisition_plan:
            raise ValueError(f"sources[{index}] requires acquisition_plan")
        current = str(row.get("current_intelligence") or "").strip()
        role = str(row.get("role") or "").strip()
        max_openings_value = row.get("max_openings")
        max_openings = int(max_openings_value) if max_openings_value is not None else None
        targets.append(
            TargetIntelligenceSource(
                discovery=TargetOpeningSource(
                    company=str(row.get("company") or ""),
                    provider=str(row.get("provider") or ""),
                    board_key=str(row.get("board_key") or ""),
                    include_title_terms=_strings(
                        row.get("include_title_terms"),
                        field=f"sources[{index}].include_title_terms",
                    ),
                    exclude_title_terms=_strings(
                        row.get("exclude_title_terms"),
                        field=f"sources[{index}].exclude_title_terms",
                    ),
                    include_locations=_strings(
                        row.get("include_locations"),
                        field=f"sources[{index}].include_locations",
                    ),
                    max_openings=max_openings,
                ),
                acquisition_plan_path=root / acquisition_plan,
                current_intelligence_path=root / current if current else None,
                role=role or None,
            )
        )
    _validate_targets(targets)
    return tuple(targets)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-target-cycle",
        description=(
            "Discover target-company ATS inventories and run new or recruiter-material "
            "openings through company intelligence, ranking, and recruiter packet generation."
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
        result = execute_target_intelligence_cycle(
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
    if result.discovery.failed_source_count and not result.candidate_count:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
