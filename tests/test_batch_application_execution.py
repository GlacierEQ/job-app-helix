from __future__ import annotations

from pathlib import Path

from job_app_helix.application_engine import CompanyTarget, RepositoryProof
from job_app_helix.application_operations import ApplicationStore, CandidateProfile, JobOpening
from job_app_helix.batch_application_execution import compile_ranked_application_batch


def _proof(name: str) -> RepositoryProof:
    return RepositoryProof(
        repository=name,
        level="L4",
        state="PROMOTED",
        visibility="public",
        admission="HELIX_ADMITTED",
        origin="batch-test",
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
        source_digest="batch-profile",
    )


def _opening(opening_id: str, requirements: tuple[str, ...]) -> JobOpening:
    return JobOpening(
        opening_id=opening_id,
        company="Acme",
        title="AI Systems Engineer",
        description="Build reliable agent systems and platform automation.",
        location="Remote",
        source="test",
        source_url=f"https://example.invalid/jobs/{opening_id}",
        requirements=requirements,
        preferred=("distributed systems",),
        digest=f"digest-{opening_id}",
    )


def test_batch_compiles_only_actionable_lanes_and_deduplicates_complete_packets(
    tmp_path: Path,
) -> None:
    profile = _profile()
    target = _target()
    strong = _opening("strong", ("Python", "agent systems", "observability"))
    hard_gap = _opening(
        "hard-gap",
        ("Python", "CUDA", "ASIC design", "compiler kernels"),
    )
    candidates = (
        (hard_gap, target, None, None),
        (strong, target, None, None),
    )
    output_dir = tmp_path / "packets"
    database = tmp_path / "applications.sqlite3"

    with ApplicationStore(database) as store:
        first = compile_ranked_application_batch(
            candidates,
            profile,
            output_dir=output_dir,
            store=store,
        )
        assert first.selected_count == 1
        assert first.compiled_count == 1
        assert first.deduplicated_count == 0
        assert first.skipped_count == 1
        packet = first.packets[0]
        assert packet.opening_id == "strong"
        assert packet.lane == "APPLY_NOW"
        assert packet.status == "READY"
        assert packet.deduplicated is False
        packet_dir = Path(packet.packet_dir)
        assert (packet_dir / "RESUME.md").is_file()
        assert (packet_dir / "STRATEGY_RECEIPT.json").is_file()
        assert (packet_dir / "submission" / "SUBMISSION_PACKET.json").is_file()
        assert len(store.list_applications()) == 1

        second = compile_ranked_application_batch(
            candidates,
            profile,
            output_dir=output_dir,
            store=store,
        )
        assert second.selected_count == 1
        assert second.compiled_count == 0
        assert second.deduplicated_count == 1
        assert second.packets[0].application_id == packet.application_id
        assert second.packets[0].deduplicated is True
        assert len(store.list_applications()) == 1
        assert store.events(packet.application_id)[0]["event_type"] == "CREATED"
        assert len(store.events(packet.application_id)) == 1


def test_batch_limit_preserves_queue_order_and_never_marks_submission(tmp_path: Path) -> None:
    profile = _profile()
    target = _target()
    strongest = _opening("a-strong", ("Python", "agent systems", "observability"))
    viable = _opening("b-viable", ("Python", "agent systems"))
    output_dir = tmp_path / "packets"

    with ApplicationStore(tmp_path / "apps.sqlite3") as store:
        result = compile_ranked_application_batch(
            (
                (viable, target, None, None),
                (strongest, target, None, None),
            ),
            profile,
            output_dir=output_dir,
            store=store,
            actionable_lanes=("APPLY_NOW", "APPLY_NEXT"),
            limit=1,
        )
        assert result.selected_count == 1
        assert result.packets[0].opening_id == "a-strong"
        record = store.get_application(result.packets[0].application_id)
        assert record["status"] == "READY"
        assert record["external_reference"] is None
