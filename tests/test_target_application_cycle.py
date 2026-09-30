from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.target_application_cycle import (
    REQUIRED_APPLICATION_ARTIFACTS,
    ApplicationReadinessError,
    promote_strongest_application_ready_packet,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _packet(
    root: Path,
    application_id: str,
    *,
    queue_rank: int,
    priority_score: float,
    lane: str = "APPLY_NOW",
    opening_id: str = "opening-1",
    company_id: str = "anthropic",
) -> Path:
    packet = root / application_id
    for relative in REQUIRED_APPLICATION_ARTIFACTS:
        path = packet / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "PRIORITY_RECEIPT.json":
            _write_json(
                path,
                {
                    "application_id": application_id,
                    "opening_id": opening_id,
                    "company_id": company_id,
                    "lane": lane,
                    "queue_rank": queue_rank,
                    "priority_score": priority_score,
                },
            )
        elif relative == "OPENING_INPUT_RECEIPT.json":
            _write_json(
                path,
                {
                    "opening_id": opening_id,
                    "opening_digest": f"digest:{opening_id}",
                },
            )
        elif path.suffix == ".json":
            _write_json(path, {"artifact": relative, "application_id": application_id})
        else:
            path.write_text(f"# {relative}\n{application_id}\n", encoding="utf-8")
    return packet


def test_promotes_highest_ranked_complete_packet_with_integrity_manifest(tmp_path: Path) -> None:
    output = tmp_path / "packets"
    second = _packet(output, "app-second", queue_rank=2, priority_score=91.0)
    strongest = _packet(output, "app-strongest", queue_rank=1, priority_score=88.0)
    release_path = tmp_path / "state" / "APPLICATION_READY_TARGET.json"

    release = promote_strongest_application_ready_packet(
        output,
        target_cycle_receipt_sha256="target-cycle-sha",
        release_path=release_path,
    )

    assert release.selected.application_id == "app-strongest"
    assert release.selected.queue_rank == 1
    assert set(release.selected.artifact_sha256) == set(REQUIRED_APPLICATION_ARTIFACTS)
    assert all(len(value) == 64 for value in release.selected.artifact_sha256.values())
    assert len(release.selected.bundle_sha256) == 64
    assert release_path.is_file()
    assert (strongest / "APPLICATION_READY.json").is_file()
    assert not (second / "APPLICATION_READY.json").exists()


def test_rejects_incomplete_higher_rank_and_promotes_next_complete_packet(tmp_path: Path) -> None:
    output = tmp_path / "packets"
    broken = _packet(output, "app-broken", queue_rank=1, priority_score=99.0)
    (broken / "COVER_LETTER.md").unlink()
    fallback = _packet(output, "app-fallback", queue_rank=2, priority_score=90.0)

    release = promote_strongest_application_ready_packet(
        output,
        target_cycle_receipt_sha256="target-cycle-sha",
        release_path=tmp_path / "state" / "APPLICATION_READY_TARGET.json",
    )

    assert release.selected.application_id == "app-fallback"
    assert len(release.rejected_higher_priority_packets) == 1
    rejected = release.rejected_higher_priority_packets[0]
    assert rejected["queue_rank"] == 1
    assert "COVER_LETTER.md" in str(rejected["reason"])
    assert (fallback / "APPLICATION_READY.json").is_file()


def test_fails_closed_when_only_packet_is_non_actionable(tmp_path: Path) -> None:
    output = tmp_path / "packets"
    _packet(output, "app-deferred", queue_rank=1, priority_score=75.0, lane="DEFER")

    with pytest.raises(ApplicationReadinessError, match="no complete actionable recruiter packet"):
        promote_strongest_application_ready_packet(
            output,
            target_cycle_receipt_sha256="target-cycle-sha",
            release_path=tmp_path / "state" / "APPLICATION_READY_TARGET.json",
        )


def test_fails_closed_on_priority_opening_identity_drift(tmp_path: Path) -> None:
    output = tmp_path / "packets"
    packet = _packet(output, "app-drift", queue_rank=1, priority_score=95.0)
    _write_json(
        packet / "OPENING_INPUT_RECEIPT.json",
        {"opening_id": "different-opening", "opening_digest": "digest:different"},
    )

    with pytest.raises(ApplicationReadinessError, match="opening receipt identity drift"):
        promote_strongest_application_ready_packet(
            output,
            target_cycle_receipt_sha256="target-cycle-sha",
            release_path=tmp_path / "state" / "APPLICATION_READY_TARGET.json",
        )
