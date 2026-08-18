"""Fresh, provenance-bound target-company intelligence.

The engine ingests observed company signals from official or otherwise attributable
sources, expires stale observations, and turns the fresh subset into a hiring-alignment
surface without converting company claims into candidate claims.
"""

from __future__ import annotations

import json
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
