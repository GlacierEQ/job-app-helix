from __future__ import annotations

from job_app_helix.application_operations import CandidateProfile
from job_app_helix.greenhouse_application_fields import (
    GreenhouseApplicationFieldError,
    build_greenhouse_application_bundle,
)


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="casey-test",
        name="Casey Barton",
        headline="Systems architect",
        summary="Builds evidence-bound automation systems.",
        skills=("Python", "TypeScript"),
        experience=("Designed production automation systems.",),
        achievements=("Shipped auditable execution pipelines.",),
        contact={
            "email": "casey@example.com",
            "phone": "+1-808-555-0100",
            "linkedin": "https://www.linkedin.com/in/casey",
            "github": "https://github.com/casey",
            "portfolio": "https://casey.example",
        },
        source_digest="resume-sha256",
    )


def _payload() -> dict[str, object]:
    return {
        "id": 4956028007,
        "questions": [
            {
                "label": "First Name",
                "required": True,
                "fields": [{"name": "first_name", "type": "input_text", "values": []}],
            },
            {
                "label": "Last Name",
                "required": True,
                "fields": [{"name": "last_name", "type": "input_text", "values": []}],
            },
            {
                "label": "Email",
                "required": True,
                "fields": [{"name": "email", "type": "input_text", "values": []}],
            },
            {
                "label": "LinkedIn Profile",
                "required": False,
                "fields": [{"name": "question_100", "type": "input_text", "values": []}],
            },
            {
                "label": "Resume",
                "required": True,
                "fields": [{"name": "resume", "type": "input_file", "values": []}],
            },
            {
                "label": "Why xAI?",
                "required": True,
                "fields": [{"name": "question_101", "type": "textarea", "values": []}],
            },
            {
                "label": "Are you a protected veteran?",
                "required": False,
                "fields": [
                    {
                        "name": "question_102",
                        "type": "multi_value_single_select",
                        "values": [
                            {"value": 1, "label": "Yes"},
                            {"value": 0, "label": "No"},
                        ],
                    }
                ],
            },
        ],
        "location_questions": [
            {
                "label": "Latitude",
                "required": True,
                "fields": [{"name": "latitude", "type": "input_hidden", "values": []}],
            }
        ],
    }


def test_build_bundle_autofills_only_exact_profile_evidence() -> None:
    seen: list[str] = []

    def transport(url: str) -> object:
        seen.append(url)
        return _payload()

    bundle = build_greenhouse_application_bundle(
        "xai",
        "4956028007",
        _profile(),
        transport=transport,
    )
    answers = {item.field.name: item for item in bundle.fields}

    assert seen == [
        "https://boards-api.greenhouse.io/v1/boards/xai/jobs/4956028007?questions=true"
    ]
    assert answers["first_name"].value == "Casey"
    assert answers["last_name"].value == "Barton"
    assert answers["email"].value == "casey@example.com"
    assert answers["question_100"].value == "https://www.linkedin.com/in/casey"
    assert answers["resume"].status == "ATTACHMENT_REQUIRED"
    assert answers["question_101"].status == "REVIEW_REQUIRED"
    assert answers["question_102"].status == "USER_DECISION_REQUIRED"
    assert answers["latitude"].status == "PROVIDER_MANAGED"
    assert bundle.auto_fill_count == 4
    assert bundle.attachment_count == 1
    assert bundle.review_required_count == 2
    assert len(bundle.receipt_sha256) == 64


def test_bundle_fails_closed_on_provider_identity_drift() -> None:
    def transport(_url: str) -> object:
        payload = _payload()
        payload["id"] = 99
        return payload

    try:
        build_greenhouse_application_bundle(
            "xai",
            "4956028007",
            _profile(),
            transport=transport,
        )
    except GreenhouseApplicationFieldError as exc:
        assert "identity drift" in str(exc)
    else:
        raise AssertionError("provider identity drift must fail closed")


def test_bundle_fails_when_provider_returns_no_fields() -> None:
    def transport(_url: str) -> object:
        return {"id": 4956028007, "questions": []}

    try:
        build_greenhouse_application_bundle(
            "xai",
            "4956028007",
            _profile(),
            transport=transport,
        )
    except GreenhouseApplicationFieldError as exc:
        assert "no application fields" in str(exc)
    else:
        raise AssertionError("empty application schema must fail closed")
