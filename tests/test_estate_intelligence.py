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


def _census() -> dict:
    rows = [
        ("GlacierEQ/alpha", 1),
        ("GlacierEQ/beta", 2),
        ("GlacierEQ/gamma", 3),
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
                "visibility": "public",
                "default_branch": "main",
                "archived": False,
                "fork": False,
                "classification": "UNGOVERNED_PUBLIC_INVENTORY",
            }
            for repository, repository_id in rows
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


def _company_index() -> dict:
    return {
        "required_company_tracks": ["acme"],
        "dossier_files": ["unused.json"],
    }


def _company_shards() -> list[dict]:
    repositories = [
        [
            "GlacierEQ/alpha",
            "L5",
            "PROMOTED",
            "public",
            "HELIX_ADMITTED",
            "ORIGINAL_CANDIDATE",
        ],
        [
            "GlacierEQ/beta",
            "L4",
            "PROMOTED",
            "public",
            "HELIX_ADMITTED",
            "ORIGINAL_CANDIDATE",
        ],
        [
            "GlacierEQ/gamma",
            "L2",
            "EXPERIMENT",
            "public",
            "HELIX_ADMITTED",
            "ORIGINAL_CANDIDATE",
        ],
    ]
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
                    "repositories": repositories,
                }
            ]
        }
    ]


def _policy() -> dict:
    return {
        "audience_presentation_defaults": {
            "recruiter": 10,
            "company_reviewer": 5,
            "senior_engineer": 20,
        },
        "audience_projection_membership": "complete_ranked_relation_graph",
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


def test_support_and_experiment_are_not_accomplishments() -> None:
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
        _bundle(),
        policy=_policy(),
        estate_facts=facts,
        census=_census(),
    )
    systems = {
        row["source_repository"]: row
        for row in projected["system_registry"]["systems"]
    }
    assert systems["GlacierEQ/alpha"][
        "counts_as_independent_accomplishment"
    ]
    assert not systems["GlacierEQ/beta"][
        "counts_as_independent_accomplishment"
    ]
    assert not systems["GlacierEQ/gamma"][
        "counts_as_independent_accomplishment"
    ]
    support = projected["system_registry"][
        "support_references"
    ][0]
    assert support["collapse_lineage"] is False
    projection = projected["company_projection_registry"]["projections"][0]
    repositories = {
        row["source_repository"]
        for row in projection["ranked_evidence"]
    }
    assert repositories == {"GlacierEQ/alpha"}


def test_audience_projection_does_not_truncate_ranked_evidence() -> None:
    projected = project_estate_intelligence(
        _bundle(),
        policy=_policy(),
        census=_census(),
    )
    projection = projected["company_projection_registry"]["projections"][0]
    ranked_ids = [row["system_id"] for row in projection["ranked_evidence"]]
    assert projection["audience_projection_state"] == "COMPLETE_UNCAPPED"
    assert set(projection["audience_projection"]["recruiter"]) == set(ranked_ids)
    assert set(projection["audience_projection"]["company_reviewer"]) == set(ranked_ids)
    assert projection["audience_projection"]["senior_engineer"] == ranked_ids


def test_role_fit_replaces_company_count_relevance() -> None:
    projected = project_estate_intelligence(
        _bundle(),
        policy=_policy(),
        census=_census(),
    )
    rows = projected["company_projection_registry"]["projections"][0][
        "ranked_evidence"
    ]
    by_repository = {row["source_repository"]: row for row in rows}
    alpha = by_repository["GlacierEQ/alpha"]
    beta = by_repository["GlacierEQ/beta"]
    alpha_relevance = alpha["promotion_score_components"][
        "target_company_relevance"
    ]
    beta_relevance = beta["promotion_score_components"][
        "target_company_relevance"
    ]
    assert alpha_relevance == 100.0
    assert beta_relevance == 0.0
    assert alpha["promotion_score"] > beta["promotion_score"]


def test_unmapped_role_does_not_invent_relevance() -> None:
    fit = role_fit(
        ["deterministic-orchestration"],
        "Unclassified Specialist 9000",
        _policy(),
    )
    assert fit["fit_score"] == 0.0
    assert fit["coverage_state"] == "UNMAPPED_ROLE"


def test_company_intelligence_preserves_fact_inference_boundary() -> None:
    intelligence = {
        "acme": {
            "observed_current_pressure": "Observed public pressure.",
            "inferred_bottleneck": "GlacierEQ bottleneck inference.",
            "inferred_brick_wall": "GlacierEQ brick-wall inference.",
            "leverage_mechanism": "Mechanism.",
            "expected_impact": "Impact.",
            "application_move": "Application move.",
            "next_deep_dive": "Refresh source.",
            "official_sources": [],
            "research_as_of": "2026-08-05",
            "freshness_state": "HISTORICAL_SOURCE_SNAPSHOT",
            "inference_boundary": "Observed and inferred remain distinct.",
        }
    }
    projected = project_estate_intelligence(
        _bundle(),
        policy=_policy(),
        company_intelligence=intelligence,
        census=_census(),
    )
    projection = projected["company_projection_registry"]["projections"][0]
    assert projection["observed_operating_pressure"] == (
        "Observed public pressure."
    )
    assert projection["inferred_bottleneck"] == (
        "GlacierEQ bottleneck inference."
    )
    assert projection["dossier_next_gate"] == "Refresh exact role proof."


def test_public_projection_omits_non_accomplishments_and_raw_counts() -> None:
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
        _bundle(),
        policy=_policy(),
        estate_facts=facts,
        census=_census(),
    )
    public = public_intelligence_projection(projected)
    rendered = json.dumps(public, sort_keys=True)
    assert public["schema"] == "glaciereq.estate-public-projection.v2"
    assert "GlacierEQ/beta" not in rendered
    assert "GlacierEQ/gamma" not in rendered
    assert "reference_accomplishments" not in rendered
    assert public["boundary"][
        "native_estate_cardinality_intentionally_not_published"
    ]


def test_external_atlas_has_47_external_tracks() -> None:
    manifest_path = ROOT / "manifests/application_intelligence"
    manifest_path /= "company_bottleneck_atlas.external.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shards = {
        ref["path"]: json.loads(
            (ROOT / ref["path"]).read_text(encoding="utf-8")
        )
        for ref in manifest["shards"]
    }
    records = parse_company_intelligence(manifest, shards)
    assert len(records) == 47
    assert "glaciereq_core" not in records
    assert records["openai"]["observed_current_pressure"]
    assert records["openai"]["inferred_bottleneck"]
    source = records["openai"]["official_sources"][0]
    assert len(source["source_sha256"]) == 64
