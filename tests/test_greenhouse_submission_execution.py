from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from job_app_helix.greenhouse_submission_execution import (
    GreenhouseSubmissionError,
    build_greenhouse_submission_plan,
    execute_greenhouse_submission,
)


def _ready_packet(tmp_path: Path) -> tuple[Path, Path]:
    packet = tmp_path / "packet"
    packet.mkdir()
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"production resume bytes")
    resume_sha = hashlib.sha256(resume.read_bytes()).hexdigest()
    field_bundle = {
        "schema": "glaciereq.greenhouse-application-fields.v1",
        "board_key": "xai",
        "job_id": "4956028007",
        "source_url": (
            "https://boards-api.greenhouse.io/v1/boards/xai/jobs/4956028007?questions=true"
        ),
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
                }
            },
            {
                "field": {
                    "label": "Resume/CV",
                    "name": "resume",
                    "field_type": "input_file",
                    "required": True,
                    "options": [],
                    "category": "questions",
                }
            },
            {
                "field": {
                    "label": "Exceptional work",
                    "name": "question_exceptional",
                    "field_type": "textarea",
                    "required": True,
                    "options": [],
                    "category": "questions",
                }
            },
            {
                "field": {
                    "label": "Internal token",
                    "name": "internal_token",
                    "field_type": "input_hidden",
                    "required": True,
                    "options": [],
                    "category": "questions",
                }
            },
        ],
    }
    (packet / "GREENHOUSE_APPLICATION_FIELDS.json").write_text(
        json.dumps(field_bundle), encoding="utf-8"
    )
    finalization = {
        "schema": "glaciereq.greenhouse-application-finalization.v1",
        "application_id": "app-xai-1",
        "opening_id": "4956028007",
        "packet_dir": str(packet),
        "preparation_receipt_sha256": "preparation-receipt",
        "field_bundle_receipt_sha256": "field-receipt",
        "required_field_count": 3,
        "resolved_required_count": 3,
        "unresolved_required_fields": [],
        "ready_for_human_submission": True,
        "receipt_sha256": "finalization-receipt",
        "fields": [
            {
                "field_name": "first_name",
                "label": "First Name",
                "field_type": "input_text",
                "required": True,
                "status": "ANSWER_BOUND",
                "value": "Casey",
                "attachment": None,
                "provenance": ["CandidateProfile.name"],
                "reason": "Prepared value is source-bound.",
            },
            {
                "field_name": "resume",
                "label": "Resume/CV",
                "field_type": "input_file",
                "required": True,
                "status": "ATTACHMENT_BOUND",
                "value": None,
                "attachment": {
                    "field_name": "resume",
                    "path": str(resume),
                    "sha256": resume_sha,
                    "size_bytes": resume.stat().st_size,
                    "provenance": "production-resume",
                },
                "provenance": ["production-resume", f"sha256:{resume_sha}"],
                "reason": "Exact attachment is hash-bound.",
            },
            {
                "field_name": "question_exceptional",
                "label": "Exceptional work",
                "field_type": "textarea",
                "required": True,
                "status": "ANSWER_BOUND",
                "value": "I built source-bound systems with deterministic recovery proofs.",
                "attachment": None,
                "provenance": ["applicant-confirmed:exceptional-work"],
                "reason": "Applicant confirmed.",
            },
            {
                "field_name": "internal_token",
                "label": "Internal token",
                "field_type": "input_hidden",
                "required": True,
                "status": "PROVIDER_MANAGED",
                "value": None,
                "attachment": None,
                "provenance": [],
                "reason": "Provider managed.",
            },
        ],
        "attachments": [
            {
                "field_name": "resume",
                "path": str(resume),
                "sha256": resume_sha,
                "size_bytes": resume.stat().st_size,
                "provenance": "production-resume",
            }
        ],
    }
    final_path = packet / "GREENHOUSE_APPLICATION_FINAL.json"
    final_path.write_text(json.dumps(finalization), encoding="utf-8")
    return final_path, resume


def test_builds_hash_bound_submission_plan_from_ready_packet(tmp_path: Path) -> None:
    final_path, resume = _ready_packet(tmp_path)

    plan = build_greenhouse_submission_plan(final_path)

    assert plan.application_id == "app-xai-1"
    assert plan.board_key == "xai"
    assert plan.job_id == "4956028007"
    assert plan.direct_api_eligible is True
    assert plan.direct_api_blockers == ()
    assert plan.submission_endpoint.endswith("/boards/xai/jobs/4956028007")
    assert len(plan.answers) == 2
    assert len(plan.attachments) == 1
    assert plan.attachments[0].sha256 == hashlib.sha256(resume.read_bytes()).hexdigest()
    assert len(plan.authorization_token) == 64
    assert (final_path.parent / "GREENHOUSE_SUBMISSION_PLAN.json").is_file()


def test_not_ready_finalization_is_rejected_before_plan_write(tmp_path: Path) -> None:
    final_path, _ = _ready_packet(tmp_path)
    payload = json.loads(final_path.read_text(encoding="utf-8"))
    payload["ready_for_human_submission"] = False
    payload["unresolved_required_fields"] = ["question_exceptional"]
    final_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(GreenhouseSubmissionError, match="not submission-ready"):
        build_greenhouse_submission_plan(final_path)

    assert not (final_path.parent / "GREENHOUSE_SUBMISSION_PLAN.json").exists()


def test_attachment_hash_drift_is_rejected(tmp_path: Path) -> None:
    final_path, resume = _ready_packet(tmp_path)
    resume.write_bytes(b"mutated after finalization")

    with pytest.raises(GreenhouseSubmissionError, match="attachment hash drift"):
        build_greenhouse_submission_plan(final_path)


def test_explicit_packet_authorization_is_required_before_transport(tmp_path: Path) -> None:
    final_path, _ = _ready_packet(tmp_path)
    plan_path = final_path.parent / "GREENHOUSE_SUBMISSION_PLAN.json"
    build_greenhouse_submission_plan(final_path, output_path=plan_path)
    called = False

    def transport(*args: object) -> tuple[int, bytes]:
        nonlocal called
        called = True
        return 200, b"{}"

    with pytest.raises(GreenhouseSubmissionError, match="authorization token"):
        execute_greenhouse_submission(
            plan_path,
            api_key="employer-issued-key",
            authorization_token="wrong-packet",
            transport=transport,
        )

    assert called is False
    assert not (final_path.parent / "GREENHOUSE_SUBMISSION_RECEIPT.json").exists()


def test_successful_mocked_provider_post_preserves_receipt_and_blocks_duplicate(
    tmp_path: Path,
) -> None:
    final_path, _ = _ready_packet(tmp_path)
    plan_path = final_path.parent / "GREENHOUSE_SUBMISSION_PLAN.json"
    plan = build_greenhouse_submission_plan(final_path, output_path=plan_path)
    calls: list[tuple[str, str, int, int]] = []

    def transport(endpoint: str, api_key: str, answers: object, attachments: object) -> tuple[int, bytes]:
        calls.append((endpoint, api_key, len(answers), len(attachments)))  # type: ignore[arg-type]
        return 200, b'{"application_id":12345,"success":true}'

    receipt = execute_greenhouse_submission(
        plan_path,
        api_key="employer-issued-key",
        authorization_token=plan.authorization_token,
        transport=transport,
    )

    assert receipt.status == "SUBMITTED"
    assert receipt.http_status == 200
    assert receipt.provider_response == {"application_id": 12345, "success": True}
    assert len(calls) == 1
    stored = json.loads(
        (final_path.parent / "GREENHOUSE_SUBMISSION_RECEIPT.json").read_text(encoding="utf-8")
    )
    assert stored["status"] == "SUBMITTED"
    assert stored["idempotency_key"] == plan.idempotency_key

    with pytest.raises(GreenhouseSubmissionError, match="already exists"):
        execute_greenhouse_submission(
            plan_path,
            api_key="employer-issued-key",
            authorization_token=plan.authorization_token,
            transport=transport,
        )
    assert len(calls) == 1


def test_transport_ambiguity_fails_closed_and_requires_reconciliation(tmp_path: Path) -> None:
    final_path, _ = _ready_packet(tmp_path)
    plan_path = final_path.parent / "GREENHOUSE_SUBMISSION_PLAN.json"
    plan = build_greenhouse_submission_plan(final_path, output_path=plan_path)

    def transport(*args: object) -> tuple[int, bytes]:
        raise TimeoutError("provider response lost")

    with pytest.raises(GreenhouseSubmissionError, match="provider outcome requires reconciliation"):
        execute_greenhouse_submission(
            plan_path,
            api_key="employer-issued-key",
            authorization_token=plan.authorization_token,
            transport=transport,
        )

    stored = json.loads(
        (final_path.parent / "GREENHOUSE_SUBMISSION_RECEIPT.json").read_text(encoding="utf-8")
    )
    assert stored["status"] == "PROVIDER_OUTCOME_UNKNOWN"


def test_malformed_multi_select_forces_handoff_instead_of_guessing(tmp_path: Path) -> None:
    final_path, _ = _ready_packet(tmp_path)
    field_bundle_path = final_path.parent / "GREENHOUSE_APPLICATION_FIELDS.json"
    field_bundle = json.loads(field_bundle_path.read_text(encoding="utf-8"))
    field_bundle["fields"].append(
        {
            "field": {
                "label": "Skills",
                "name": "skills[]",
                "field_type": "multi_value_multi_select",
                "required": True,
                "options": [],
                "category": "questions",
            }
        }
    )
    field_bundle_path.write_text(json.dumps(field_bundle), encoding="utf-8")
    finalization = json.loads(final_path.read_text(encoding="utf-8"))
    finalization["fields"].append(
        {
            "field_name": "skills[]",
            "label": "Skills",
            "field_type": "multi_value_multi_select",
            "required": True,
            "status": "ANSWER_BOUND",
            "value": "Python, Rust",
            "attachment": None,
            "provenance": ["applicant-confirmed:skills"],
            "reason": "Applicant confirmed.",
        }
    )
    final_path.write_text(json.dumps(finalization), encoding="utf-8")

    plan = build_greenhouse_submission_plan(final_path)

    assert plan.direct_api_eligible is False
    assert plan.handoff_state == "HOSTED_FORM_HANDOFF_REQUIRED"
    assert "multi-select answer must be an explicit JSON array" in plan.direct_api_blockers[0]
