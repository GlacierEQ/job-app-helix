from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from job_app_helix.application_engine import find_target, load_targets
from job_app_helix.application_operations import (
    ApplicationStore,
    compile_application_lifecycle,
    ingest_job_opening,
    ingest_job_opening_url,
    load_candidate_profile,
    match_opening,
    project_application,
)

ROOT = Path(__file__).resolve().parents[1]


def _targets():
    return load_targets(ROOT / "manifests")


def _opening():
    return ingest_job_opening(
        {
            "company": "Anthropic",
            "title": "Safety Systems Engineer",
            "description": (
                "Build reliable AI safety systems, Python services, evaluation "
                "pipelines, distributed infrastructure, observability, and "
                "failure recovery."
            ),
            "location": "San Francisco, CA",
            "requirements": [
                "Python",
                "AI safety",
                "systems architecture",
                "evaluation",
                "observability",
            ],
        }
    )


def _profile_file(tmp_path: Path) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(
        json.dumps(
            {
                "name": "Casey Barton",
                "headline": "Systems architect and full-stack developer",
                "summary": (
                    "I build evidence-grounded automation, AI evaluation, and "
                    "reliable software execution systems."
                ),
                "skills": [
                    "Python",
                    "AI safety evaluation",
                    "systems architecture",
                    "observability",
                    "distributed systems",
                ],
                "experience": [
                    (
                        "Built execution systems with deterministic receipts and "
                        "failure recovery."
                    ),
                    (
                        "Designed full-stack automation and evidence-grounded "
                        "data workflows."
                    ),
                ],
                "achievements": [
                    (
                        "Developed public technical repositories demonstrating "
                        "agent coordination."
                    )
                ],
                "contact": {"location": "Honolulu, Hawaii"},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_job_opening_ingestion_is_content_addressed() -> None:
    first = _opening()
    second = _opening()
    assert first.opening_id == second.opening_id
    assert first.digest == second.digest
    assert first.requirements[0] == "Python"


def test_live_job_url_ingests_json_ld_jobposting() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "JobPosting",
                    "title": "Safety Systems Engineer",
                    "description": "<p>Build AI safety evaluation systems.</p>",
                    "hiringOrganization": {"name": "Anthropic"},
                    "jobLocation": {
                        "address": {
                            "addressLocality": "San Francisco",
                            "addressRegion": "CA",
                        }
                    },
                    "qualifications": ["Python", "AI safety"],
                }
            ).encode()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/ld+json; charset=utf-8",
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        opening = ingest_job_opening_url(
            f"http://127.0.0.1:{server.server_port}/jobs/1"
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert opening.company == "Anthropic"
    assert opening.title == "Safety Systems Engineer"
    assert "AI safety evaluation systems" in opening.description
    assert opening.source == "url"


def test_matching_uses_candidate_evidence_and_public_proof(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(_profile_file(tmp_path))
    target = find_target("anthropic", _targets())
    match = match_opening(
        _opening(),
        target,
        profile,
        mapped_role="Safety Systems Engineer",
    )
    assert match.role_score == 1.0
    assert match.proof_score > 0
    assert "python" in match.matched_terms
    assert match.recommendation in {"STRONG_MATCH", "VIABLE_MATCH"}
    assert len(match.digest) == 64


def test_projection_uses_only_profile_claims_and_admitted_repositories(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(_profile_file(tmp_path))
    target = find_target("anthropic", _targets())
    kit, _, projection = project_application(
        _opening(),
        target,
        profile,
        role="Safety Systems Engineer",
    )
    assert (
        "Built execution systems with deterministic receipts"
        in projection.resume_markdown
    )
    assert "GlacierEQ/anthropic-agent-coordinator" in projection.resume_markdown
    assert kit.non_affiliation in projection.cover_letter_markdown
    assert any(
        source.startswith("candidate-profile:")
        for source in projection.claim_sources
    )
    assert all(
        row["repository"] in projection.claim_sources
        for row in kit.proof_repositories
    )


def test_full_lifecycle_prepares_exact_artifact_set_without_collapsing(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(_profile_file(tmp_path))
    target = find_target("anthropic", _targets())
    db = tmp_path / "operations.sqlite3"
    output = tmp_path / "applications"

    with ApplicationStore(db) as store:
        packet = compile_application_lifecycle(
            _opening(),
            target,
            profile,
            output_dir=output,
            store=store,
            role="Safety Systems Engineer",
        )
        application_id = packet["application_id"]
        row = store.get_application(application_id)
        assert row["status"] == "READY"
        assert (
            packet["adapter_receipt"]["status"]
            == "READY_FOR_MANUAL_SUBMISSION"
        )
        assert packet["adapter_receipt"]["submission_performed"] is False
        assert packet["adapter_receipt"]["artifact_count"] == len(packet["artifacts"])
        assert packet["adapter_receipt"]["artifact_count"] > 1
        assert Path(packet["adapter_receipt"]["artifact"]).name == (
            "ARTIFACT_SET_MANIFEST.json"
        )
        for artifact in packet["artifacts"].values():
            assert Path(artifact).is_file()

        with pytest.raises(ValueError, match="invalid application status: SUBMITTED"):
            store.transition(application_id, "SUBMITTED")

        store.record_feedback(
            application_id,
            "submission_transport_removed",
            "External submission transport is intentionally absent.",
        )

        assert store.get_application(application_id)["status"] == "READY"
        event_types = [
            event["event_type"] for event in store.events(application_id)
        ]
        assert event_types == ["CREATED", "FEEDBACK"]
        summary = store.feedback_summary()
        assert summary["applications"] == 1
        assert summary["response_events"] == 0
        assert summary["feedback_events"] == 1


def test_recompiling_same_projection_is_idempotent(tmp_path: Path) -> None:
    profile = load_candidate_profile(_profile_file(tmp_path))
    target = find_target("anthropic", _targets())
    opening = _opening()
    output = tmp_path / "out"

    with ApplicationStore(tmp_path / "operations.sqlite3") as store:
        first = compile_application_lifecycle(
            opening,
            target,
            profile,
            output_dir=output,
            store=store,
        )
        second = compile_application_lifecycle(
            opening,
            target,
            profile,
            output_dir=output,
            store=store,
        )
        assert first["application_id"] == second["application_id"]
        assert len(store.list_applications()) == 1
        events = store.events(first["application_id"])
        assert [event["event_type"] for event in events] == ["CREATED"]


def test_external_reference_cannot_create_submission_state(tmp_path: Path) -> None:
    profile = load_candidate_profile(_profile_file(tmp_path))
    target = find_target("anthropic", _targets())
    with ApplicationStore(tmp_path / "operations.sqlite3") as store:
        packet = compile_application_lifecycle(
            _opening(),
            target,
            profile,
            output_dir=tmp_path / "out",
            store=store,
        )
        with pytest.raises(ValueError, match="external_reference may not mutate"):
            store.transition(
                packet["application_id"],
                "READY",
                external_reference="ats-123",
            )
        assert store.get_application(packet["application_id"])["status"] == "READY"
