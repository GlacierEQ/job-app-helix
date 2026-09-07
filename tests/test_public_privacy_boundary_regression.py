from __future__ import annotations

from job_app_helix.estate_intelligence_public import (
    _PRIVATE_REPOSITORY_PLACEHOLDER,
    _prepare_public_boundary_bundle,
    _redact_private_repository_identities,
    _repository_pattern,
)


def test_exact_private_identity_is_redacted_without_prefix_false_positive() -> None:
    identities = (
        "GlacierEQ/awesome-cursorrules",
        "GlacierEQ/job-app",
        "GlacierEQ/GlacierEQ",
    )
    text = (
        "Audit GlacierEQ/awesome-cursorrules and GlacierEQ/job-app. "
        "Keep public GlacierEQ/job-app-helix and GlacierEQ/GlacierEQ_Swarm visible."
    )

    redacted = _redact_private_repository_identities(text, identities)

    assert "GlacierEQ/awesome-cursorrules" not in redacted
    assert "GlacierEQ/job-app." not in redacted
    assert "GlacierEQ/job-app-helix" in redacted
    assert "GlacierEQ/GlacierEQ_Swarm" in redacted
    assert redacted.count(_PRIVATE_REPOSITORY_PLACEHOLDER) == 2


def test_repository_pattern_requires_identity_boundary() -> None:
    private = _repository_pattern("GlacierEQ/job-app")
    assert private.search("use GlacierEQ/job-app in private context")
    assert not private.search("use GlacierEQ/job-app-helix publicly")


def test_public_boundary_copy_redacts_prose_and_opaques_private_members() -> None:
    bundle = {
        "system_registry": {
            "systems": [
                {
                    "system_id": "private-system",
                    "visibility": "private",
                    "member_repositories": ["GlacierEQ/job-app"],
                },
                {
                    "system_id": "public-system",
                    "visibility": "public",
                    "member_repositories": ["GlacierEQ/job-app-helix"],
                },
            ]
        },
        "company_projection_registry": {
            "projections": [
                {
                    "company_id": "acme",
                    "dossier_next_gate": (
                        "Inspect GlacierEQ/job-app privately while presenting "
                        "GlacierEQ/job-app-helix publicly."
                    ),
                }
            ]
        },
    }

    prepared, identities = _prepare_public_boundary_bundle(bundle)
    projection = prepared["company_projection_registry"]["projections"][0]
    systems = prepared["system_registry"]["systems"]

    assert identities == ("GlacierEQ/job-app",)
    assert _PRIVATE_REPOSITORY_PLACEHOLDER in projection["dossier_next_gate"]
    assert "GlacierEQ/job-app-helix" in projection["dossier_next_gate"]
    assert systems[0]["member_repositories"] == ["__private_member_0_0__"]
    assert systems[1]["member_repositories"] == ["GlacierEQ/job-app-helix"]
