from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from job_app_helix.opening_evidence_freshness import census_opening_evidence_freshness, plan_opening_evidence_reverification


def _receipt(packet_dir: Path, observed_at: str | None) -> None:
    packet_dir.mkdir(parents=True)
    payload: dict[str, object] = {
        "schema": "glaciereq.opening-input-receipt.v1",
        "application_id": packet_dir.name,
        "opening_id": "opening-1",
        "opening_digest": "digest-1",
    }
    if observed_at is not None:
        payload["source_evidence_observed_at"] = observed_at
    (packet_dir / "OPENING_INPUT_RECEIPT.json").write_text(json.dumps(payload), encoding="utf-8")


def test_reverification_plan_is_actionable_without_mutating_packet_evidence(tmp_path: Path) -> None:
    packet_dir = tmp_path / "packet-a"
    observed = datetime(2026, 8, 20, 8, tzinfo=UTC)
    _receipt(packet_dir, observed.isoformat().replace("+00:00", "Z"))

    decision = plan_opening_evidence_reverification(
        packet_dir,
        max_age_minutes=60,
        now=observed + timedelta(minutes=90),
    )

    assert decision.state == "stale"
    assert decision.action == "reverify_opening_source"
    assert "refresh_opening_source" in decision.continuation
    assert (packet_dir / "OPENING_INPUT_RECEIPT.json").is_file()


def test_census_marks_unobserved_active_packet_for_source_observation(tmp_path: Path) -> None:
    _receipt(tmp_path / "packet-a", None)
    _receipt(tmp_path / ".stale" / "prior-packet", "2026-08-20T08:00:00Z")

    census = census_opening_evidence_freshness(tmp_path, now=datetime(2026, 8, 20, 8, tzinfo=UTC))

    assert census.packet_count == 1
    assert census.attention_count == 1
    assert census.decisions[0].state == "source_observation_required"
    assert census.decisions[0].action == "record_upstream_source_observation"
