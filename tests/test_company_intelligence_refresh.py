from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from job_app_helix.company_intelligence import CompanyIntelligence, CompanySignal
from job_app_helix.company_intelligence_refresh import (
    persist_refresh,
    refresh_company_intelligence,
)


def _signal(
    *,
    kind: str = "engineering",
    statement: str = "Build reliable agent systems.",
    source_url: str = "https://example.com/engineering",
    observed_at: str = "2026-08-18T00:00:00Z",
) -> CompanySignal:
    return CompanySignal(
        kind=kind,
        statement=statement,
        source_url=source_url,
        observed_at=observed_at,
        source_title="Official source",
    )


def _intel(
    signals: tuple[CompanySignal, ...],
    *,
    collected_at: str = "2026-08-18T00:00:00Z",
    company_id: str = "example",
    company: str = "Example",
    max_age_days: int = 30,
) -> CompanyIntelligence:
    return CompanyIntelligence(
        schema="glaciereq.company-intelligence.v1",
        company_id=company_id,
        company=company,
        collected_at=collected_at,
        max_age_days=max_age_days,
        signals=signals,
    )


def test_refresh_supersedes_changed_source_and_retains_history() -> None:
    prior = _signal(statement="Build reliable agent systems.")
    replacement = _signal(
        statement="Build reliable agent systems with stronger observability.",
        observed_at="2026-08-18T06:00:00Z",
    )

    result = refresh_company_intelligence(
        _intel((prior,)),
        _intel((replacement,), collected_at="2026-08-18T06:00:00Z"),
        now=datetime(2026, 8, 18, 7, tzinfo=UTC),
    )

    assert result.intelligence.signals == (replacement,)
    assert result.receipt.superseded_count == 1
    assert result.receipt.added_count == 0
    assert len(result.retired) == 1
    assert result.retired[0].reason == "SUPERSEDED"
    assert result.retired[0].signal == prior
    assert result.retired[0].replacement_fingerprint is not None


def test_refresh_keeps_absent_but_still_fresh_signal() -> None:
    retained = _signal(
        kind="value",
        statement="Care deeply about users.",
        source_url="https://example.com/values",
        observed_at="2026-08-10T00:00:00Z",
    )
    incoming = _signal(observed_at="2026-08-18T06:00:00Z")

    result = refresh_company_intelligence(
        _intel((retained,)),
        _intel((incoming,), collected_at="2026-08-18T06:00:00Z"),
        now=datetime(2026, 8, 18, 7, tzinfo=UTC),
    )

    assert set(result.intelligence.signals) == {retained, incoming}
    assert result.receipt.added_count == 1
    assert result.receipt.stale_retired_count == 0
    assert result.retired == ()


def test_refresh_retires_absent_stale_signal() -> None:
    stale = _signal(
        kind="hiring",
        statement="Hiring for an old team.",
        source_url="https://example.com/jobs",
        observed_at="2026-01-01T00:00:00Z",
    )
    incoming = _signal(observed_at="2026-08-18T06:00:00Z")

    result = refresh_company_intelligence(
        _intel((stale,)),
        _intel((incoming,), collected_at="2026-08-18T06:00:00Z"),
        now=datetime(2026, 8, 18, 7, tzinfo=UTC),
    )

    assert stale not in result.intelligence.signals
    assert result.receipt.stale_retired_count == 1
    assert result.retired[0].reason == "STALE"


def test_stale_incoming_does_not_displace_fresh_current_signal() -> None:
    current = _signal(observed_at="2026-08-10T00:00:00Z")
    stale_incoming = _signal(
        statement="Ancient copy of the same source.",
        observed_at="2026-01-01T00:00:00Z",
    )

    result = refresh_company_intelligence(
        _intel((current,), collected_at="2026-08-10T00:00:00Z"),
        _intel((stale_incoming,), collected_at="2026-08-18T06:00:00Z"),
        now=datetime(2026, 8, 18, 7, tzinfo=UTC),
    )

    assert result.intelligence.signals == (current,)
    assert result.retired[0].reason == "STALE_INCOMING"
    assert result.receipt.stale_retired_count == 1
    assert result.receipt.superseded_count == 0


def test_duplicate_signal_channel_is_rejected() -> None:
    first = _signal(statement="First statement")
    duplicate = _signal(statement="Conflicting second statement")

    with pytest.raises(ValueError, match="duplicate signal channel"):
        refresh_company_intelligence(
            _intel((first,)),
            _intel((first, duplicate), collected_at="2026-08-18T06:00:00Z"),
            now=datetime(2026, 8, 18, 7, tzinfo=UTC),
        )


def test_refresh_rejects_identity_change_and_time_regression() -> None:
    current = _intel((_signal(),), collected_at="2026-08-18T06:00:00Z")

    with pytest.raises(ValueError, match="company identity"):
        refresh_company_intelligence(
            current,
            _intel((_signal(),), company_id="other", company="Other"),
        )

    with pytest.raises(ValueError, match="older than current"):
        refresh_company_intelligence(
            current,
            _intel((_signal(),), collected_at="2026-08-17T06:00:00Z"),
        )


def test_persist_refresh_writes_active_receipt_and_append_only_history(tmp_path: Path) -> None:
    prior = _signal(statement="Old statement")
    replacement = _signal(statement="New statement", observed_at="2026-08-18T06:00:00Z")
    result = refresh_company_intelligence(
        _intel((prior,)),
        _intel((replacement,), collected_at="2026-08-18T06:00:00Z"),
        now=datetime(2026, 8, 18, 7, tzinfo=UTC),
    )
    active = tmp_path / "active.json"
    history = tmp_path / "history.jsonl"
    receipt = tmp_path / "receipt.json"

    persist_refresh(result, active_path=active, history_path=history, receipt_path=receipt)
    persist_refresh(result, active_path=active, history_path=history, receipt_path=receipt)

    active_payload = json.loads(active.read_text(encoding="utf-8"))
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    history_rows = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines()]

    assert active_payload["signals"][0]["statement"] == "New statement"
    assert receipt_payload["superseded_count"] == 1
    assert len(receipt_payload["receipt_sha256"]) == 64
    assert len(history_rows) == 2
    assert all(row["reason"] == "SUPERSEDED" for row in history_rows)
