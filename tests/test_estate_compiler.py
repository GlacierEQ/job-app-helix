from __future__ import annotations

import pytest

from job_app_helix.estate_compiler import compile_estate, public_safe_projection


def census():
    rows = [
        ("GlacierEQ/alpha", 1, "public", False, False, "UNGOVERNED_PUBLIC_INVENTORY"),
        ("GlacierEQ/z-backup-alpha", 2, "private", True, False, "ARCHIVE_BACKUP_OR_FORK"),
        ("GlacierEQ/alpha_v2", 3, "public", False, False, "UNGOVERNED_PUBLIC_INVENTORY"),
        ("GlacierEQ/case-1FDV-private", 4, "private", False, False, "PRIVATE_REVIEW_REQUIRED"),
        ("GlacierEQ/upstream", 5, "public", False, True, "UPSTREAM_OR_FORK_REVIEW"),
    ]
    return {
        "state": "VERIFIED_INVENTORY",
        "repository_count": 5,
        "native_repository_count": 4,
        "fork_repository_count": 1,
        "repositories": [
            {
                "repository": repo,
                "repository_id": rid,
                "visibility": vis,
                "default_branch": "main",
                "archived": archived,
                "fork": fork,
                "classification": classification,
            }
            for repo, rid, vis, archived, fork, classification in rows
        ],
    }


def flagships():
    return {
        "flagships": [
            {
                "system_id": "alpha",
                "repository": "GlacierEQ/alpha",
                "level": "L5",
                "state": "PROMOTED",
                "public_surface": "PUBLIC",
                "role": "Deterministic orchestration and evidence authority",
                "evidence": "12/12 tests and signed receipt.",
                "next_gate": "None",
            }
        ]
    }


def company_index():
    return {"required_company_tracks": ["acme"], "dossier_files": ["unused.json"]}


def company_shards():
    return [
        {
            "companies": [
                {
                    "company_id": "acme",
                    "display_name": "Acme",
                    "target_roles": ["Staff Engineer"],
                    "recruiter_thesis": "Build governed systems.",
                    "gap_or_next_gate": "Reliable orchestration under failure.",
                    "non_affiliation": "No affiliation implied.",
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


def semantic_company_shards():
    shards = company_shards()
    company = shards[0]["companies"][0]
    company["track_state"] = "SEMANTIC_TEST"
    company["capability_map"] = "fixture-semantic-map.json"
    company["capability_donors"] = [
        [
            "GlacierEQ/alpha_v2",
            "semantic-health",
            "SOURCE_AND_EXACT_HEAD_CHECKS_VERIFIED",
            "REFERENCE_ONLY",
        ]
    ]
    return shards


def semantic_capabilities():
    head = "a" * 40
    return {
        "schema": "fixture.semantic-capabilities.v1",
        "truth_boundary": {
            "blocked_repository_cannot_be_recruiter_capability_donor": True,
        },
        "donor_systems": {
            "GlacierEQ/alpha_v2": {
                "visibility": "public",
                "fork": False,
                "head_sha": head,
                "proof_state": "SOURCE_AND_EXACT_HEAD_CHECKS_VERIFIED",
                "evidence_inventory": [
                    {"path": "src/health.py", "blob_sha": "b" * 40}
                ],
                "proof_receipts": [
                    {
                        "kind": "check_run",
                        "id": 123,
                        "name": "CI",
                        "head_sha": head,
                        "conclusion": "success",
                    }
                ],
            }
        },
        "blocked_candidate_systems": {},
        "capabilities": [
            {
                "capability_id": "semantic-health",
                "company_id": "acme",
                "donor_repository": "GlacierEQ/alpha_v2",
                "head_sha": head,
                "evidence_refs": ["src/health.py"],
                "mechanism": "Structured connector health.",
                "recruiter_safe_claim": "Implemented structured connector health.",
            }
        ],
        "company_projection": {
            "acme": {
                "state": "SEMANTIC_TEST",
                "capability_ids": ["semantic-health"],
                "donor_repositories": ["GlacierEQ/alpha_v2"],
                "affiliation_claim": False,
                "deployment_claim": False,
            }
        },
    }


def test_compiler_collapses_only_high_confidence_history():
    bundle = compile_estate(
        census(),
        flagships=flagships(),
        company_index=company_index(),
        company_shards=company_shards(),
    )
    registry = bundle["system_registry"]
    alpha = next(
        row
        for row in registry["systems"]
        if row["source_repository"] == "GlacierEQ/alpha"
    )
    assert "GlacierEQ/z-backup-alpha" in alpha["member_repositories"]
    assert registry["separate_namespaces"]["legal_private"]["repository_count"] == 1
    assert registry["separate_namespaces"]["fork_reference"]["repository_count"] == 1


def test_ambiguous_lineage_is_not_silently_merged():
    payload = census()
    payload["repositories"][2]["repository"] = "GlacierEQ/alpha-v2"
    bundle = compile_estate(payload, flagships=flagships())
    systems = bundle["system_registry"]["systems"]
    assert any(row["source_repository"] == "GlacierEQ/alpha-v2" for row in systems)


def test_capability_donors_are_evidence_bound():
    bundle = compile_estate(census(), flagships=flagships())
    caps = {
        row["capability_id"]: row
        for row in bundle["capability_donor_registry"]["capabilities"]
    }
    assert caps["deterministic-orchestration"]["verification_state"] == "EVIDENCE_BOUND"
    assert caps["provenance-and-evidence"]["independent_donor_count"] == 1


def test_company_projection_uses_system_and_separate_visibility_score():
    bundle = compile_estate(
        census(),
        flagships=flagships(),
        company_index=company_index(),
        company_shards=company_shards(),
    )
    projection = bundle["company_projection_registry"]["projections"][0]
    assert projection["company_id"] == "acme"
    assert len(projection["reference_systems"]) == 1
    assert projection["minimal_proof_surface"] == projection["reference_systems"]
    assert projection["projection_innovation"] == (
        "complete_ranked_relation_graph_with_minimal_proof_view"
    )
    assert bundle["company_projection_registry"]["policy"]["company_surface_max_systems"] is None
    assert bundle["company_projection_registry"]["policy"]["presentation_pagination_changes_membership"] is False
    score = next(iter(bundle["company_projection_registry"]["promotion_scores"].values()))
    assert "visibility_decision" in score
    assert set(score["components"]) == {
        "originality",
        "technical_depth",
        "verification_strength",
        "transferability",
        "target_company_relevance",
    }


def test_public_projection_excludes_legal_private_namespace():
    bundle = compile_estate(
        census(),
        flagships=flagships(),
        company_index=company_index(),
        company_shards=company_shards(),
    )
    public = public_safe_projection(bundle)
    rendered = str(public)
    assert "case-1FDV-private" not in rendered


def test_semantic_capability_donor_compiles_into_company_and_public_projection():
    bundle = compile_estate(
        census(),
        flagships=flagships(),
        company_index=company_index(),
        company_shards=semantic_company_shards(),
        semantic_capabilities=semantic_capabilities(),
    )
    capability = next(
        row
        for row in bundle["capability_donor_registry"]["capabilities"]
        if row["capability_id"] == "semantic-health"
    )
    proof = capability["proof_refs"][0]
    assert proof["head_sha"] == "a" * 40
    assert proof["proof_receipts"][0]["head_sha"] == proof["head_sha"]

    projection = bundle["company_projection_registry"]["projections"][0]
    assert "semantic-health" in projection["capabilities"]
    semantic_rows = [
        row
        for row in projection["ranked_evidence"]
        if row["mapping_kind"] == "semantic_capability_donor"
    ]
    assert len(semantic_rows) == 1
    assert semantic_rows[0]["promotion_state"] == "REFERENCE_ONLY"
    assert semantic_rows[0]["capability_ids"] == ["semantic-health"]

    public = public_safe_projection(bundle)["company_projections"][0]
    assert "semantic-health" in public["capabilities"]
    assert any(
        row["mapping_kind"] == "semantic_capability_donor"
        for row in public["ranked_evidence"]
    )


def test_semantic_capability_donor_rejects_non_recruiter_governing_state():
    shards = semantic_company_shards()
    shards[0]["companies"][0]["repositories"].append(
        [
            "GlacierEQ/alpha_v2",
            "L2",
            "BLOCKED",
            "public",
            "HELIX_ADMITTED",
            "ORIGINAL_CANDIDATE",
        ]
    )
    with pytest.raises(ValueError, match="non-recruiter governing states"):
        compile_estate(
            census(),
            flagships=flagships(),
            company_index=company_index(),
            company_shards=shards,
            semantic_capabilities=semantic_capabilities(),
        )


def test_semantic_capability_donor_rejects_receipt_head_drift():
    semantic = semantic_capabilities()
    semantic["donor_systems"]["GlacierEQ/alpha_v2"]["proof_receipts"][0][
        "head_sha"
    ] = "c" * 40
    with pytest.raises(ValueError, match="proof receipt head SHA drift"):
        compile_estate(
            census(),
            flagships=flagships(),
            company_index=company_index(),
            company_shards=semantic_company_shards(),
            semantic_capabilities=semantic,
        )


def test_explicit_namespace_assertion_is_evidence_bound() -> None:
    facts = {
        "namespaces": [
            {
                "repository": "GlacierEQ/alpha_v2",
                "namespace": "LEGAL_PRIVATE",
                "evidence_refs": ["governed-classification:fixture"],
            }
        ]
    }
    bundle = compile_estate(census(), flagships=flagships(), lineage=facts)
    registry = bundle["system_registry"]
    assert registry["namespace_assertions_applied"] == 1
    assert registry["separate_namespaces"]["legal_private"]["repository_count"] == 2
    assert all(
        row["source_repository"] != "GlacierEQ/alpha_v2"
        for row in registry["systems"]
    )


def test_explicit_successor_becomes_reference_root() -> None:
    facts = {
        "relationships": [
            {
                "repository": "GlacierEQ/alpha_v2",
                "relation": "EXPLICIT_SUCCESSOR_OF",
                "target": "GlacierEQ/alpha",
                "evidence_refs": ["git-ancestry:fixture"],
            }
        ]
    }
    bundle = compile_estate(census(), flagships=flagships(), lineage=facts)
    systems = bundle["system_registry"]["systems"]
    successor = next(
        row
        for row in systems
        if row["source_repository"] == "GlacierEQ/alpha_v2"
    )
    assert "GlacierEQ/alpha" in successor["member_repositories"]
    assert "GlacierEQ/z-backup-alpha" in successor["member_repositories"]


def test_experiment_pipeline_has_monotonic_gate_contract():
    shards = company_shards()
    shards[0]["companies"][0]["repositories"].append(
        [
            "GlacierEQ/alpha_v2",
            "L1",
            "EXPERIMENT",
            "public",
            "ESTATE_DISCOVERED_NOT_HELIX_ADMITTED",
            "ORIGINAL_CANDIDATE",
        ]
    )
    bundle = compile_estate(
        census(),
        flagships=flagships(),
        company_index=company_index(),
        company_shards=shards,
    )
    experiment = bundle["experiment_pipeline"][0]
    assert experiment["stage"] == "EXPERIMENT"
    assert list(experiment["promotion_requirements"]) == [
        "DISTINCT_VALUE",
        "TESTED",
        "SYSTEM_COMPONENT",
        "FLAGSHIP_DONOR",
    ]
    public = public_safe_projection(bundle)
    projection = public["company_projections"][0]
    experiment_system = experiment["system_id"]
    assert experiment_system not in projection["reference_systems"]
    assert all(
        row["system_id"] != experiment_system
        for row in projection["ranked_evidence"]
    )
