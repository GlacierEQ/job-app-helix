"""Acquire live job openings with provenance and deterministic change detection."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .application_operations import JobOpening, ingest_job_opening_url

OpeningFetcher = Callable[[str], JobOpening]


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class OpeningChange:
    status: str
    previous_digest: str | None
    current_digest: str
    changed_fields: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OpeningAcquisitionResult:
    schema: str
    acquired_at: str
    source_url: str
    opening: JobOpening
    change: OpeningChange
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "acquired_at": self.acquired_at,
            "source_url": self.source_url,
            "opening": self.opening.as_dict(),
            "change": self.change.as_dict(),
            "receipt_sha256": self.receipt_sha256,
        }


def _opening_identity(opening: JobOpening) -> dict[str, object]:
    return {
        "opening_id": opening.opening_id,
        "company": opening.company,
        "title": opening.title,
        "description": opening.description,
        "location": opening.location,
        "requirements": list(opening.requirements),
        "preferred": list(opening.preferred),
        "source_url": opening.source_url,
        "metadata": dict(opening.metadata),
        "digest": opening.digest,
    }


def detect_opening_change(
    opening: JobOpening,
    previous: Mapping[str, object] | None,
) -> OpeningChange:
    if previous is None:
        return OpeningChange(
            status="NEW",
            previous_digest=None,
            current_digest=opening.digest,
            changed_fields=(),
        )

    previous_opening = previous.get("opening")
    if not isinstance(previous_opening, Mapping):
        raise ValueError("previous opening snapshot is missing opening object")

    previous_digest = str(previous_opening.get("digest") or "").strip()
    if previous_digest == opening.digest:
        return OpeningChange(
            status="UNCHANGED",
            previous_digest=previous_digest or None,
            current_digest=opening.digest,
            changed_fields=(),
        )

    current = _opening_identity(opening)
    changed = tuple(
        sorted(
            key
            for key, value in current.items()
            if key != "digest" and previous_opening.get(key) != value
        )
    )
    return OpeningChange(
        status="CHANGED",
        previous_digest=previous_digest or None,
        current_digest=opening.digest,
        changed_fields=changed,
    )


def acquire_live_opening(
    url: str,
    *,
    snapshot_path: Path,
    receipt_path: Path | None = None,
    fetcher: OpeningFetcher = ingest_job_opening_url,
) -> OpeningAcquisitionResult:
    if not url.startswith(("https://", "http://")):
        raise ValueError("job URL must be http(s)")

    previous: Mapping[str, object] | None = None
    if snapshot_path.is_file():
        loaded = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, Mapping):
            raise ValueError("existing opening snapshot must contain an object")
        previous = loaded

    opening = fetcher(url)
    if opening.source_url and opening.source_url != url:
        raise ValueError(
            f"opening source URL mismatch: observed {opening.source_url!r}, requested {url!r}"
        )

    change = detect_opening_change(opening, previous)
    acquired_at = _utc_now()
    base: dict[str, object] = {
        "schema": "glaciereq.live-opening-acquisition.v1",
        "acquired_at": acquired_at,
        "source_url": url,
        "opening": opening.as_dict(),
        "change": change.as_dict(),
    }
    receipt_sha = _sha256(base)
    result = OpeningAcquisitionResult(
        schema=str(base["schema"]),
        acquired_at=acquired_at,
        source_url=url,
        opening=opening,
        change=change,
        receipt_sha256=receipt_sha,
    )
    payload = result.as_dict()
    _write_json(snapshot_path, payload)
    if receipt_path is not None:
        _write_json(receipt_path, payload)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-opening-acquire",
        description=(
            "Acquire an attributable live JobPosting URL, normalize it, persist the "
            "snapshot, and report deterministic NEW/UNCHANGED/CHANGED state."
        ),
    )
    parser.add_argument("url")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = acquire_live_opening(
        args.url,
        snapshot_path=args.snapshot,
        receipt_path=args.receipt,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
