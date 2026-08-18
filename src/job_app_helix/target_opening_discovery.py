"""Discover and maintain target-company opening inventories from public ATS APIs.

This module closes the upstream gap before Opening Watch: callers describe target companies
once, Helix discovers their current Greenhouse or Lever inventories, normalizes provider
records into JobOpening objects, persists deterministic inventory deltas, then hands the live
set directly to the existing field-sensitive Opening Watch runtime.
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
SUPPORTED_PROVIDERS = frozenset({"greenhouse", "lever"})


@dataclass(frozen=True)
class TargetOpeningSource:
    company: str
    provider: str
    board_key: str
    include_title_terms: tuple[str, ...] = ()
    exclude_title_terms: tuple[str, ...] = ()
    include_locations: tuple[str, ...] = ()
    max_openings: int | None = None

    def __post_init__(self) -> None:
        if not self.company.strip():
            raise ValueError("target opening source requires company")
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported target opening provider: {self.provider}")
        if not self.board_key.strip():
            raise ValueError("target opening source requires board_key")
        if self.max_openings is not None and self.max_openings <= 0:
            raise ValueError("max_openings must be positive when supplied")

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SourceDiscoveryResult:
    company: str
    provider: str
    board_key: str
    openings: tuple[JobOpening, ...]
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "company": self.company,
            "provider": self.provider,
            "board_key": self.board_key,
            "openings": [opening.as_dict() for opening in self.openings],
            "error": self.error,
        }


@dataclass(frozen=True)
class InventoryDelta:
    added_urls: tuple[str, ...]
    removed_urls: tuple[str, ...]
    retained_urls: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TargetOpeningDiscoveryResult:
    schema: str
    source_count: int
    successful_source_count: int
    failed_source_count: int
    opening_count: int
    sources: tuple[SourceDiscoveryResult, ...]
    delta: InventoryDelta
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
            "delta": self.delta.as_dict(),
            "watch": self.watch.as_dict() if self.watch is not None else None,
            "receipt_sha256": self.receipt_sha256,
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
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


def _matches(source: TargetOpeningSource, title: str, location: str) -> bool:
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


def _greenhouse_openings(
    source: TargetOpeningSource,
    transport: JsonTransport,
) -> tuple[JobOpening, ...]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{source.board_key}/jobs?content=true"
    payload = transport(url)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Greenhouse response requires jobs list")
    openings: list[JobOpening] = []
    for row in payload["jobs"]:
        if not isinstance(row, Mapping):
            continue
        location_value = row.get("location")
        location = (
            str(location_value.get("name") or "").strip()
            if isinstance(location_value, Mapping)
            else str(location_value or "").strip()
        )
        title = str(row.get("title") or "").strip()
        absolute_url = str(row.get("absolute_url") or "").strip()
        content = str(row.get("content") or "").strip()
        if not title or not absolute_url or not content or not _matches(source, title, location):
            continue
        openings.append(
            ingest_job_opening(
                {
                    "id": str(row.get("id") or absolute_url),
                    "company": source.company,
                    "title": title,
                    "description": content,
                    "location": location,
                    "metadata": {
                        "provider": "greenhouse",
                        "board_key": source.board_key,
                        "provider_id": row.get("id"),
                        "updated_at": row.get("updated_at"),
                    },
                },
                source="greenhouse-api",
                source_url=absolute_url,
            )
        )
    return tuple(openings)


def _lever_description(row: Mapping[str, Any]) -> str:
    description = str(row.get("descriptionPlain") or row.get("description") or "").strip()
    if description:
        return description
    sections = row.get("lists")
    if not isinstance(sections, list):
        return ""
    values: list[str] = []
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        heading = str(section.get("text") or "").strip()
        content = str(section.get("content") or "").strip()
        if heading:
            values.append(heading)
        if content:
            values.append(content)
    return "\n".join(values).strip()


def _lever_openings(
    source: TargetOpeningSource,
    transport: JsonTransport,
) -> tuple[JobOpening, ...]:
    url = f"https://api.lever.co/v0/postings/{source.board_key}?mode=json"
    payload = transport(url)
    if not isinstance(payload, list):
        raise ValueError("Lever response requires a postings list")
    openings: list[JobOpening] = []
    for row in payload:
        if not isinstance(row, Mapping):
            continue
        categories = row.get("categories")
        location = (
            str(categories.get("location") or "").strip()
            if isinstance(categories, Mapping)
            else ""
        )
        title = str(row.get("text") or row.get("title") or "").strip()
        hosted_url = str(row.get("hostedUrl") or row.get("applyUrl") or "").strip()
        description = _lever_description(row)
        if not title or not hosted_url or not description or not _matches(source, title, location):
            continue
        openings.append(
            ingest_job_opening(
                {
                    "id": str(row.get("id") or hosted_url),
                    "company": source.company,
                    "title": title,
                    "description": description,
                    "location": location,
                    "metadata": {
                        "provider": "lever",
                        "board_key": source.board_key,
                        "provider_id": row.get("id"),
                        "workplace_type": row.get("workplaceType"),
                    },
                },
                source="lever-api",
                source_url=hosted_url,
            )
        )
    return tuple(openings)


def discover_source(
    source: TargetOpeningSource,
    *,
    transport: JsonTransport = _fetch_json,
) -> tuple[JobOpening, ...]:
    if source.provider == "greenhouse":
        openings = _greenhouse_openings(source, transport)
    else:
        openings = _lever_openings(source, transport)
    ordered = tuple(
        sorted(openings, key=lambda row: (row.title.casefold(), row.source_url or ""))
    )
    if source.max_openings is not None:
        return ordered[: source.max_openings]
    return ordered


def _load_previous_urls(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("existing target opening inventory must be an object")
    rows = payload.get("openings")
    if not isinstance(rows, list):
        raise ValueError("existing target opening inventory requires openings list")
    return {
        str(row.get("source_url"))
        for row in rows
        if isinstance(row, Mapping) and row.get("source_url")
    }


def execute_target_opening_discovery(
    sources: Sequence[TargetOpeningSource],
    *,
    state_dir: Path,
    transport: JsonTransport = _fetch_json,
    continue_on_source_error: bool = True,
    run_watch: bool = True,
) -> TargetOpeningDiscoveryResult:
    """Discover live company inventories and optionally run Opening Watch over the result."""
    if not sources:
        raise ValueError("target opening discovery requires at least one source")
    identities = [(source.provider, source.board_key) for source in sources]
    if len(identities) != len(set(identities)):
        raise ValueError("target opening discovery sources must be unique by provider/board_key")

    source_results: list[SourceDiscoveryResult] = []
    all_openings: list[JobOpening] = []
    for source in sources:
        try:
            openings = discover_source(source, transport=transport)
        except Exception as exc:
            if not continue_on_source_error:
                raise
            source_results.append(
                SourceDiscoveryResult(
                    company=source.company,
                    provider=source.provider,
                    board_key=source.board_key,
                    openings=(),
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        source_results.append(
            SourceDiscoveryResult(
                company=source.company,
                provider=source.provider,
                board_key=source.board_key,
                openings=openings,
            )
        )
        all_openings.extend(openings)

    by_url: dict[str, JobOpening] = {}
    for opening in all_openings:
        if not opening.source_url:
            raise ValueError(f"discovered opening has no source_url: {opening.opening_id}")
        if opening.source_url in by_url:
            raise ValueError(f"duplicate discovered opening URL: {opening.source_url}")
        by_url[opening.source_url] = opening

    inventory_path = state_dir / "TARGET_OPENING_INVENTORY.json"
    previous_urls = _load_previous_urls(inventory_path)
    current_urls = set(by_url)
    delta = InventoryDelta(
        added_urls=tuple(sorted(current_urls - previous_urls)),
        removed_urls=tuple(sorted(previous_urls - current_urls)),
        retained_urls=tuple(sorted(current_urls & previous_urls)),
    )
    ordered_openings = tuple(
        sorted(
            by_url.values(),
            key=lambda row: (
                row.company.casefold(),
                row.title.casefold(),
                row.source_url or "",
            ),
        )
    )
    _write_json(
        inventory_path,
        {
            "schema": "glaciereq.target-opening-inventory.v1",
            "openings": [opening.as_dict() for opening in ordered_openings],
            "delta": delta.as_dict(),
        },
    )

    watch: OpeningWatchResult | None = None
    if run_watch and ordered_openings:
        cached = {
            opening.source_url: opening
            for opening in ordered_openings
            if opening.source_url
        }

        def cached_fetcher(url: str) -> JobOpening:
            try:
                return cached[url]
            except KeyError as exc:
                raise ValueError(f"opening URL was not discovered in this cycle: {url}") from exc

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
        "schema": "glaciereq.target-opening-discovery.v1",
        "source_count": len(sources),
        "successful_source_count": successful_sources,
        "failed_source_count": len(sources) - successful_sources,
        "opening_count": len(ordered_openings),
        "sources": [result.as_dict() for result in source_results],
        "delta": delta.as_dict(),
        "watch": watch.as_dict() if watch is not None else None,
    }
    receipt_sha = _canonical_sha256(base)
    result = TargetOpeningDiscoveryResult(
        schema=str(base["schema"]),
        source_count=len(sources),
        successful_source_count=successful_sources,
        failed_source_count=len(sources) - successful_sources,
        opening_count=len(ordered_openings),
        sources=tuple(source_results),
        delta=delta,
        watch=watch,
        receipt_sha256=receipt_sha,
    )
    _write_json(state_dir / "TARGET_OPENING_DISCOVERY_RECEIPT.json", result.as_dict())
    return result


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return tuple(str(item).strip() for item in value if str(item).strip())


def load_sources(path: Path) -> tuple[TargetOpeningSource, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or not isinstance(payload.get("sources"), list):
        raise ValueError("target opening discovery manifest requires sources list")
    sources: list[TargetOpeningSource] = []
    for index, row in enumerate(payload["sources"]):
        if not isinstance(row, Mapping):
            raise ValueError(f"sources[{index}] must be an object")
        sources.append(
            TargetOpeningSource(
                company=str(row.get("company") or ""),
                provider=str(row.get("provider") or ""),
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
                    int(row["max_openings"])
                    if row.get("max_openings") is not None
                    else None
                ),
            )
        )
    return tuple(sources)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-discover-openings",
        description=(
            "Discover maintained Greenhouse/Lever target-company inventories and feed the "
            "normalized live set directly into Opening Watch."
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--inventory-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = execute_target_opening_discovery(
        load_sources(args.manifest),
        state_dir=args.state_dir,
        continue_on_source_error=not args.fail_fast,
        run_watch=not args.inventory_only,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.successful_source_count and result.opening_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
