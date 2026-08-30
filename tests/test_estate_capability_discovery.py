from __future__ import annotations

import json

import pytest

from job_app_helix.estate_compiler import compile_estate
from job_app_helix.estate_intelligence import (
    project_estate_intelligence,
    public_intelligence_projection,
)


def _census() -> dict:
    rows = [
        ("GlacierEQ/alpha", 1, "public"),
        ("GlacierEQ/delta", 2, "public"),
        ("GlacierEQ/case-1FDV-private", 3, "private"),
    ]
    return {
        "state": "VERIFIED_INVENTORY",
        "repository_count": 3,
        "native_repository_count": 3,
        "fork_repository_count": 0,
        "repositories": [
            {
                "repository": repository,
                "repository_id": repository_id,
                "visibility": visibility,
                "default_branch": "main",
                "archived": False,
                "fork": False,
                "classification": "UNGOVERNED_PUBLIC_INVENTORY",
            }
            for repository, repository_id, visibility in rows
        ],
    }


def _flagships() -> dict:
    return {
        "flagships": [
            {
                "system_id": "alpha",
                "repository": "GlacierEQ/alpha",
                "level": "L5",
                "state": "PROMOTED",
                "public_surface": "PUBLIC",
                "role": "Provenance evidence authority",
                "evidence": "12/12 tests and receipt.",
            }
        ]
    }


def _company_index() -> dict:
    return {
        "required_company_tracks": ["acme"],
        "dossier_files": ["unused.json"],
    }


def _company_shards() -> list[dict]:
    return [
        {
            "companies": [
                {
                    "company_id": "acme",
                    "display_name": "Acme",
                    "target_roles": ["Agent Infrastructure Engineer"],
                    "recruiter_thesis": "Build reliable agent infrastructure.",
                    "gap_or_next_gate": "Scale reliable orchestration.",
                    "repositories": [
                        [
                            "GlacierEQ/alpha",
                            "L5",
                            "PROMOTED",
                            "public",
                            "HELIX_ADMITTED",
                            "ORIGINAL_CANDIDATE",
                        ]
                    ],
                }
            ]
        }
    ]


def _policy() -> dict:
    return {
        "audience_caps": {
            "recruiter": 10,
            "company_reviewer": 5,
            "senior_engineer": 20,
        },
        "role_capability_rules": [
            {
                "match_any": ["agent", "infrastructure", "engineer"],
                "capabilities": [
                    "deterministic-orchestration",
                    "provenance-and-evidence",
                ],
            }
        ],
    }


def _bundle() -> dict:
    return compile_estate(
        _census(),
        flagships=_flagships(),
        company_index=_company_index(),
        company_shards=_company_shards(),
    )


def test_evidence_bound_estate_capability_becomes_internal_company_candidate() -> None:
    facts = {
        "capabilities": [
            {
                "repository": "GlacierEQ/delta",
                "capability_id": "deterministic-orchestration",
                "evidence_refs": [
                    "repo:GlacierEQ/delta@abc123:tests/test_recovery.py"
                ],
                "evidence": "Deterministic restart path covered by repository-native tests.",
            }
        ]
    }
    projected = project_estate_intelligence(
        _bundle(),
        policy=_policy(),
        estate_facts=facts,
        census=_census(),
    )
    capabilities = {
        row["capability_id"]: row
        for row in projected["capability_donor_registry"]["capabilities"]
    }
    donor = capabilities["deterministic-orchestration"]
    delta_system = next(
        row["system_id"]
        for row in projected["system_registry"]["systems"]
        if row["source_repository"] == "GlacierEQ/delta"
    )
    assert delta_system in donor["donor_systems"]
    assert donor["verification_state"] == "EVIDENCE_BOUND"

    projection = projected["company_projection_registry"]["projections"][0]
    delta = next(
        row
        for row in projection["ranked_evidence"]
        if row["system_id"] == delta_system
    )
    assert delta["projection_source"] == "ESTATE_CAPABILITY_MATCH"
    assert delta["target_relevance_state"] == "ROLE_CAPABILITY_OVERLAP"
    assert projection["estate_candidate_count"] == 1
    assert projected["receipt"]["counts"]["capability_assertions_applied"] == 1

    public = public_intelligence_projection(projected)
    rendered = json.dumps(public, sort_keys=True)
    assert "GlacierEQ/delta" not in rendered
    assert delta_system not in rendered


def test_capability_assertion_cannot_cross_legal_private_boundary() -> None:
    facts = {
        "capabilities": [
            {
                "repository": "GlacierEQ/case-1FDV-private",
                "capability_id": "document-intelligence",
                "evidence_refs": ["private-case-proof:fixture"],
            }
        ]
    }
    with pytest.raises(
        ValueError,
        match="reference engineering system",
    ):
        project_estate_intelligence(
            _bundle(),
            policy=_policy(),
            estate_facts=facts,
            census=_census(),
        )
