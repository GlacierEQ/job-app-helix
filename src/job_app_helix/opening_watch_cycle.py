"""Drive application intelligence only for live openings that materially changed.

The opening watch owns cheap change detection across the full URL set. Only NEW or CHANGED
openings enter the expensive company-intelligence, calibration, ranking, and recruiter-packet
cycle. UNCHANGED openings stay on the zero-mutation fast path. The fetch cache guarantees
that a selected opening is not fetched twice in one watch/cycle execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .application_operations import ApplicationStore, CandidateProfile, JobOpening, load_candidate_profile
from .batch_application_execution import DEFAULT_ACTIONABLE_LANES
from .company_intelligence_acquisition import Transport, fetch_http_source
from .intelligence_cycle import (
    IntelligenceCycleCandidate,
    IntelligenceCycleResult,
    execute_intelligence_cycle,
    load_cycle_manifest,
)
from .opening_acquisition import OpeningFetcher
from .opening_watch import OpeningWatchResult, OpeningWatchTarget, execute_opening_watch
from .outcome_calibration import OutcomeCalibration

MATERIAL_OPENING_STATES = frozenset({"NEW", "CHANGED"})


@dataclass(frozen=True)
class OpeningWatchCycleResult:
    schema: str
    watch: OpeningWatchResult
    selected_urls: tuple[str, ...]
    unchanged_urls: tuple[str, ...]
    failed_urls: tuple[str, ...]
    cycle: IntelligenceCycleResult | None
    receipt_sha256: str

    @property
    def selected_count(self) -> int:
        return len(self.selected_urls)

    @property
    def unchanged_count(self) -> int:
        return len(self.unchanged_urls)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "watch": self.watch.as_dict(),
            "selected_urls": list(self.selected_urls),
            "unchanged_urls": list(self.unchanged_urls),
            "failed_urls": list(self.failed_urls),
            "cycle": self.cycle.as_dict() if self.cycle is not None else None,
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


def _validate_live_candidates(
    candidates: Sequence[IntelligenceCycleCandidate],
) -> dict[str, IntelligenceCycleCandidate]:
    if not candidates:
        raise ValueError("opening watch cycle requires at least one candidate")
    by_url: dict[str, IntelligenceCycleCandidate] = {}
    for candidate in candidates:
        if candidate.opening_url is None:
            raise ValueError("opening watch cycle accepts live opening_url candidates only")
        if candidate.opening_url in by_url:
            raise ValueError(f"duplicate opening URL: {candidate.opening_url}")
        by_url[candidate.opening_url] = candidate
    return by_url


def execute_opening_watch_cycle(
    candidates: Sequence[IntelligenceCycleCandidate],
    profile: CandidateProfile,
    *,
    state_dir: Path,
    output_dir: Path,
    store: ApplicationStore,
    opening_fetcher: OpeningFetcher,
    transport: Transport = fetch_http_source,
    actionable_lanes: Sequence[str] = DEFAULT_ACTIONABLE_LANES,
    limit: int | None = None,
    calibration: OutcomeCalibration | None = None,
    continue_on_error: bool = True,
) -> OpeningWatchCycleResult:
    """Refresh every opening, then execute full intelligence only for material changes."""
    by_url = _validate_live_candidates(candidates)
    fetched: dict[str, JobOpening] = {}

    def cached_fetcher(url: str) -> JobOpening:
        opening = fetched.get(url)
        if opening is None:
            opening = opening_fetcher(url)
            fetched[url] = opening
        return opening

    watch = execute_opening_watch(
        tuple(OpeningWatchTarget(url=url, label=candidate.company) for url, candidate in by_url.items()),
        state_dir=state_dir / "opening-watch",
        fetcher=cached_fetcher,
        continue_on_error=continue_on_error,
    )

    selected_urls = tuple(
        item.url for item in watch.items if item.status in MATERIAL_OPENING_STATES
    )
    unchanged_urls = tuple(item.url for item in watch.items if item.status == "UNCHANGED")
    failed_urls = tuple(item.url for item in watch.items if item.error is not None)
    selected = tuple(by_url[url] for url in selected_urls)

    cycle = None
    if selected:
        cycle = execute_intelligence_cycle(
            selected,
            profile,
            output_dir=output_dir,
            state_dir=state_dir,
            store=store,
            transport=transport,
            opening_fetcher=cached_fetcher,
            actionable_lanes=actionable_lanes,
            limit=limit,
            calibration=calibration,
            continue_on_company_error=continue_on_error,
        )

    base: dict[str, object] = {
        "schema": "glaciereq.opening-watch-cycle.v1",
        "watch_receipt_sha256": watch.receipt_sha256,
        "selected_urls": list(selected_urls),
        "unchanged_urls": list(unchanged_urls),
        "failed_urls": list(failed_urls),
        "cycle_receipt_sha256": cycle.receipt_sha256 if cycle is not None else None,
    }
    receipt_sha = _sha256(base)
    result = OpeningWatchCycleResult(
        schema=str(base["schema"]),
        watch=watch,
        selected_urls=selected_urls,
        unchanged_urls=unchanged_urls,
        failed_urls=failed_urls,
        cycle=cycle,
        receipt_sha256=receipt_sha,
    )
    _write_json(state_dir / "OPENING_WATCH_CYCLE_RECEIPT.json", result.as_dict())
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-watch-cycle",
        description=(
            "Refresh live openings and run company/ranking/packet intelligence only for "
            "NEW or CHANGED postings."
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
    from .application_operations import ingest_job_opening_url

    args = _parser().parse_args(argv)
    candidates = load_cycle_manifest(args.manifest)
    profile = load_candidate_profile(args.profile)
    lanes = tuple(args.lane) if args.lane else DEFAULT_ACTIONABLE_LANES
    with ApplicationStore(args.database) as store:
        result = execute_opening_watch_cycle(
            candidates,
            profile,
            state_dir=args.state_dir,
            output_dir=args.output_dir,
            store=store,
            opening_fetcher=ingest_job_opening_url,
            actionable_lanes=lanes,
            limit=args.limit,
            continue_on_error=not args.fail_fast,
        )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    if result.failed_urls and not result.selected_urls and not result.unchanged_urls:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
