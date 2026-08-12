from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from job_app_helix.application_engine import find_target, load_targets
from job_app_helix.application_operations import (
    ApplicationStore,
    JsonApiApplicationAdapter,
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
                "Build reliable AI safety systems, Python services, "
                "evaluation pipelines, distributed infrastructure, "
                "observability, and failure recovery."
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
                "headline": (
                    "Systems architect and full-stack developer"
                ),
                "summary": (
                    "I build evidence-grounded automation, "
                    "AI evaluation, and reliable software "
                    "execution systems."
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
                        "Built execution systems with deterministic "
                        "receipts and failure recovery."
                    ),
                    (
                        "Designed full-stack automation and "
                        "evidence-grounded data workflows."
                    ),
                ],
                "achievements": [
                    (
                        "Developed public technical repositories "
                        "demonstrating agent coordination."
                    )
                ],
                "contact": {
                    "location": "Honolulu, Hawaii"
                },
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
                    "description": (
                        "<p>Build AI safety evaluation systems.</p>"
                    ),
                    "hiringOrganization": {
                        "name": "Anthropic"
                    },
                    "jobLocation": {
                        "address": {
                            "addressLocality": "San Francisco",
                            "addressRegion": "CA",
                        }
                    },
                    "qualifications": [
                        "Python",
                        "AI safety",
                    ],
                }
            ).encode()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/ld+json; charset=utf-8",
            )
            self.send_header(
                "Content-Length",
                str(len(body)),
            )
            self.end_headers()
            self.wfile.write(body)

        def log_message(
            self,
            *_: object,
        ) -> None:
            return

    server = HTTPServer(
        ("127.0.0.1", 0),
        Handler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    try:
        opening = ingest_job_opening_url(
            (
                "http://127.0.0.1:"
                f"{server.server_port}/jobs/1"
            )
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert opening.company == "Anthropic"
    assert opening.title == "Safety Systems Engineer"
    assert (
        "AI safety evaluation systems"
        in opening.description
    )
    assert opening.source == "url"


def test_matching_uses_candidate_evidence_and_public_proof(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(
        _profile_file(tmp_path)
    )
    target = find_target(
        "anthropic",
        _targets(),
    )
    match = match_opening(
        _opening(),
        target,
        profile,
        mapped_role="Safety Systems Engineer",
    )
    assert match.role_score == 1.0
    assert match.proof_score > 0
    assert "python" in match.matched_terms
    assert match.recommendation in {
        "STRONG_MATCH",
        "VIABLE_MATCH",
    }
    assert len(match.digest) == 64


def test_projection_uses_only_profile_claims_and_admitted_repositories(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(
        _profile_file(tmp_path)
    )
    target = find_target(
        "anthropic",
        _targets(),
    )
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
    assert (
        "GlacierEQ/anthropic-agent-coordinator"
        in projection.resume_markdown
    )
    assert (
        kit.non_affiliation
        in projection.cover_letter_markdown
    )
    assert any(
        source.startswith("candidate-profile:")
        for source in projection.claim_sources
    )
    assert all(
        row["repository"]
        in projection.claim_sources
        for row in kit.proof_repositories
    )


def test_full_lifecycle_writes_packet_and_tracks_response(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(
        _profile_file(tmp_path)
    )
    target = find_target(
        "anthropic",
        _targets(),
    )
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
        application_id = packet[
            "application_id"
        ]
        row = store.get_application(
            application_id
        )
        assert row["status"] == "READY"
        assert (
            packet["adapter_receipt"]["status"]
            == "READY_FOR_MANUAL_SUBMISSION"
        )
        assert (
            packet["adapter_receipt"][
                "submission_performed"
            ]
            is False
        )
        for path in packet[
            "artifacts"
        ].values():
            assert Path(path).is_file()

        store.transition(
            application_id,
            "SUBMITTED",
            external_reference="ats-123",
        )
        store.record_response(
            application_id,
            "interview",
            (
                "Recruiter requested a "
                "technical interview."
            ),
            source_reference="email-message-42",
        )
        store.record_feedback(
            application_id,
            "positive",
            "Interview requested.",
        )
        assert (
            store.get_application(
                application_id
            )["status"]
            == "INTERVIEW"
        )
        event_types = [
            event["event_type"]
            for event in store.events(
                application_id
            )
        ]
        assert event_types == [
            "CREATED",
            "STATUS_CHANGED",
            "RESPONSE",
            "STATUS_CHANGED",
            "FEEDBACK",
        ]
        summary = store.feedback_summary()
        assert summary["applications"] == 1
        assert summary["response_events"] == 1
        assert summary["feedback_events"] == 1


def test_submitted_state_requires_external_receipt(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(
        _profile_file(tmp_path)
    )
    target = find_target(
        "anthropic",
        _targets(),
    )
    with ApplicationStore(
        tmp_path / "operations.sqlite3"
    ) as store:
        packet = compile_application_lifecycle(
            _opening(),
            target,
            profile,
            output_dir=tmp_path / "out",
            store=store,
        )
        with pytest.raises(
            ValueError,
            match="external_reference",
        ):
            store.transition(
                packet["application_id"],
                "SUBMITTED",
            )


def test_json_api_adapter_requires_explicit_submission(
    tmp_path: Path,
) -> None:
    received: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(
                self.headers["Content-Length"]
            )
            received.append(
                json.loads(
                    self.rfile.read(length)
                )
            )
            body = (
                b'{"application_id":"remote-7"}'
            )
            self.send_response(201)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Content-Length",
                str(len(body)),
            )
            self.end_headers()
            self.wfile.write(body)

        def log_message(
            self,
            *_: object,
        ) -> None:
            return

    server = HTTPServer(
        ("127.0.0.1", 0),
        Handler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    try:
        adapter = JsonApiApplicationAdapter(
            (
                "http://127.0.0.1:"
                f"{server.server_port}/applications"
            )
        )
        packet = {
            "application_id": "app-1",
            "role": "Safety Systems Engineer",
        }
        prepared = adapter.prepare(
            packet,
            tmp_path,
        )
        dry_run = adapter.submit(packet)
        assert prepared["status"] == "READY"
        assert dry_run["status"] == "DRY_RUN"
        assert (
            dry_run["submission_performed"]
            is False
        )
        assert received == []
        submitted = adapter.submit(
            packet,
            submit=True,
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert submitted["status"] == "SUBMITTED"
    assert submitted["http_status"] == 201
    assert received == [
        {
            "application_id": "app-1",
            "role": "Safety Systems Engineer",
        }
    ]
