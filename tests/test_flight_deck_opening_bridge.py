from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from job_app_helix.flight_deck_opening_bridge import compile_flight_deck_opening_bridge


def _write_snapshot(root: Path, key: str, *, metadata: dict | None = None, title: str = "Engineer") -> dict:
    opening = {
        "opening_id": "opening-123",
        "company": "Example Co",
        "title": title,
        "description": "Build reliable systems",
        "location": "Remote",
        "requirements": ["Python"],
        "preferred": ["Distributed systems"],
        "source_url": "https://example.test/jobs/123",
        "metadata": metadata or {"updated_at": "v1"},
        "digest": "provider-digest",
    }
    payload = {
        "schema": "glaciereq.live-opening-acquisition.v1",
        "source_url": opening["source_url"],
        "opening": opening,
        "change": {"status": "NEW", "previous_digest": None, "current_digest": "provider-digest", "changed_fields": []},
        "receipt_sha256": "acquisition-receipt-1",
    }
    path = root / "openings" / key / "OPENING_SNAPSHOT.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _watch_item(*, key: str = "state-1", error: str | None = None) -> dict:
    if error:
        return {
            "url": "https://example.test/jobs/failed",
            "label": "failed",
            "state_key": "failed-state",
            "status": "FAILED_ISOLATED",
            "opening_id": None,
            "changed_fields": [],
            "material_changed_fields": [],
            "change_class": "FAILED_ISOLATED",
            "receipt_sha256": None,
            "error": error,
        }
    return {
        "url": "https://example.test/jobs/123",
        "label": "target",
        "state_key": key,
        "status": "NEW",
        "opening_id": "opening-123",
        "changed_fields": [],
        "material_changed_fields": [],
        "change_class": "NEW",
        "receipt_sha256": "acquisition-receipt-1",
        "error": None,
    }


def _watch(items: list[dict]) -> dict:
    return {
        "schema": "glaciereq.opening-watch.v2",
        "items": items,
        "receipt_sha256": "watch-receipt-1",
    }


def test_bridge_emits_private_flight_deck_compatible_active_identity(tmp_path: Path) -> None:
    _write_snapshot(tmp_path, "state-1")
    result = compile_flight_deck_opening_bridge(_watch([_watch_item()]), state_dir=tmp_path)
    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.status == "ACTIVE"
    assert observation.source_url == "https://example.test/jobs/123"
    assert observation.opening_id == "opening-123"
    assert len(observation.opening_digest) == 64
    assert observation.watch_receipt_sha256 == "watch-receipt-1"
    assert observation.acquisition_receipt_sha256 == "acquisition-receipt-1"


def test_metadata_only_provider_churn_does_not_change_material_digest(tmp_path: Path) -> None:
    first = _write_snapshot(tmp_path, "state-1", metadata={"updated_at": "v1"})
    result_one = compile_flight_deck_opening_bridge(_watch([_watch_item()]), state_dir=tmp_path)
    second = deepcopy(first)
    second["opening"]["metadata"] = {"updated_at": "v2", "tracking": "changed"}
    second["opening"]["digest"] = "provider-digest-v2"
    second["receipt_sha256"] = "acquisition-receipt-2"
    path = tmp_path / "openings" / "state-1" / "OPENING_SNAPSHOT.json"
    path.write_text(json.dumps(second), encoding="utf-8")
    item = _watch_item()
    item["receipt_sha256"] = "acquisition-receipt-2"
    result_two = compile_flight_deck_opening_bridge(_watch([item]), state_dir=tmp_path)
    assert result_one.observations[0].opening_digest == result_two.observations[0].opening_digest


def test_recruiter_material_change_rotates_flight_deck_digest(tmp_path: Path) -> None:
    _write_snapshot(tmp_path, "state-1", title="Engineer")
    first = compile_flight_deck_opening_bridge(_watch([_watch_item()]), state_dir=tmp_path)
    _write_snapshot(tmp_path, "state-1", title="Senior Engineer")
    second = compile_flight_deck_opening_bridge(_watch([_watch_item()]), state_dir=tmp_path)
    assert first.observations[0].opening_digest != second.observations[0].opening_digest


def test_failed_acquisition_is_isolated_not_misclassified_as_missing(tmp_path: Path) -> None:
    result = compile_flight_deck_opening_bridge(
        _watch([_watch_item(error="TimeoutError: provider timeout")]),
        state_dir=tmp_path,
    )
    assert result.observations == ()
    assert result.isolated_failures == (
        {
            "source_url": "https://example.test/jobs/failed",
            "watch_change_class": "FAILED_ISOLATED",
            "error": "TimeoutError: provider timeout",
        },
    )


def test_watch_snapshot_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    _write_snapshot(tmp_path, "state-1")
    item = _watch_item()
    item["opening_id"] = "tampered-opening"
    with pytest.raises(ValueError, match="opening_id mismatch"):
        compile_flight_deck_opening_bridge(_watch([item]), state_dir=tmp_path)


def test_watch_snapshot_receipt_mismatch_fails_closed(tmp_path: Path) -> None:
    _write_snapshot(tmp_path, "state-1")
    item = _watch_item()
    item["receipt_sha256"] = "wrong-receipt"
    with pytest.raises(ValueError, match="receipt mismatch"):
        compile_flight_deck_opening_bridge(_watch([item]), state_dir=tmp_path)
