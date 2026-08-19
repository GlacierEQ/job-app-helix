from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from job_app_helix.application_operations import CandidateProfile
from job_app_helix.greenhouse_application_preparation import (
    GreenhouseApplicationPreparationError,
    prepare_greenhouse_application_release,
)


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="casey-production",
        name="Casey Barton",
        headline="Systems architect",
        summary="Builds evidence-bound software systems.",
        skills=("Python", "TypeScript", "Rust"),
        experience=("Built production-grade job application intelligence pipelines.",),
        achievements=(
            "Designed a deterministic recovery engine for stranded repository capability.",
            "Built source-bound recruiter packet generation with exact opening lineage.",
        ),
        contact={"email": "casey@example.com", "github": "https://github.com/GlacierEQ"},
        source_digest="profile-digest",
    )


def _release(tmp_path: Path, *, opening_id: str = "4956028007") -> Path:
    packet = tmp_path / "packet"
    packet.mkdir()
    release = {
        "schema": "glaciereq.application-ready-release.v1",
        "receipt_sha256": "release-receipt",
        "selected": {
            "application_id": "app-xai-1",
            "opening_id": opening_id,
            "packet_dir": str(packet),
        },
    }
    path = tmp_path / "APPLICATION_READY_TARGET.json"
    path.write_text(json.dumps(release), encoding="utf-8")
    return path


def _transport(url: str) -> dict[str, object]:
    assert url.endswith("/4956028007?questions=true")
    return {
        "id": 4956028007,
        "questions": [
            {
                "label": "First Name",
                "required": True,
                "fields": [{"name": "first_name", "type": "input_text"}],
            },
            {
                "label": "What exceptional work have you done?",
                "required": True,
                "fields": [{"name": "question_exceptional", "type": "textarea"}],
            },
            {
                "label": "Will you now or in the future require sponsorship?",
                "required": True,
                "fields": [{"name": "question_sponsorship", "type": "input_text"}],
            },
        ],
        "compliance": [],
        "location_questions": [],
    }


def test_prepares_application_ready_packet_with_source_bound_custom_draft(tmp_path: Path) -> None:
    release = _release(tmp_path)
    evidence = tmp_path / "xai.md"
    evidence.write_text(
        "| Thread | Claim support | Artifacts | Precise claim | Limit |\n"
        "|---|---|---|---|---|\n"
        "| xai-colossus-energy | **Directly supported** | src + tests | "
        "Typed scenario calculation of PUE-derived overhead and capacity headroom. | "
        "No live telemetry. |\n",
        encoding="utf-8",
    )

    result = prepare_greenhouse_application_release(
        release,
        _profile(),
        board_key="xai",
        job_id="4956028007",
        evidence_sources=(evidence,),
        output_path=tmp_path / "prepared.json",
        transport=_transport,
    )

    packet = tmp_path / "packet"
    assert (packet / "GREENHOUSE_APPLICATION_FIELDS.json").is_file()
    assert (packet / "GREENHOUSE_APPLICATION_PREPARATION.json").is_file()
    assert (tmp_path / "prepared.json").is_file()
    assert result.application_id == "app-xai-1"
    assert result.opening_id == "4956028007"
    assert result.drafted_count == 1

    by_name = {item.field_name: item for item in result.prompts}
    assert by_name["first_name"].status == "AUTO_FILL_VERIFIED"
    assert by_name["first_name"].draft == "Casey"
    exceptional = by_name["question_exceptional"]
    assert exceptional.status == "DRAFT_REVIEW_REQUIRED"
    assert "deterministic recovery engine" in (exceptional.draft or "")
    assert "source-bound recruiter packet generation" in (exceptional.draft or "")
    assert exceptional.provenance[:2] == (
        "CandidateProfile.achievements[0]",
        "CandidateProfile.achievements[1]",
    )
    assert by_name["question_sponsorship"].status == "REVIEW_REQUIRED"
    assert by_name["question_sponsorship"].draft is None

    source_claims = [
        item
        for item in result.evidence
        if item.evidence_class == "source_reviewed_portfolio_claim"
    ]
    assert len(source_claims) == 1
    assert source_claims[0].source_sha256 == hashlib.sha256(evidence.read_bytes()).hexdigest()


def test_release_identity_drift_fails_before_packet_mutation(tmp_path: Path) -> None:
    release = _release(tmp_path, opening_id="different-job")

    with pytest.raises(GreenhouseApplicationPreparationError, match="identity drift"):
        prepare_greenhouse_application_release(
            release,
            _profile(),
            board_key="xai",
            job_id="4956028007",
            transport=_transport,
        )

    packet = tmp_path / "packet"
    assert not (packet / "GREENHOUSE_APPLICATION_FIELDS.json").exists()
    assert not (packet / "GREENHOUSE_APPLICATION_PREPARATION.json").exists()


def test_sensitive_provider_field_remains_applicant_decision(tmp_path: Path) -> None:
    release = _release(tmp_path)

    def sensitive_transport(url: str) -> dict[str, object]:
        payload = _transport(url)
        payload["compliance"] = [
            {
                "label": "Veteran status",
                "required": False,
                "fields": [{"name": "veteran_status", "type": "input_text"}],
            }
        ]
        return payload

    result = prepare_greenhouse_application_release(
        release,
        _profile(),
        board_key="xai",
        job_id="4956028007",
        transport=sensitive_transport,
    )

    veteran = next(item for item in result.prompts if item.field_name == "veteran_status")
    assert veteran.status == "USER_DECISION_REQUIRED"
    assert veteran.draft is None
    assert veteran.provenance == ()
