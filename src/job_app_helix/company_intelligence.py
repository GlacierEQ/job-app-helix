"""Fresh, provenance-bound target-company intelligence.

The engine ingests observed company signals from official or otherwise attributable
sources, expires stale observations, and turns the fresh subset into a hiring-alignment
surface without converting company claims into candidate claims.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_SIGNAL_KINDS = {"product", "investment", "engineering", "value", "hiring"}


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class CompanySignal:
    kind: str
    statement: str
    source_url: str
    observed_at: str
    source_title: str = ""

    def __post_init__(self) -> None:
        if self.kind not in _SIGNAL_KINDS:
            raise ValueError(f"unsupported company signal kind: {self.kind}")
        if not self.statement.strip():
            raise ValueError("company signal statement must not be empty")
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("company signal source_url must be an absolute HTTP(S) URL")
        _parse_time(self.observed_at)


@dataclass(frozen=True)
class CompanyIntelligence:
    schema: str
    company_id: str
    company: str
    collected_at: str
    max_age_days: int
    signals: tuple[CompanySignal, ...]

    def __post_init__(self) -> None:
        if self.max_age_days <= 0:
            raise ValueError("max_age_days must be positive")
        _parse_time(self.collected_at)
        if not self.signals:
            raise ValueError("company intelligence requires at least one sourced signal")

    def fresh_signals(self, *, now: datetime | None = None) -> tuple[CompanySignal, ...]:
        clock = (now or datetime.now(UTC)).astimezone(UTC)
        return tuple(
            signal
            for signal in self.signals
            if 0 <= (clock - _parse_time(signal.observed_at)).total_seconds()
            <= self.max_age_days * 86400
        )

    def stale_signals(self, *, now: datetime | None = None) -> tuple[CompanySignal, ...]:
        fresh = set(self.fresh_signals(now=now))
        return tuple(signal for signal in self.signals if signal not in fresh)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_company_intelligence(
    manifest: Mapping[str, Any],
    shards: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Reconstruct the external bottleneck atlas without collapsing fact/inference.

    The historical estate-intelligence compiler consumes a dictionary keyed by company
    id. Newer company-fit manifests use ``CompanyIntelligence`` objects instead. This
    parser restores the displaced atlas contract while keeping the two models separate:
    official observations remain observations and GlacierEQ bottleneck/leverage fields
    remain explicit inferences.
    """
    refs = manifest.get("shards")
    if not isinstance(refs, list) or not refs:
        raise ValueError("company intelligence atlas requires a non-empty shards list")

    excluded_raw = manifest.get("excluded_company_ids", [])
    if not isinstance(excluded_raw, list):
        raise ValueError("excluded_company_ids must be a list")
    excluded = {str(company_id) for company_id in excluded_raw}

    records: dict[str, dict[str, Any]] = {}
    observed_total = 0
    for index, ref in enumerate(refs):
        if not isinstance(ref, Mapping):
            raise ValueError(f"atlas shards[{index}] must be an object")
        path = str(ref.get("path", "")).strip()
        if not path:
            raise ValueError(f"atlas shards[{index}] is missing path")
        shard = shards.get(path)
        if not isinstance(shard, Mapping):
            raise ValueError(f"atlas shard was not supplied: {path}")

        raw_records = shard.get("records")
        if not isinstance(raw_records, list):
            raise ValueError(f"atlas shard records must be a list: {path}")
        expected_count = int(ref.get("record_count", len(raw_records)))
        if len(raw_records) != expected_count:
            raise ValueError(
                f"atlas shard record count mismatch for {path}: "
                f"{len(raw_records)} != {expected_count}"
            )
        declared_sha = str(ref.get("shard_sha256", ""))
        embedded_sha = str(shard.get("shard_sha256", ""))
        if declared_sha and embedded_sha and declared_sha != embedded_sha:
            raise ValueError(f"atlas shard digest mismatch for {path}")

        observed_total += len(raw_records)
        for row_index, raw in enumerate(raw_records):
            if not isinstance(raw, Mapping):
                raise ValueError(f"atlas {path} records[{row_index}] must be an object")
            company_id = str(raw.get("company_id", "")).strip()
            if not company_id:
                raise ValueError(f"atlas {path} records[{row_index}] lacks company_id")
            if company_id in excluded:
                continue
            if company_id in records:
                raise ValueError(f"duplicate company intelligence record: {company_id}")

            sources = raw.get("official_sources", [])
            if not isinstance(sources, list):
                raise ValueError(f"official_sources must be a list for {company_id}")
            for source_index, source in enumerate(sources):
                if not isinstance(source, Mapping):
                    raise ValueError(
                        f"official_sources[{source_index}] must be an object for {company_id}"
                    )
                source_sha = str(source.get("source_sha256", ""))
                if source_sha and len(source_sha) != 64:
                    raise ValueError(
                        f"invalid source_sha256 for {company_id}: {source_sha!r}"
                    )

            leverage = raw.get("leverage", {})
            if leverage is None:
                leverage = {}
            if not isinstance(leverage, Mapping):
                raise ValueError(f"leverage must be an object for {company_id}")

            record = dict(raw)
            record["leverage_mechanism"] = leverage.get("mechanism")
            record["expected_impact"] = leverage.get("expected_impact")
            record["research_as_of"] = manifest.get("research_as_of")
            record["freshness_state"] = manifest.get("freshness_state")
            record["inference_boundary"] = manifest.get("inference_boundary")
            records[company_id] = record

    expected_total = int(manifest.get("record_count", observed_total))
    if observed_total != expected_total:
        raise ValueError(
            f"atlas total record count mismatch: {observed_total} != {expected_total}"
        )
    expected_external = expected_total - sum(
        1
        for company_id in excluded
        if any(
            company_id == str(raw.get("company_id", ""))
            for shard in shards.values()
            for raw in shard.get("records", [])
            if isinstance(raw, Mapping)
        )
    )
    if len(records) != expected_external:
        raise ValueError(
            f"atlas external record count mismatch: {len(records)} != {expected_external}"
        )
    return records


def load_company_intelligence(path: Path) -> CompanyIntelligence:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("company intelligence payload must be an object")
    raw_signals = payload.get("signals")
    if not isinstance(raw_signals, list):
        raise ValueError("company intelligence signals must be a list")
    signals = tuple(CompanySignal(**item) for item in raw_signals)
    return CompanyIntelligence(
        schema=str(payload.get("schema", "glaciereq.company-intelligence.v1")),
        company_id=str(payload["company_id"]),
        company=str(payload["company"]),
        collected_at=str(payload["collected_at"]),
        max_age_days=int(payload.get("max_age_days", 45)),
        signals=signals,
    )
