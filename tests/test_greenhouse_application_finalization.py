from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from job_app_helix.greenhouse_application_finalization import (
    GreenhouseApplicationFinalizationError,
    finalize_greenhouse_application,
)


def _packet(tmp_path: Path) -> tuple[Path, Path]:
    packet = tmp_path / "packet"
    packet.mkdir()
    field_bundle = {
        "schema": "glaciereq.greenhouse-application-fields.v1",
        "job_id": "4956028007",
        "receipt_sha256": "field-receipt",
        "fields": [
            {
                "field": {
                    "label": "First Name",
                    "name": "first_name",
                    "field_type": "input_text",
                    "required": True,
                    "options": [],
                    "category": "questions",
                },
                "status": "AUTO_FILL",
                "value": "Casey",
                "provenance": "CandidateProfile.name",
                "reason": "Exact profile name evidence.",
            },
            {
                "field": {
                    "label": "Resume/CV",
                    "name": "resume",
                    "field_type": "input_file",
                    "required": True,
                    "options": [],
                    "category": "questions",
                },
                "status": "ATTACHMENT_REQUIRED",
                "value": None,
                "provenance": None,
                "reason": "Attachment required.",
            },
            {
                "field": {
                    "label": "What exceptional work have you done?",
                    "name": "question_exceptional",
                    "field_type": "textarea",
                    "required": True,
                    "options": [],
                    "category": "questions",
                },
                "status": "REVIEW_REQUIRED",
                "value": None,
                "provenance": None,
                "reason": "Applicant review required.",
            },
            {
                "field": {
                    "label": "Internal token",
                    "name": "internal_token",
                    "field_type": "input_hidden",
                    "required": True,
                    "options": [],
                    "category": "questions",
                },
                "status": "PROVIDER_MANAGED",
                "value": None,
                "provenance": None,
                "reason": "Provider managed.",
            },
        ],
    }
    (packet / "GREENHOUSE_APPLICATION_FIELDS.json").write_text(
        json.dumps(field_bundle), encoding="utf-8"
    )
    preparation = {
        "schema": "glaciereq.greenhouse-application-preparation.v2",
        "application_id": "app-xai-1",
        "opening_id": "4956028007",
        "packet_dir": str(packet),
        "release_receipt_sha256": "release-receipt",
        "field_bundle_receipt_sha256": "field-receipt",
        "receipt_sha256": "preparation-receipt",
        "prompts": [
            {
                "field_name": "first_name",
                "label": "First Name",
                "status": "AUTO_FILL_VERIFIED",
                "draft": "Casey",
                "provenance": ["CandidateProfile.name"],
                "reason": "Exact profile evidence.",
            },
            {
                "field_name": "resume",
                "label": "Resume/CV",
                "status": "ATTACHMENT_REQUIRED",
                "draft": None,
                "provenance": [],
                "reason": "Attachment required.",
            },
            {
                "field_name": "question_exceptional",
                "label": "What exceptional work have you done?",
                "status": "APPLICANT_CONFIRMED",
                "draft": "I built source-bound systems with deterministic recovery proofs.",
                "provenance": ["applicant-confirmed:exceptional-work"],
                "reason": "Applicant confirmed.",
            },
            {
                "field_name": "internal_token",
                "label": "Internal token",
                "status": "PROVIDER_MANAGED",
                "draft": None,
                "provenance": [],
                "reason": "Provider managed.",
            },
        ],
    }
    preparation_path = packet / "GREENHOUSE_APPLICATION_PREPARATION.json"
    preparation_path.write_text(json.dumps(preparation), encoding="utf-8")
    return packet, preparation_path


def _attachment_source(tmp_path: Path, artifact: Path, *, field_name: str = "resume") -> Path:
    source = tmp_path / "attachments.json"
    source.write_text(
        json.dumps(
            {
                "attachments": [
                    {
                        "field_name": field_name,
                        "path": str(artifact),
                        "provenance": "production-resume",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return source


def test_hash_binds_required_attachment_and_marks_packet_ready(tmp_path: Path) -> None:
    packet, preparation = _packet(tmp_path)
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"production resume bytes")
    source = _attachment_source(tmp_path, resume)

    result = finalize_greenhouse_application(
        preparation,
        attachment_sources=(source,),
    )

    assert result.ready_for_human_submission is True
    assert result.required_field_count == 3
    assert result.resolved_required_count == 3
    assert result.unresolved_required_fields == ()
    assert (packet / "GREENHOUSE_APPLICATION_FINAL.json").is_file()

    by_name = {item.field_name: item for item in result.fields}
    assert by_name["first_name"].status == "ANSWER_BOUND"
    assert by_name["question_exceptional"].status == "ANSWER_BOUND"
    assert by_name["internal_token"].status == "PROVIDER_MANAGED"
    attachment = by_name["resume"].attachment
    assert attachment is not None
    assert by_name["resume"].status == "ATTACHMENT_BOUND"
    assert attachment.sha256 == hashlib.sha256(resume.read_bytes()).hexdigest()
    assert attachment.size_bytes == len(resume.read_bytes())


def test_missing_required_attachment_blocks_readiness_without_fabricating_path(tmp_path: Path) -> None:
    packet, preparation = _packet(tmp_path)

    result = finalize_greenhouse_application(preparation)

    assert result.ready_for_human_submission is False
    assert result.unresolved_required_fields == ("resume",)
    by_name = {item.field_name: item for item in result.fields}
    assert by_name["resume"].status == "UNRESOLVED_REQUIRED"
    assert by_name["resume"].attachment is None
    assert (packet / "GREENHOUSE_APPLICATION_FINAL.json").is_file()


def test_draft_review_required_does_not_satisfy_required_field(tmp_path: Path) -> None:
    packet, preparation = _packet(tmp_path)
    payload = json.loads(preparation.read_text(encoding="utf-8"))
    exceptional = next(
        row for row in payload["prompts"] if row["field_name"] == "question_exceptional"
    )
    exceptional["status"] = "DRAFT_REVIEW_REQUIRED"
    preparation.write_text(json.dumps(payload), encoding="utf-8")
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"resume")

    result = finalize_greenhouse_application(
        preparation,
        attachment_sources=(_attachment_source(tmp_path, resume),),
    )

    assert result.ready_for_human_submission is False
    assert result.unresolved_required_fields == ("question_exceptional",)
    assert (packet / "GREENHOUSE_APPLICATION_FINAL.json").is_file()


def test_lineage_mismatch_fails_before_final_artifact_mutation(tmp_path: Path) -> None:
    packet, preparation = _packet(tmp_path)
    payload = json.loads(preparation.read_text(encoding="utf-8"))
    payload["field_bundle_receipt_sha256"] = "stale-receipt"
    preparation.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(GreenhouseApplicationFinalizationError, match="lineage mismatch"):
        finalize_greenhouse_application(preparation)

    assert not (packet / "GREENHOUSE_APPLICATION_FINAL.json").exists()


def test_attachment_rejects_unknown_or_non_file_live_field_before_write(tmp_path: Path) -> None:
    packet, preparation = _packet(tmp_path)
    artifact = tmp_path / "resume.pdf"
    artifact.write_bytes(b"resume")
    source = _attachment_source(tmp_path, artifact, field_name="first_name")

    with pytest.raises(GreenhouseApplicationFinalizationError, match="non-file live field"):
        finalize_greenhouse_application(preparation, attachment_sources=(source,))

    assert not (packet / "GREENHOUSE_APPLICATION_FINAL.json").exists()
