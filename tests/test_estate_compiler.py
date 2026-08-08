from __future__ import annotations

from job_app_helix.estate_compiler import compile_estate, public_safe_projection


def census() -> dict:
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
                "visibility": visibility,
                "default_branch": "main",
                "archived": archived,
                "fork": fork,
                "classification": classification,
            }
            for repo, rid, visibility, archived, fork, classification in rows
        ],
    }


def flagships() -> dict:
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


def company_index() -> dict:
    return {"required_company_tracks": ["acme"], "dossier_files": ["unused.json"]}


def company_shards() -> list[dict]:
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


def test_compiler_collapses_only_high_confidence_history() -> None:
    bundle = compile_estate(
        census(), flagships=flagships(), company_index=company_index(), company_shards=company_shards()
    )
    registry = bundle["canonical_system_registry"]
    alpha = next(row for row in registry["systems"] if row["canonical_repository"] == "GlacierEQ/alpha")
    assert "GlacierEQ/z-backup-alpha" in alpha["member_repositories"]
    assert registry["separate_namespaces"]["legal_private"]["repository_count"] == 1
    assert registry["separate_namespaces"]["fork_reference"]["repository_count"] == 1


def test_ambiguous_lineage_is_not_silently_merged() -> None:
    payload = census()
    payload["repositories"][2]["repository"] = "GlacierEQ/alpha-v2"
    bundle = compile_estate(payload, flagships=flagships())
    assert any(
        row["canonical_repository"] == "GlacierEQ/alpha-v2"
        for row in bundle["canonical_system_registry"]["systems"]
    )


def test_capability_donors_are_evidence_bound() -> None:
    bundle = compile_estate(census(), flagships=flagships())
    capabilities = {
        row["capability_id"]: row for row in bundle["capability_donor_registry"]["capabilities"]
    }
    assert capabilities["deterministic-orchestration"]["verification_state"] == "EVIDENCE_BOUND"
    assert capabilities["provenance-and-evidence"]["independent_donor_count"] == 1


def test_company_projection_scores_and_minimizes_proof_surface() -> None:
    bundle = compile_estate(
        census(), flagships=flagships(), company_index=company_index(), company_shards=company_shards()
    )
    projection = bundle["company_projection_registry"]["projections"][0]
    assert projection["company_id"] == "acme"
    assert projection["minimal_proof_surface"] == projection["canonical_systems"]
    assert projection["projection_innovation"] == "bounded_greedy_capability_set_cover"
    score = next(iter(bundle["company_projection_registry"]["promotion_scores"].values()))
    assert "visibility_decision" in score
    assert set(score["components"]) == {
        "originality",
        "technical_depth",
        "verification_strength",
        "transferability",
        "target_company_relevance",
    }


def test_public_projection_excludes_legal_private_namespace() -> None:
    bundle = compile_estate(
        census(), flagships=flagships(), company_index=company_index(), company_shards=company_shards()
    )
    assert "case-1FDV-private" not in str(public_safe_projection(bundle))


def test_experiment_pipeline_has_monotonic_gate_contract() -> None:
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
        census(), flagships=flagships(), company_index=company_index(), company_shards=shards
    )
    experiment = bundle["experiment_pipeline"][0]
    assert experiment["stage"] == "EXPERIMENT"
    assert list(experiment["promotion_requirements"]) == [
        "DISTINCT_VALUE",
        "TESTED",
        "SYSTEM_COMPONENT",
        "FLAGSHIP_DONOR",
    ]
