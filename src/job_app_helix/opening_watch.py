"""Continuously maintain a set of attributable live job openings.

The watch composes the proven single-opening acquisition contract into a batch runtime:
each URL owns an isolated content-addressed state directory, failures stay local to that
opening, and every run emits aggregate change telemetry plus an append-only event log.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .opening_acquisition import OpeningFetcher, acquire_live_opening


@dataclass(frozen=True)
class OpeningWatchTarget:
    url: str
    label: str | None = None


@dataclass(frozen=True)
class OpeningWatchItemResult:
    url: str
    label: str | None
    state_key: str
    status: str
    opening_id: str | None
    changed_fields: tuple[str, ...]
    receipt_sha256: str | None
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OpeningWatchResult:
    schema: str
    target_count: int
    successful_count: int
    failed_count: int
    new_count: int
    changed_count: int
    unchanged_count: int
    items: tuple[OpeningWatchItemResult, ...]
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "target_count": self.target_count,
            "successful_count": self.successful_count,
            "failed_count": self.failed_count,
            "new_count": self.new_count,
            "changed_count": self.changed_count,
            "unchanged_count": self.unchanged_count,
            "items": [item.as_dict() for item in self.items],
            "receipt_sha256": self.receipt_sha256,
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _state_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _append_event(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def execute_opening_watch(
    targets: Sequence[OpeningWatchTarget],
    *,
    state_dir: Path,
    fetcher: OpeningFetcher,
    continue_on_error: bool = True,
) -> OpeningWatchResult:
    """Refresh a live opening set and persist deterministic aggregate change telemetry."""
    if not targets:
        raise ValueError("opening watch requires at least one target")
    urls = [target.url for target in targets]
    if len(set(urls)) != len(urls):
        raise ValueError("opening watch targets must have unique URLs")

    items: list[OpeningWatchItemResult] = []
    for target in targets:
        if not target.url.startswith(("https://", "http://")):
            raise ValueError(f"opening watch URL must be http(s): {target.url!r}")
        key = _state_key(target.url)
        root = state_dir / "openings" / key
        try:
            acquisition = acquire_live_opening(
                target.url,
                snapshot_path=root / "OPENING_SNAPSHOT.json",
                receipt_path=root / "OPENING_ACQUISITION_RECEIPT.json",
                fetcher=fetcher,
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            item = OpeningWatchItemResult(
                url=target.url,
                label=target.label,
                state_key=key,
                status="FAILED_ISOLATED",
                opening_id=None,
                changed_fields=(),
                receipt_sha256=None,
                error=f"{type(exc).__name__}: {exc}",
            )
        else:
            item = OpeningWatchItemResult(
                url=target.url,
                label=target.label,
                state_key=key,
                status=acquisition.change.status,
                opening_id=acquisition.opening.opening_id,
                changed_fields=acquisition.change.changed_fields,
                receipt_sha256=acquisition.receipt_sha256,
            )
        items.append(item)
        _append_event(state_dir / "OPENING_CHANGE_EVENTS.jsonl", item.as_dict())

    counts = {
        "NEW": sum(item.status == "NEW" for item in items),
        "CHANGED": sum(item.status == "CHANGED" for item in items),
        "UNCHANGED": sum(item.status == "UNCHANGED" for item in items),
    }
    successful = sum(item.error is None for item in items)
    base: dict[str, object] = {
        "schema": "glaciereq.opening-watch.v1",
        "target_count": len(targets),
        "successful_count": successful,
        "failed_count": len(targets) - successful,
        "new_count": counts["NEW"],
        "changed_count": counts["CHANGED"],
        "unchanged_count": counts["UNCHANGED"],
        "items": [item.as_dict() for item in items],
    }
    receipt_sha = _canonical_sha256(base)
    result = OpeningWatchResult(
        schema=str(base["schema"]),
        target_count=len(targets),
        successful_count=successful,
        failed_count=len(targets) - successful,
        new_count=counts["NEW"],
        changed_count=counts["CHANGED"],
        unchanged_count=counts["UNCHANGED"],
        items=tuple(items),
        receipt_sha256=receipt_sha,
    )
    _write_json(state_dir / "OPENING_WATCH_RECEIPT.json", result.as_dict())
    return result


def load_watch_manifest(path: Path) -> tuple[OpeningWatchTarget, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("opening watch manifest must be an object")
    raw = payload.get("openings")
    if not isinstance(raw, list) or not raw:
        raise ValueError("opening watch manifest requires non-empty openings")
    targets: list[OpeningWatchTarget] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping) or not item.get("url"):
            raise ValueError(f"opening watch openings[{index}] requires url")
        targets.append(
            OpeningWatchTarget(
                url=str(item["url"]),
                label=str(item["label"]) if item.get("label") else None,
            )
        )
    return tuple(targets)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-opening-watch",
        description=(
            "Refresh an attributable set of live job openings with isolated failures, "
            "persistent snapshots, and aggregate NEW/CHANGED/UNCHANGED telemetry."
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    from .application_operations import ingest_job_opening_url

    args = _parser().parse_args(argv)
    result = execute_opening_watch(
        load_watch_manifest(args.manifest),
        state_dir=args.state_dir,
        fetcher=ingest_job_opening_url,
        continue_on_error=not args.fail_fast,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.successful_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
