"""Project Helix opening-watch state into private flight-deck opening identity.

The bridge deliberately hashes recruiter-material fields instead of the full provider
snapshot. Metadata-only churn therefore remains observable in Helix without invalidating
a human-reviewed application package in the private flight deck. Failed acquisitions are
reported separately and are never converted into a false CLOSED/MISSING observation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .opening_watch import RECRUITER_MATERIAL_FIELDS

WATCH_SCHEMA = "glaciereq.opening-watch.v2"
SNAPSHOT_SCHEMA = "glaciereq.live-opening-acquisition.v1"
BRIDGE_SCHEMA = "glaciereq.flight-deck-opening-bridge.v1"


@dataclass(frozen=True)
class FlightDeckOpeningObservation:
    status: str
    source_url: str
    opening_id: str
    opening_digest: str
    watch_change_class: str
    watch_receipt_sha256: str
    acquisition_receipt_sha256: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class FlightDeckOpeningBridgeResult:
    schema: str
    observations: tuple[FlightDeckOpeningObservation, ...]
    isolated_failures: tuple[dict[str, str], ...]
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "observations": [item.as_dict() for item in self.observations],
            "isolated_failures": list(self.isolated_failures),
            "receipt_sha256": self.receipt_sha256,
        }


def _reference_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _material_opening_digest(opening: Mapping[str, object]) -> str:
    """Hash only fields whose changes can alter recruiter-facing application output."""
    material = {
        field: opening.get(field)
        for field in sorted(RECRUITER_MATERIAL_FIELDS)
    }
    return _reference_sha256(material)


def _snapshot_for_item(state_dir: Path, state_key: str) -> dict[str, object]:
    if not state_key or any(part in {"", ".", ".."} for part in Path(state_key).parts):
        raise ValueError("opening-watch item has unsafe state_key")
    snapshot_path = state_dir / "openings" / state_key / "OPENING_SNAPSHOT.json"
    snapshot = _load_object(snapshot_path)
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError(f"opening snapshot schema mismatch for {state_key}")
    return snapshot


def compile_flight_deck_opening_bridge(
    watch_receipt: Mapping[str, object],
    *,
    state_dir: Path,
) -> FlightDeckOpeningBridgeResult:
    """Compile exact active-opening observations from a Helix watch receipt.

    Successful watch entries are joined back to their acquisition snapshots so the bridge
    never trusts aggregate telemetry as a substitute for source-bound opening content.
    Failed entries remain failures; transient provider/network failure is not evidence that
    an opening disappeared.
    """
    if watch_receipt.get("schema") != WATCH_SCHEMA:
        raise ValueError("opening watch receipt schema mismatch")
    watch_sha = str(watch_receipt.get("receipt_sha256") or "").strip()
    if not watch_sha:
        raise ValueError("opening watch receipt_sha256 is required")
    items = watch_receipt.get("items")
    if not isinstance(items, list):
        raise ValueError("opening watch receipt items must be a list")

    observations: list[FlightDeckOpeningObservation] = []
    failures: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, Mapping):
            raise ValueError(f"opening watch item {index} must be an object")
        url = str(raw_item.get("url") or "").strip()
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"opening watch item {index} has invalid url")
        if url in seen_urls:
            raise ValueError(f"opening watch receipt contains duplicate url: {url}")
        seen_urls.add(url)

        error = raw_item.get("error")
        if error is not None or raw_item.get("status") == "FAILED_ISOLATED":
            failures.append(
                {
                    "source_url": url,
                    "watch_change_class": str(raw_item.get("change_class") or "FAILED_ISOLATED"),
                    "error": str(error or "opening acquisition failed"),
                }
            )
            continue

        state_key = str(raw_item.get("state_key") or "").strip()
        snapshot = _snapshot_for_item(state_dir, state_key)
        if snapshot.get("source_url") != url:
            raise ValueError(f"opening snapshot source_url mismatch for {url}")
        acquisition_sha = str(snapshot.get("receipt_sha256") or "").strip()
        if not acquisition_sha:
            raise ValueError(f"opening snapshot receipt_sha256 missing for {url}")
        if raw_item.get("receipt_sha256") != acquisition_sha:
            raise ValueError(f"opening watch/acquisition receipt mismatch for {url}")

        opening = snapshot.get("opening")
        if not isinstance(opening, Mapping):
            raise ValueError(f"opening snapshot opening object missing for {url}")
        opening_id = str(opening.get("opening_id") or "").strip()
        if not opening_id:
            raise ValueError(f"opening_id missing for {url}")
        if raw_item.get("opening_id") != opening_id:
            raise ValueError(f"opening watch/snapshot opening_id mismatch for {url}")
        if opening.get("source_url") not in {None, "", url}:
            raise ValueError(f"opening payload source_url mismatch for {url}")

        observations.append(
            FlightDeckOpeningObservation(
                status="ACTIVE",
                source_url=url,
                opening_id=opening_id,
                opening_digest=_material_opening_digest(opening),
                watch_change_class=str(raw_item.get("change_class") or ""),
                watch_receipt_sha256=watch_sha,
                acquisition_receipt_sha256=acquisition_sha,
            )
        )

    base: dict[str, object] = {
        "schema": BRIDGE_SCHEMA,
        "observations": [item.as_dict() for item in observations],
        "isolated_failures": failures,
    }
    return FlightDeckOpeningBridgeResult(
        schema=BRIDGE_SCHEMA,
        observations=tuple(observations),
        isolated_failures=tuple(failures),
        receipt_sha256=_reference_sha256(base),
    )


def compile_bridge_from_state(state_dir: Path) -> FlightDeckOpeningBridgeResult:
    receipt = _load_object(state_dir / "OPENING_WATCH_RECEIPT.json")
    return compile_flight_deck_opening_bridge(receipt, state_dir=state_dir)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-flight-deck-bridge",
        description=(
            "Compile source-bound live-opening observations for GlacierEQ/job-app's "
            "private application flight deck."
        ),
    )
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = compile_bridge_from_state(args.state_dir)
    rendered = json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.observations else 2


if __name__ == "__main__":
    raise SystemExit(main())
