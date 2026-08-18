# ruff: noqa: I001
from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.application_operations import ingest_job_opening
from job_app_helix.opening_acquisition import acquire_live_opening


URL = "https://jobs.example.com/roles/123"


def _opening(*, title: str = "Senior Systems Engineer", location: str = "Remote"):
    return ingest_job_opening(
        {
            "id": "123",
            "company": "Example",
            "title": title,
            "description": "Build reliable distributed systems in Python and Rust.",
            "location": location,
            "requirements": ["Python", "distributed systems"],
            "preferred": ["Rust"],
            "metadata": {"provider": "example"},
        },
        source="url",
        source_url=URL,
    )


def test_first_acquisition_is_new_and_persists_receipt(tmp_path: Path) -> None:
    snapshot = tmp_path / "OPENING.json"
    receipt = tmp_path / "OPENING_RECEIPT.json"
    result = acquire_live_opening(
        URL,
        snapshot_path=snapshot,
        receipt_path=receipt,
        fetcher=lambda _: _opening(),
    )

    assert result.change.status == "NEW"
    assert result.change.changed_fields == ()
    assert result.receipt_sha256
    assert snapshot.is_file()
    assert receipt.is_file()
    persisted = json.loads(snapshot.read_text(encoding="utf-8"))
    assert persisted["opening"]["opening_id"] == "123"
    assert persisted["source_url"] == URL
    assert persisted["receipt_sha256"] == result.receipt_sha256


def test_reacquisition_of_identical_opening_is_unchanged(tmp_path: Path) -> None:
    snapshot = tmp_path / "OPENING.json"
    acquire_live_opening(URL, snapshot_path=snapshot, fetcher=lambda _: _opening())
    second = acquire_live_opening(URL, snapshot_path=snapshot, fetcher=lambda _: _opening())

    assert second.change.status == "UNCHANGED"
    assert second.change.previous_digest == second.change.current_digest
    assert second.change.changed_fields == ()


def test_material_opening_change_identifies_exact_fields(tmp_path: Path) -> None:
    snapshot = tmp_path / "OPENING.json"
    acquire_live_opening(URL, snapshot_path=snapshot, fetcher=lambda _: _opening())
    second = acquire_live_opening(
        URL,
        snapshot_path=snapshot,
        fetcher=lambda _: _opening(title="Principal Systems Engineer", location="Austin, TX"),
    )

    assert second.change.status == "CHANGED"
    assert second.change.previous_digest != second.change.current_digest
    assert second.change.changed_fields == ("location", "title")


def test_source_url_mismatch_is_rejected_before_snapshot_mutation(tmp_path: Path) -> None:
    snapshot = tmp_path / "OPENING.json"
    bad = ingest_job_opening(
        {
            "id": "123",
            "company": "Example",
            "title": "Engineer",
            "description": "Build systems.",
        },
        source="url",
        source_url="https://evil.example/jobs/123",
    )

    with pytest.raises(ValueError, match="source URL mismatch"):
        acquire_live_opening(URL, snapshot_path=snapshot, fetcher=lambda _: bad)

    assert not snapshot.exists()


def test_invalid_existing_snapshot_fails_closed(tmp_path: Path) -> None:
    snapshot = tmp_path / "OPENING.json"
    snapshot.write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain an object"):
        acquire_live_opening(URL, snapshot_path=snapshot, fetcher=lambda _: _opening())
