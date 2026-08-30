from __future__ import annotations

import json

import pytest

from job_app_helix.estate_intelligence_public import public_intelligence_projection

PUBLIC_HEAD = "a" * 40
PRIVATE_HEAD = "b" * 40


def _bundle() -> dict:
    public_system = {
        "system_id": "sys-public",
        "source_repository": "GlacierEQ/public-donor",
        "member_repositories": ["GlacierEQ/public-donor"],
        "visibility": "public",
        "public_surface": "PUBLIC",
    }
    private_system = {
        "system_id": "sys-private",
        "source_repository": "GlacierEQ/private-case-source",
        "member_repositories": ["GlacierEQ/private-case-source"],
        "visibility": "private",
        "public_surface": "PRIVATE_UNTIL_SANITIZED",
    }
    public_proof = {
        "system_id": "sys-public",
        "source": "semantic_capability_map",
        "company_id": "supabase",
        "repository": "GlacierEQ/public-donor",
        "head_sha": PUBLIC_HEAD,
        "proof_state": "SOURCE_AND_EXACT_HEAD_CHECKS_VERIFIED",
        "admission_state": "REFERENCE_ONLY",
        "evidence_refs": ["src/connector.py"],
        "proof_receipts": [
            {
                "kind": "check_run",
                "id": 101,
                "name": "CI",
                "head_sha": PUBLIC_HEAD,
                "conclusion": "success",
            }
        ],
    }
    private_proof = {
        "system_id": "sys-private",
        "source": "semantic_capability_map",
        "company_id": "supabase",
        "repository": "GlacierEQ/private-case-source",
        "head_sha": PRIVATE_HEAD,
        "proof_state": "SOURCE_AND_EXACT_HEAD_CHECKS_VERIFIED",
        "admission_state": "REFERENCE_ONLY",
        "evidence_refs": ["private/evidence.py"],
        "proof_receipts": [
            {
                "kind": "check_run",
                "id": 202,
                "name": "Private CI",
                "head_sha": PRIVATE_HEAD,
                "conclusion": "success",
            }
        ],
    }
    return {
        "source_digest": "c" * 64,
        "system_registry": {
            "systems": [public_system, private_system],
        },
        "capability_donor_registry": {
            "capabilities": [
                {
                    "capability_id": "supabase-least-privilege-broker",
                    "donor_systems": ["sys-public"],
                    "proof_refs": [public_proof],
                },
                {
                    "capability_id": "private-case-mechanism",
                    "donor_systems": ["sys-private"],
                    "proof_refs": [private_proof],
                },
            ]
        },
        "company_projection_registry": {
            "promotion_scores": {
                "sys-public": {"total": 88.0},
                "sys-private": {"total": 90.0},
            },
            "projections": [
                {
                    "company_id": "supabase",
                    "display_name": "Supabase",
                    "target_roles": ["Platform Engineer"],
                    "operating_problem": "Secure data-platform integration.",
                    "recruiter_thesis": "Public semantic donor proof.",
                    "reference_systems": ["sys-public", "sys-private"],
                    "capabilities": [
                        "supabase-least-privilege-broker",
                        "private-case-mechanism",
                    ],
                    "minimal_proof_surface": ["sys-public", "sys-private"],
                    "ranked_evidence": [
                        {
                            "system_id": "sys-public",
                            "source_repository": "GlacierEQ/public-donor",
                            "promotion_state": "REFERENCE_ONLY",
                            "visibility": "public",
                            "visibility_decision": "PUBLIC_ELIGIBLE",
                            "capability_ids": ["supabase-least-privilege-broker"],
                            "promotion_score": 88.0,
                        },
                        {
                            "system_id": "sys-private",
                            "source_repository": "GlacierEQ/private-case-source",
                            "promotion_state": "REFERENCE_ONLY",
                            "visibility": "private",
                            "visibility_decision": "INTERNAL_OR_SANITIZED_ONLY",
                            "capability_ids": ["private-case-mechanism"],
                            "promotion_score": 90.0,
                        },
                    ],
                    "official_sources": [],
                    "audience_projection": {
                        "recruiter": ["sys-public", "sys-private"],
                        "company_reviewer": ["sys-public", "sys-private"],
                        "senior_engineer": ["sys-public", "sys-private"],
                    },
                    "role_projection": {
                        "Platform Engineer": {
                            "profile_capabilities": [
                                "supabase-least-privilege-broker",
                                "private-case-mechanism",
                            ],
                            "coverage_state": "MAPPED_ROLE",
                            "systems": [
                                {
                                    "system_id": "sys-public",
                                    "fit_score": 95.0,
                                    "matched_capabilities": [
                                        "supabase-least-privilege-broker"
                                    ],
                                },
                                {
                                    "system_id": "sys-private",
                                    "fit_score": 96.0,
                                    "matched_capabilities": ["private-case-mechanism"],
                                },
                            ],
                        }
                    },
                    "non_affiliation": "No affiliation implied.",
                }
            ],
        },
    }


def test_public_capability_proof_packet_is_exact_head_and_private_safe() -> None:
    public = public_intelligence_projection(_bundle())
    company = public["company_projections"][0]

    assert public["boundary"][
        "semantic_capability_proof_is_exact_head_and_public_only"
    ] is True
    assert company["capabilities"] == ["supabase-least-privilege-broker"]
    assert company["reference_systems"] == ["sys-public"]
    assert company["capability_proofs"] == [
        {
            "capability_id": "supabase-least-privilege-broker",
            "system_id": "sys-public",
            "source_repository": "GlacierEQ/public-donor",
            "head_sha": PUBLIC_HEAD,
            "proof_state": "SOURCE_AND_EXACT_HEAD_CHECKS_VERIFIED",
            "admission_state": "REFERENCE_ONLY",
            "evidence_refs": ["src/connector.py"],
            "proof_receipts": [
                {
                    "kind": "check_run",
                    "id": 101,
                    "name": "CI",
                    "head_sha": PUBLIC_HEAD,
                    "conclusion": "success",
                }
            ],
        }
    ]
    rendered = json.dumps(public, sort_keys=True)
    assert "private-case-source" not in rendered
    assert "private/evidence.py" not in rendered


def test_public_capability_proof_packet_fails_closed_on_receipt_head_drift() -> None:
    bundle = _bundle()
    proof = bundle["capability_donor_registry"]["capabilities"][0]["proof_refs"][0]
    proof["proof_receipts"][0]["head_sha"] = "d" * 40

    with pytest.raises(ValueError, match="receipt head does not match donor head"):
        public_intelligence_projection(bundle)


@pytest.mark.parametrize(
    "unsafe_path",
    ["../secret.txt", "/etc/passwd", "src//connector.py", "src/./connector.py"],
)
def test_public_capability_proof_packet_rejects_unsafe_evidence_paths(
    unsafe_path: str,
) -> None:
    bundle = _bundle()
    proof = bundle["capability_donor_registry"]["capabilities"][0]["proof_refs"][0]
    proof["evidence_refs"] = [unsafe_path]

    with pytest.raises(ValueError, match="evidence refs are unsafe"):
        public_intelligence_projection(bundle)
