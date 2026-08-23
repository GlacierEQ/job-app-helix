from __future__ import annotations

from pathlib import Path

import pytest

from job_app_helix.submission_integrity import (
    SubmissionIntegrityError,
    build_artifact_set,
    verify_external_submission_receipt,
)


def _packet(tmp_path: Path) -> dict[str, object]:
    resume = tmp_path / "RESUME.md"
    cover = tmp_path / "COVER_LETTER.md"
    resume.write_text("resume\n", encoding="utf-8")
    cover.write_text("cover\n", encoding="utf-8")
    return {
        "application_id": "app-artifact-set-test",
        "artifacts": {
            "resume": str(resume),
            "cover_letter": str(cover),
        },
    }


def test_build_artifact_set_preserves_multiplicity(tmp_path: Path) -> None:
    artifact_set = build_artifact_set(_packet(tmp_path))

    assert len(artifact_set.artifacts) == 2
    assert {item.name for item in artifact_set.artifacts} == {
        "resume",
        "cover_letter",
    }
    assert len(artifact_set.digest) == 64


def test_one_file_collapse_is_rejected(tmp_path: Path) -> None:
    only = tmp_path / "SUBMISSION_PACKET.json"
    only.write_text("{}\n", encoding="utf-8")

    with pytest.raises(SubmissionIntegrityError, match="at least two"):
        build_artifact_set(
            {
                "application_id": "app-collapsed",
                "artifacts": {"packet": str(only)},
            }
        )


def test_external_receipt_must_match_exact_artifact_set(tmp_path: Path) -> None:
    artifact_set = build_artifact_set(_packet(tmp_path))
    accepted = [
        {"name": item.name, "sha256": item.sha256}
        for item in artifact_set.artifacts
    ]
    verified = verify_external_submission_receipt(
        artifact_set,
        {
            "status": "ACCEPTED_ARTIFACT_SET_VERIFIED",
            "external_reference": "ats-verified-1",
            "artifact_set_digest": artifact_set.digest,
            "accepted_artifacts": accepted,
        },
    )

    assert verified["status"] == "SUBMITTED_VERIFIED"
    assert verified["accepted_artifact_count"] == 2


def test_http_success_shape_without_artifact_receipt_is_rejected(
    tmp_path: Path,
) -> None:
    artifact_set = build_artifact_set(_packet(tmp_path))

    with pytest.raises(SubmissionIntegrityError, match="does not prove"):
        verify_external_submission_receipt(
            artifact_set,
            {
                "status": "SUBMITTED",
                "http_status": 201,
                "external_reference": "ats-123",
            },
        )


def test_missing_accepted_artifact_is_rejected(tmp_path: Path) -> None:
    artifact_set = build_artifact_set(_packet(tmp_path))
    first = artifact_set.artifacts[0]

    with pytest.raises(SubmissionIntegrityError, match="changed the intended"):
        verify_external_submission_receipt(
            artifact_set,
            {
                "status": "ACCEPTED_ARTIFACT_SET_VERIFIED",
                "external_reference": "ats-partial",
                "artifact_set_digest": artifact_set.digest,
                "accepted_artifacts": [
                    {"name": first.name, "sha256": first.sha256}
                ],
            },
        )
