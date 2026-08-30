"""Continuously maintain a set of attributable live job openings.

The watch composes the proven single-opening acquisition contract into a batch runtime:
each URL owns an isolated content-addressed state directory, failures stay local to that
opening, and every run emits aggregate change telemetry plus an append-only event log.
Recruiter-material changes are separated from metadata/digest churn so downstream packet
rebuilds happen only when the posting changed in a way that can affect candidate fit,
positioning, or application content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .opening_acquisition import OpeningFetcher, acquire_live_opening

RECRUITER_MATERIAL_FIELDS = frozenset(
    {
        "opening_id",
        "company",
        "title",
        "description",
        "location",
        "requirements",
        "preferred",
    }
)


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
    material_changed_fields: tuple[str, ...]
    change_class: str
    receipt_sha256: str | None
    error: str | None = None

    @property
    def recruiter_material(self) -> bool:
        return self.change_class in {"NEW", "RECRUITER_MATERIAL"}

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
    material_changed_count: int
    non_material_changed_count: int
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
            "material_changed_count": self.material_changed_count,
            "non_material_changed_count": self.non_material_changed_count,
            "unchanged_count": self.unchanged_count,
            "items": [item.as_dict() for item in self.items],
            "receipt_sha256": self.receipt_sha256,
        }


def _reference_sha256(payload: Mapping[str, object]) -> str:
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


def classify_opening_change(
    status: str,
    changed_fields: Sequence[str],
) -> tuple[str, tuple[str, ...]]:
    """Classify raw posting drift by whether it can change recruiter-facing output."""
    if status == "NEW":
        return "NEW", ()
    if status == "UNCHANGED":
        return "UNCHANGED", ()
    if status != "CHANGED":
        raise ValueError(f"unsupported opening change status: {status}")

    material = tuple(sorted(RECRUITER_MATERIAL_FIELDS.intersection(changed_fields)))
    if material:
        return "RECRUITER_MATERIAL", material
    if changed_fields:
        return "METADATA_ONLY", ()
    return "DIGEST_ONLY", ()


def execute_opening_watch(
    targets: Sequence[OpeningWatchTarget],
    *,
    state_dir: Path,
    fetcher: OpeningFetcher,
    continue_on_error: bool = True,
) -> OpeningWatchResult:
    """Refresh a live opening set and persist field-sensitive change telemetry."""
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
                material_changed_fields=(),
                change_class="FAILED_ISOLATED",
                receipt_sha256=None,
                error=f"{type(exc).__name__}: {exc}",
            )
        else:
            change_class, material_fields = classify_opening_change(
                acquisition.change.status,
                acquisition.change.changed_fields,
            )
            item = OpeningWatchItemResult(
                url=target.url,
                label=target.label,
                state_key=key,
                status=acquisition.change.status,
                opening_id=acquisition.opening.opening_id,
                changed_fields=acquisition.change.changed_fields,
                material_changed_fields=material_fields,
                change_class=change_class,
                receipt_sha256=acquisition.receipt_sha256,
            )
        items.append(item)
        _append_event(state_dir / "OPENING_CHANGE_EVENTS.jsonl", item.as_dict())

    counts = {
        "NEW": sum(item.status == "NEW" for item in items),
        "CHANGED": sum(item.status == "CHANGED" for item in items),
        "UNCHANGED": sum(item.status == "UNCHANGED" for item in items),
        "RECRUITER_MATERIAL": sum(item.change_class == "RECRUITER_MATERIAL" for item in items),
        "NON_MATERIAL": sum(
            item.change_class in {"METADATA_ONLY", "DIGEST_ONLY"} for item in items
        ),
    }
    successful = sum(item.error is None for item in items)
    base: dict[str, object] = {
        "schema": "glaciereq.opening-watch.v2",
        "target_count": len(targets),
        "successful_count": successful,
        "failed_count": len(targets) - successful,
        "new_count": counts["NEW"],
        "changed_count": counts["CHANGED"],
        "material_changed_count": counts["RECRUITER_MATERIAL"],
        "non_material_changed_count": counts["NON_MATERIAL"],
        "unchanged_count": counts["UNCHANGED"],
        "items": [item.as_dict() for item in items],
    }
    receipt_sha = _reference_sha256(base)
    result = OpeningWatchResult(
        schema=str(base["schema"]),
        target_count=len(targets),
        successful_count=successful,
        failed_count=len(targets) - successful,
        new_count=counts["NEW"],
        changed_count=counts["CHANGED"],
        material_changed_count=counts["RECRUITER_MATERIAL"],
        non_material_changed_count=counts["NON_MATERIAL"],
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
            "Refresh attributable live job openings with isolated failures and classify "
            "recruiter-material change separately from metadata/digest churn."
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
