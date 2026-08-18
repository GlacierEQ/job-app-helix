from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from job_app_helix.application_engine import CompanyTarget, RepositoryProof
from job_app_helix.application_operations import ApplicationStore, CandidateProfile, JobOpening
from job_app_helix.freshness_aware_batch import compile_freshness_aware_batch


def _proof(name: str) -> RepositoryProof:
    return RepositoryProof(
        repository=name,
        level="L4",
        state="PROMOTED",
        visibility="public",
        admission="HELIX_ADMITTED",
        origin="freshness-test",
    )


def _target() -> CompanyTarget:
    return CompanyTarget(
        company_id="acme",
        display_name="Acme",
        track_state="ACTIVE",
        target_roles=("AI Systems Engineer",),
        recruiter_thesis="agent systems reliability observability",
        gap_or_next_gate="none",
        non_affiliation="Independent project work; no affiliation claimed.",
        repositories=(
            _proof("GlacierEQ/pro-code"),
            _proof("GlacierEQ/Pro_Code"),
            _proof("GlacierEQ/job-app-helix"),
        ),
    )


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="casey",
        name="Casey",
        headline="AI systems engineer",
        summary="Builds reliable agent systems with observability and Python automation.",
        skills=("Python", "agent systems", "observability", "distributed systems"),
        experience=("Built production agent orchestration and recovery systems",),
        achievements=("Designed evidence-bound automation with runtime verification",),
        source_digest="freshness-profile",
    )


def _opening() -> JobOpening:
    return JobOpening(
        opening_id="live-role",
        company="Acme",
        title="AI Systems Engineer",
        description="Build reliable agent systems and platform automation.",
        location="Remote",
        source="url",
        source_url="https://example.invalid/jobs/live-role",
        requirements=("Python", "agent systems", "observability"),
        preferred=("distributed systems",),
        digest="opening-digest-v1",
    )


def _input_receipt(packet_dir: str) -> dict[str, object]:
    path = Path(packet_dir) / "OPENING_INPUT_RECEIPT.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_same_opening_digest_reuses_complete_packet(tmp_path: Path) -> None:
    opening = _opening()
    candidate = ((opening, _target(), None, None),)
    output_dir = tmp_path / "packets"

    with ApplicationStore(tmp_path / "apps.sqlite3") as store:
        first = compile_freshness_aware_batch(
            candidate,
            _profile(),
            output_dir=output_dir,
            store=store,
        )
        second = compile_freshness_aware_batch(
            candidate,
            _profile(),
            output_dir=output_dir,
            store=store,
        )

    assert first.batch.compiled_count == 1
    assert second.batch.compiled_count == 0
    assert second.batch.deduplicated_count == 1
    assert second.reused_count == 1
    assert second.refreshed_count == 0
    assert second.decisions[0].action == "REUSE_CURRENT"
    receipt = _input_receipt(second.batch.packets[0].packet_dir)
    assert receipt["opening_digest"] == "opening-digest-v1"
    assert len(str(receipt["receipt_sha256"])) == 64


def test_changed_opening_digest_quarantines_and_rebuilds_stale_packet(tmp_path: Path) -> None:
    original = _opening()
    changed = replace(original, digest="opening-digest-v2")
    output_dir = tmp_path / "packets"
    database = tmp_path / "apps.sqlite3"

    with ApplicationStore(database) as store:
        first = compile_freshness_aware_batch(
            ((original, _target(), None, None),),
            _profile(),
            output_dir=output_dir,
            store=store,
        )
        application_id = first.batch.packets[0].application_id
        packet_dir = Path(first.batch.packets[0].packet_dir)
        marker = packet_dir / "STALE_MARKER.txt"
        marker.write_text("old packet", encoding="utf-8")

        second = compile_freshness_aware_batch(
            ((changed, _target(), None, None),),
            _profile(),
            output_dir=output_dir,
            store=store,
        )

    decision = second.decisions[0]
    assert decision.application_id == application_id
    assert decision.action == "REFRESH_STALE"
    assert decision.previous_digest == "opening-digest-v1"
    assert second.refreshed_count == 1
    assert second.batch.compiled_count == 1
    assert second.batch.deduplicated_count == 0
    assert decision.quarantine_path is not None
    quarantine = Path(decision.quarantine_path)
    assert quarantine.is_dir()
    assert (quarantine / "STALE_MARKER.txt").read_text(encoding="utf-8") == "old packet"
    fresh_packet = Path(second.batch.packets[0].packet_dir)
    assert fresh_packet.is_dir()
    assert not (fresh_packet / "STALE_MARKER.txt").exists()
    receipt = _input_receipt(str(fresh_packet))
    assert receipt["opening_digest"] == "opening-digest-v2"


def test_unbound_legacy_packet_is_refreshed_once_and_preserved(tmp_path: Path) -> None:
    opening = _opening()
    output_dir = tmp_path / "packets"

    with ApplicationStore(tmp_path / "apps.sqlite3") as store:
        first = compile_freshness_aware_batch(
            ((opening, _target(), None, None),),
            _profile(),
            output_dir=output_dir,
            store=store,
        )
        packet_dir = Path(first.batch.packets[0].packet_dir)
        (packet_dir / "OPENING_INPUT_RECEIPT.json").unlink()

        second = compile_freshness_aware_batch(
            ((opening, _target(), None, None),),
            _profile(),
            output_dir=output_dir,
            store=store,
        )

    assert second.decisions[0].action == "REFRESH_STALE"
    assert second.decisions[0].previous_digest is None
    assert second.batch.compiled_count == 1
    assert second.decisions[0].quarantine_path is not None
    assert Path(second.decisions[0].quarantine_path).is_dir()
