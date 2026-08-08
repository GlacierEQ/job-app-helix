from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.company_intelligence import parse_company_intelligence
from job_app_helix.estate_compiler import compile_estate
from job_app_helix.estate_intelligence import (
    project_estate_intelligence,
    public_intelligence_projection,
    role_fit,
)

ROOT = Path(__file__).resolve().parents[1]


def _census():
    rows = [
        ("GlacierEQ/alpha", 1, "public", False, False),
        ("GlacierEQ/beta", 2, "public", False, False),
        ("GlacierEQ/gamma", 3, "public", False, False),
    ]
    return {
        "state": "VERIFIED_INVENTORY",
        "repository_count": 3,
        "native_repository_count": 3,
        "fork_repository_count": 0,
        "repositories": [
            {
                "repository": repo,
                "repository_id": rid,
                "visibility": visibility,
                "default_branch": "main",
                "archived": archived,
                "fork": fork,
                "classification": "UNGOVERNED_PUBLIC_INVENTORY",
            }
            for repo, rid, visibility, archived, fork in rows
        ],
    }


def _flagships():
    return {
        "flagships": [
            {
                "system_id": "alpha",
                "repository": "GlacierEQ/alpha",
                "level": "L5",
                "state": "PROMOTED",
                "public_surface": "PUBLIC",
                "role": "Deterministic orchestration agent authority evidence",
                "evidence": "12/12 tests and receipt.",
            },
            {
                "system_id": "beta",
                "repository": "GlacierEQ/beta",
                "level": "L4",
                "state": "PROMOTED",
                "public_surface": "PUBLIC",
                "role": "Document PDF processing",
                "evidence": "8/8 tests.",
            },
            {
                "system_id": "gamma",
                "repository": "GlacierEQ/gamma",
                "level": "L2",
                "state": "REFERENCE_ONLY",
                "public_surface": "PUBLIC",
                "role": "Agent experiment",
                "evidence": "Prototype receipt.",
            },
        ]
    }


def _company_index():
    return {"required_company_tracks": ["acme"], "dossier_files": ["unused.json"]}


def _company_shards():
    return [
        {
            "companies": [
                {
                    "company_id": "acme",
                    "display_name": "Acme",
                    "target_roles": ["Agent Infrastructure Engineer"],
                    "recruiter_thesis": "Build governed agent infrastructure.",
                    "gap_or_next_gate": "Refresh exact role proof.",
                    "non_affiliation": "No affiliation implied.",
                    "repositories": [
                        ["GlacierEQ/alpha", "L5", "PROMOTED", "public", "HELIX_ADMITTED", "ORIGINAL_CANDIDATE"],
                        ["GlacierEQ/beta", "L4", "PROMOTED", "public", "HELIX_ADMITTED", "ORIGINAL_CANDIDATE"],
                        ["GlacierEQ/gamma", "L2", "EXPERIMENT", "public", "HELIX_ADMITTED", "ORIGINAL_CANDIDATE"],
                    ],
                }
            ]
        }
    ]


def _policy():
    return {
        "audience_caps": {"recruiter": 10, "company_reviewer": 5, "senior_engineer": 20},
        "role_capability_rules": [
            {
                "match_any": ["agent", "infrastructure", "engineer"],
                "capabilities": ["deterministic-orchestration", "provenance-and-evidence"],
            }
        ],
    }


def _bundle():
    return compile_estate(
        _census(),
        flagships=_flagships(),
        company_index=_company_index(),
        company_shards=_company_shards(),
    )


def test_support_and_experiment_do_not_become_accomplishments() -> None:
    facts = {
        "supports": [
            {
                "repository": "GlacierEQ/beta",
                "relation": "DEPENDENCY_OF",
                "target": "GlacierEQ/alpha",
                "evidence_refs": ["dependency:fixture"],
            }
        ]
    }
    projected = project_estate_intelligence(
        _bundle(), policy=_policy(), estate_facts=facts, census=_census()
    )
    systems = {
        row["canonical_repository"]: row
        for row in projected["canonical_system_registry"]["systems"]
    }
    assert systems["GlacierEQ/alpha"]["counts_as_independent_accomplishment"] is True
    assert systems["GlacierEQ/beta"]["counts_as_independent_accomplishment"] is False
    assert systems["GlacierEQ/gamma"]["counts_as_independent_accomplishment"] is False
    assert projected["canonical_system_registry"]["support_references"][0]["collapse_lineage"] is False
    projection = projected["company_projection_registry"]["projections"][0]
    repositories = {row["source_repository"] for row in projection["ranked_evidence"]}
    assert repositories == {"GlacierEQ/alpha"}


def test_role_fit_replaces_company_count_relevance() -> None:
    projected = project_estate_intelligence(_bundle(), policy=_policy(), census=_census())
    projection = projected["company_projection_registry"]["projections"][0]
    alpha = next(row for row in projection["ranked_evidence"] if row["source_repository"] == "GlacierEQ/alpha")
    beta = next(row for row in projection["ranked_evidence"] if row["source_repository"] == "GlacierEQ/beta")
    assert alpha["promotion_score_components"]["target_company_relevance"] == 100.0
    assert beta["promotion_score_components"]["target_company_relevance"] == 0.0
    assert alpha["promotion_score"] > beta["promotion_score"]


def test_unmapped_role_is_zero_not_invented_relevance() -> None:
    fit = role_fit(["deterministic-orchestration"], "Unclassified Specialist 9000", _policy())
    assert fit["fit_score"] == 0.0
    assert fit["coverage_state"] == "UNMAPPED_ROLE"


def test_company_intelligence_keeps_observation_and_inference_separate() -> None:
    intelligence = {
        "acme": {
            "observed_current_pressure": "Observed public pressure.",
            "inferred_bottleneck": "GlacierEQ bottleneck inference.",
            "inferred_brick_wall": "GlacierEQ brick-wall inference.",
            "leverage_mechanism": "Mechanism.",
            "expected_impact": "Impact.",
            "application_move": "Application move.",
            "next_deep_dive": "Refresh source.",
            "official_sources": [{"title": "Official", "url": "https://example.test", "source_sha256": "a" * 64, "observed_signal": "Signal"}],
            "research_as_of": "2026-08-05",
            "freshness_state": "HISTORICAL_SOURCE_SNAPSHOT_REQUIRES_REFRESH_BEFORE_LIVE_APPLICATION",
            "inference_boundary": "Observed and inferred remain distinct.",
        }
    }
    projected = project_estate_intelligence(
        _bundle(), policy=_policy(), company_intelligence=intelligence, census=_census()
    )
    projection = projected["company_projection_registry"]["projections"][0]
    assert projection["observed_operating_pressure"] == "Observed public pressure."
    assert projection["inferred_bottleneck"] == "GlacierEQ bottleneck inference."
    assert projection["dossier_next_gate"] == "Refresh exact role proof."


def test_public_projection_omits_internal_counts_and_non_accomplishments() -> None:
    facts = {
        "supports": [
            {
                "repository": "GlacierEQ/beta",
                "relation": "REFERENCE_OF",
                "target": "GlacierEQ/alpha",
                "evidence_refs": ["reference:fixture"],
            }
        ]
    }
    projected = project_estate_intelligence(
        _bundle(), policy=_policy(), estate_facts=facts, census=_census()
    )
    public = public_intelligence_projection(projected)
    rendered = json.dumps(public, sort_keys=True)
    assert public["schema"] == "glaciereq.estate-public-projection.v2"
    assert "GlacierEQ/beta" not in rendered
    assert "GlacierEQ/gamma" not in rendered
    assert "canonical_accomplishments" not in rendered
    assert public["boundary"]["native_estate_cardinality_intentionally_not_published"] is True


def test_external_atlas_is_47_external_tracks() -> None:
    manifest = json.loads(
        (ROOT / "manifests/application_intelligence/company_bottleneck_atlas.external.json").read_text(encoding="utf-8")
    )
    shards = {
        ref["path"]: json.loads((ROOT / ref["path"]).read_text(encoding="utf-8"))
        for ref in manifest["shards"]
    }
    records = parse_company_intelligence(manifest, shards)
    assert len(records) == 47
    assert "glaciereq_core" not in records
    assert records["openai"]["observed_current_pressure"]
    assert records["openai"]["inferred_bottleneck"]
    assert len(records["openai"]["official_sources"][0]["source_sha256"]) == 64
