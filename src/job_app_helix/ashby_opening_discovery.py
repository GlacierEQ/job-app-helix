"""Discover attributable Ashby job-board openings and feed them into Opening Watch.

Ashby exposes a public job-posting endpoint intended for custom careers pages. This runtime
normalizes listed postings into Helix JobOpening objects, preserves provider metadata useful
for recruiter/application intelligence, isolates broken boards, and composes the current live
set directly into the existing field-sensitive Opening Watch engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .application_operations import JobOpening, ingest_job_opening
from .opening_watch import OpeningWatchResult, OpeningWatchTarget, execute_opening_watch

JsonTransport = Callable[[str], Any]


@dataclass(frozen=True)
class AshbyOpeningSource:
    company: str
    board_key: str
    include_title_terms: tuple[str, ...] = ()
    exclude_title_terms: tuple[str, ...] = ()
    include_locations: tuple[str, ...] = ()
    max_openings: int | None = None
    include_compensation: bool = True

    def __post_init__(self) -> None:
        if not self.company.strip():
            raise ValueError("Ashby opening source requires company")
        if not self.board_key.strip():
            raise ValueError("Ashby opening source requires board_key")
        if self.max_openings is not None and self.max_openings <= 0:
            raise ValueError("max_openings must be positive when supplied")

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AshbySourceResult:
    company: str
    board_key: str
    openings: tuple[JobOpening, ...]
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "company": self.company,
            "board_key": self.board_key,
            "openings": [opening.as_dict() for opening in self.openings],
            "error": self.error,
        }


@dataclass(frozen=True)
class AshbyDiscoveryResult:
    schema: str
    source_count: int
    successful_source_count: int
    failed_source_count: int
    opening_count: int
    sources: tuple[AshbySourceResult, ...]
    watch: OpeningWatchResult | None
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_count": self.source_count,
            "successful_source_count": self.successful_source_count,
            "failed_source_count": self.failed_source_count,
            "opening_count": self.opening_count,
            "sources": [source.as_dict() for source in self.sources],
            "watch": self.watch.as_dict() if self.watch is not None else None,
            "receipt_sha256": self.receipt_sha256,
        }


def _reference_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "job-app-helix/0.3"},
    )
    with urllib.request.urlopen(request, timeout=20.0) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="replace"))


def _matches(source: AshbyOpeningSource, title: str, location: str) -> bool:
    normalized_title = title.casefold()
    normalized_location = location.casefold()
    if source.include_title_terms and not any(
        term.casefold() in normalized_title for term in source.include_title_terms
    ):
        return False
    if any(term.casefold() in normalized_title for term in source.exclude_title_terms):
        return False
    return not source.include_locations or any(
        term.casefold() in normalized_location for term in source.include_locations
    )


def _secondary_locations(row: Mapping[str, Any]) -> tuple[str, ...]:
    values = row.get("secondaryLocations")
    if not isinstance(values, list):
        return ()
    return tuple(
        str(value.get("location") or "").strip()
        for value in values
        if isinstance(value, Mapping) and str(value.get("location") or "").strip()
    )


def _compensation_summary(row: Mapping[str, Any]) -> str | None:
    compensation = row.get("compensation")
    if not isinstance(compensation, Mapping):
        return None
    value = compensation.get("compensationTierSummary") or compensation.get(
        "scrapeableCompensationSalarySummary"
    )
    rendered = str(value or "").strip()
    return rendered or None


def discover_ashby_openings(
    source: AshbyOpeningSource,
    *,
    transport: JsonTransport = _fetch_json,
) -> tuple[JobOpening, ...]:
    include_compensation = "true" if source.include_compensation else "false"
    url = (
        "https://api.ashbyhq.com/posting-api/job-board/"
        f"{source.board_key}?includeCompensation={include_compensation}"
    )
    payload = transport(url)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Ashby response requires jobs list")
    api_version = str(payload.get("apiVersion") or "").strip()
    if api_version and api_version != "1":
        raise ValueError(f"unsupported Ashby posting API version: {api_version}")

    openings: list[JobOpening] = []
    for row in payload["jobs"]:
        if not isinstance(row, Mapping) or row.get("isListed") is False:
            continue
        title = str(row.get("title") or "").strip()
        location = str(row.get("location") or "").strip()
        job_url = str(row.get("jobUrl") or "").strip()
        description = str(row.get("descriptionPlain") or "").strip()
        if not title or not job_url or not description or not _matches(source, title, location):
            continue
        openings.append(
            ingest_job_opening(
                {
                    "id": job_url,
                    "company": source.company,
                    "title": title,
                    "description": description,
                    "location": location,
                    "metadata": {
                        "provider": "ashby",
                        "board_key": source.board_key,
                        "apply_url": row.get("applyUrl"),
                        "published_at": row.get("publishedAt"),
                        "employment_type": row.get("employmentType"),
                        "workplace_type": row.get("workplaceType"),
                        "is_remote": row.get("isRemote"),
                        "department": row.get("department"),
                        "team": row.get("team"),
                        "secondary_locations": list(_secondary_locations(row)),
                        "compensation_summary": _compensation_summary(row),
                    },
                },
                source="ashby-public-api",
                source_url=job_url,
            )
        )
    ordered = tuple(
        sorted(openings, key=lambda opening: (opening.title.casefold(), opening.source_url or ""))
    )
    if source.max_openings is not None:
        return ordered[: source.max_openings]
    return ordered


def execute_ashby_opening_discovery(
    sources: Sequence[AshbyOpeningSource],
    *,
    state_dir: Path,
    transport: JsonTransport = _fetch_json,
    continue_on_source_error: bool = True,
    run_watch: bool = True,
) -> AshbyDiscoveryResult:
    """Discover Ashby boards and optionally advance the attributable live set through Watch."""
    if not sources:
        raise ValueError("Ashby opening discovery requires at least one source")
    board_keys = [source.board_key for source in sources]
    if len(board_keys) != len(set(board_keys)):
        raise ValueError("Ashby opening sources must be unique by board_key")

    source_results: list[AshbySourceResult] = []
    by_url: dict[str, JobOpening] = {}
    for source in sources:
        try:
            openings = discover_ashby_openings(source, transport=transport)
        except Exception as exc:
            if not continue_on_source_error:
                raise
            source_results.append(
                AshbySourceResult(
                    company=source.company,
                    board_key=source.board_key,
                    openings=(),
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        source_results.append(
            AshbySourceResult(
                company=source.company,
                board_key=source.board_key,
                openings=openings,
            )
        )
        for opening in openings:
            if not opening.source_url:
                raise ValueError(f"Ashby opening has no source_url: {opening.opening_id}")
            if opening.source_url in by_url:
                raise ValueError(f"duplicate Ashby opening URL: {opening.source_url}")
            by_url[opening.source_url] = opening

    ordered_openings = tuple(
        sorted(
            by_url.values(),
            key=lambda opening: (
                opening.company.casefold(),
                opening.title.casefold(),
                opening.source_url or "",
            ),
        )
    )
    watch: OpeningWatchResult | None = None
    if run_watch and ordered_openings:
        cached = {opening.source_url: opening for opening in ordered_openings if opening.source_url}

        def cached_fetcher(url: str) -> JobOpening:
            try:
                return cached[url]
            except KeyError as exc:
                raise ValueError(f"Ashby opening URL not discovered in this cycle: {url}") from exc

        watch = execute_opening_watch(
            tuple(
                OpeningWatchTarget(
                    url=opening.source_url or "",
                    label=f"{opening.company}: {opening.title}",
                )
                for opening in ordered_openings
            ),
            state_dir=state_dir / "opening-watch",
            fetcher=cached_fetcher,
            continue_on_error=True,
        )

    successful_sources = sum(result.error is None for result in source_results)
    base: dict[str, object] = {
        "schema": "glaciereq.ashby-opening-discovery.v1",
        "source_count": len(sources),
        "successful_source_count": successful_sources,
        "failed_source_count": len(sources) - successful_sources,
        "opening_count": len(ordered_openings),
        "sources": [result.as_dict() for result in source_results],
        "watch": watch.as_dict() if watch is not None else None,
    }
    receipt_sha = _reference_sha256(base)
    result = AshbyDiscoveryResult(
        schema=str(base["schema"]),
        source_count=len(sources),
        successful_source_count=successful_sources,
        failed_source_count=len(sources) - successful_sources,
        opening_count=len(ordered_openings),
        sources=tuple(source_results),
        watch=watch,
        receipt_sha256=receipt_sha,
    )
    _write_json(state_dir / "ASHBY_OPENING_DISCOVERY_RECEIPT.json", result.as_dict())
    return result


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return tuple(str(item).strip() for item in value if str(item).strip())


def load_sources(path: Path) -> tuple[AshbyOpeningSource, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or not isinstance(payload.get("sources"), list):
        raise ValueError("Ashby opening discovery manifest requires sources list")
    sources: list[AshbyOpeningSource] = []
    for index, row in enumerate(payload["sources"]):
        if not isinstance(row, Mapping):
            raise ValueError(f"sources[{index}] must be an object")
        sources.append(
            AshbyOpeningSource(
                company=str(row.get("company") or ""),
                board_key=str(row.get("board_key") or ""),
                include_title_terms=_string_tuple(
                    row.get("include_title_terms"),
                    field=f"sources[{index}].include_title_terms",
                ),
                exclude_title_terms=_string_tuple(
                    row.get("exclude_title_terms"),
                    field=f"sources[{index}].exclude_title_terms",
                ),
                include_locations=_string_tuple(
                    row.get("include_locations"),
                    field=f"sources[{index}].include_locations",
                ),
                max_openings=(
                    int(row["max_openings"]) if row.get("max_openings") is not None else None
                ),
                include_compensation=bool(row.get("include_compensation", True)),
            )
        )
    return tuple(sources)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m job_app_helix.ashby_opening_discovery",
        description="Discover attributable Ashby inventories and feed them into Opening Watch.",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--inventory-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = execute_ashby_opening_discovery(
        load_sources(args.manifest),
        state_dir=args.state_dir,
        continue_on_source_error=not args.fail_fast,
        run_watch=not args.inventory_only,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.successful_source_count and result.opening_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
