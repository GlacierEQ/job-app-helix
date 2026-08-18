"""Refresh company intelligence without destroying prior provenance.

The refresh engine treats each incoming intelligence manifest as a new observation
set. It validates company identity and time ordering, computes semantic deltas,
retires superseded or stale observations into append-only history, and emits a
new active manifest plus a deterministic refresh receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .company_intelligence import CompanyIntelligence, CompanySignal, load_company_intelligence


def _now_utc(value: datetime | None = None) -> datetime:
    return (value or datetime.now(UTC)).astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _signal_key(signal: CompanySignal) -> tuple[str, str]:
    """Identify a signal channel independently of changing wording."""
    return signal.kind, signal.source_url.rstrip("/")


def _signal_fingerprint(signal: CompanySignal) -> str:
    normalized = {
        "kind": signal.kind,
        "statement": " ".join(signal.statement.split()),
        "source_url": signal.source_url.rstrip("/"),
        "source_title": " ".join(signal.source_title.split()),
    }
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _index_signals(
    signals: tuple[CompanySignal, ...],
    *,
    label: str,
) -> dict[tuple[str, str], CompanySignal]:
    indexed: dict[tuple[str, str], CompanySignal] = {}
    for signal in signals:
        key = _signal_key(signal)
        if key in indexed:
            raise ValueError(
                f"{label} company intelligence contains duplicate signal channel: "
                f"{signal.kind} {signal.source_url}"
            )
        indexed[key] = signal
    return indexed


def _age_seconds(signal: CompanySignal, clock: datetime) -> float:
    observed = datetime.fromisoformat(signal.observed_at.replace("Z", "+00:00"))
    return (clock - observed.astimezone(UTC)).total_seconds()


@dataclass(frozen=True)
class RetiredSignal:
    signal: CompanySignal
    retired_at: str
    reason: str
    replacement_fingerprint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RefreshReceipt:
    schema: str
    company_id: str
    previous_collected_at: str
    incoming_collected_at: str
    refreshed_at: str
    active_count: int
    added_count: int
    unchanged_count: int
    superseded_count: int
    stale_retired_count: int
    receipt_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RefreshResult:
    intelligence: CompanyIntelligence
    retired: tuple[RetiredSignal, ...]
    receipt: RefreshReceipt


def _receipt_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def refresh_company_intelligence(
    current: CompanyIntelligence,
    incoming: CompanyIntelligence,
    *,
    now: datetime | None = None,
) -> RefreshResult:
    """Compose a new active intelligence set while retaining historical evidence.

    Current observations omitted by a partial refresh remain active until stale.
    Incoming stale observations are retired immediately instead of being reactivated.
    A kind/source channel is unique inside each snapshot so ambiguous overwrites fail.
    """
    if current.company_id != incoming.company_id or current.company != incoming.company:
        raise ValueError("company intelligence refresh cannot change company identity")

    current_collected = datetime.fromisoformat(current.collected_at.replace("Z", "+00:00"))
    incoming_collected = datetime.fromisoformat(incoming.collected_at.replace("Z", "+00:00"))
    if incoming_collected < current_collected:
        raise ValueError("incoming company intelligence collected_at is older than current state")

    clock = _now_utc(now)
    freshness_limit = incoming.max_age_days * 86400
    current_by_key = _index_signals(current.signals, label="current")
    incoming_by_key = _index_signals(incoming.signals, label="incoming")

    active: list[CompanySignal] = []
    retired: list[RetiredSignal] = []
    added = 0
    unchanged = 0
    superseded = 0
    stale_retired = 0

    for key, signal in incoming_by_key.items():
        prior = current_by_key.get(key)
        age_seconds = _age_seconds(signal, clock)
        if age_seconds > freshness_limit:
            stale_retired += 1
            retired.append(
                RetiredSignal(signal=signal, retired_at=_iso(clock), reason="STALE_INCOMING")
            )
            if prior is not None and 0 <= _age_seconds(prior, clock) <= freshness_limit:
                active.append(prior)
            continue
        if age_seconds < 0:
            raise ValueError("incoming company signal observed_at cannot be in the future")

        if prior is None:
            added += 1
        elif _signal_fingerprint(prior) == _signal_fingerprint(signal):
            unchanged += 1
        else:
            superseded += 1
            retired.append(
                RetiredSignal(
                    signal=prior,
                    retired_at=_iso(clock),
                    reason="SUPERSEDED",
                    replacement_fingerprint=_signal_fingerprint(signal),
                )
            )
        active.append(signal)

    for key, signal in current_by_key.items():
        if key in incoming_by_key:
            continue
        age_seconds = _age_seconds(signal, clock)
        if age_seconds > freshness_limit:
            stale_retired += 1
            retired.append(RetiredSignal(signal=signal, retired_at=_iso(clock), reason="STALE"))
        elif age_seconds >= 0:
            active.append(signal)

    active.sort(key=lambda signal: (signal.kind, signal.source_url, signal.statement))
    refreshed = CompanyIntelligence(
        schema=incoming.schema,
        company_id=incoming.company_id,
        company=incoming.company,
        collected_at=incoming.collected_at,
        max_age_days=incoming.max_age_days,
        signals=tuple(active),
    )

    base_receipt = {
        "schema": "glaciereq.company-intelligence-refresh.v1",
        "company_id": refreshed.company_id,
        "previous_collected_at": current.collected_at,
        "incoming_collected_at": incoming.collected_at,
        "refreshed_at": _iso(clock),
        "active_count": len(refreshed.signals),
        "added_count": added,
        "unchanged_count": unchanged,
        "superseded_count": superseded,
        "stale_retired_count": stale_retired,
    }
    receipt = RefreshReceipt(
        **base_receipt,
        receipt_sha256=_receipt_hash(
            {
                **base_receipt,
                "active": [asdict(signal) for signal in refreshed.signals],
                "retired": [item.to_dict() for item in retired],
            }
        ),
    )
    return RefreshResult(refreshed, tuple(retired), receipt)


def persist_refresh(
    result: RefreshResult,
    *,
    active_path: Path,
    history_path: Path,
    receipt_path: Path,
) -> None:
    """Persist active state and append historical retirement events atomically per file."""
    active_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    active_payload = json.dumps(result.intelligence.as_dict(), indent=2, sort_keys=True) + "\n"
    receipt_payload = json.dumps(result.receipt.to_dict(), indent=2, sort_keys=True) + "\n"

    active_tmp = active_path.with_suffix(active_path.suffix + ".tmp")
    receipt_tmp = receipt_path.with_suffix(receipt_path.suffix + ".tmp")
    active_tmp.write_text(active_payload, encoding="utf-8")
    receipt_tmp.write_text(receipt_payload, encoding="utf-8")
    active_tmp.replace(active_path)
    receipt_tmp.replace(receipt_path)

    if result.retired:
        with history_path.open("a", encoding="utf-8") as handle:
            for item in result.retired:
                handle.write(json.dumps(item.to_dict(), sort_keys=True) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-company-refresh",
        description=(
            "Refresh attributable company intelligence with semantic change detection, "
            "stale retirement, and append-only provenance history."
        ),
    )
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--incoming", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    current = load_company_intelligence(args.current)
    incoming = load_company_intelligence(args.incoming)
    result = refresh_company_intelligence(current, incoming)
    persist_refresh(
        result,
        active_path=args.output,
        history_path=args.history,
        receipt_path=args.receipt,
    )
    print(json.dumps(result.receipt.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
