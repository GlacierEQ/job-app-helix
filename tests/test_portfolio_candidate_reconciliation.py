from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "portfolio_candidate_reconciliation_2026-08-03.json"


def load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def repository_names(records: object) -> set[str]:
    assert isinstance(records, list)
    names: set[str] = set()
    for record in records:
        assert isinstance(record, dict)
        repository = record.get("repository")
        assert isinstance(repository, str)
        assert repository.startswith("GlacierEQ/")
        assert repository not in names
        names.add(repository)
    return names


def test_reconciliation_policy_upgrades_earnable_claims() -> None:
    manifest = load_manifest()
    assert manifest["schema"] == "glaciereq.portfolio-candidate-reconciliation.v1"

    policy = manifest["policy"]
    assert isinstance(policy, dict)
    assert policy["strong_claim_is_target_contract"] is True
    assert policy["upgrade_code_before_weakening_earnable_claim"] is True

    admission = policy["admission_requires"]
    flagship = policy["flagship_promotion_requires"]
    never_infer = policy["never_infer"]
    assert isinstance(admission, list) and len(admission) >= 7
    assert isinstance(flagship, list) and len(flagship) >= 10
    assert isinstance(never_infer, list) and "authorship from repository ownership" in never_infer


def test_original_candidates_and_upstream_references_do_not_overlap() -> None:
    manifest = load_manifest()
    candidates = repository_names(manifest["immediate_admission_candidates"])
    audit = repository_names(manifest["audit_before_admission"])
    references = repository_names(manifest["reference_or_upstream_not_candidate_evidence"])

    assert candidates == {"GlacierEQ/ECHO", "GlacierEQ/sigma-glue"}
    assert not candidates & references
    assert not audit & references
    assert "GlacierEQ/codex-supermemory" in references
    assert "GlacierEQ/megapdf-sdk" in references
    assert "GlacierEQ/Office-Word-MCP-Server" in references


def test_company_tracks_cover_the_required_hiring_targets() -> None:
    manifest = load_manifest()
    tracks = manifest["company_track_status"]
    assert isinstance(tracks, dict)

    expected = {
        "apple",
        "nvidia",
        "anthropic",
        "spacex",
        "xai",
        "tasklet",
        "openai",
        "google_deepmind",
        "microsoft",
        "aws",
        "meta",
        "tesla",
    }
    assert set(tracks) == expected

    spacex = tracks["spacex"]
    assert isinstance(spacex, dict)
    assert spacex["public_inventory_complete"] is True
    assert spacex["public_repository_count"] == 12

    openai = tracks["openai"]
    microsoft = tracks["microsoft"]
    aws = tracks["aws"]
    assert isinstance(openai, dict) and openai["public_inventory_complete"] is False
    assert isinstance(microsoft, dict) and microsoft["public_inventory_complete"] is False
    assert isinstance(aws, dict) and aws["public_inventory_complete"] is False


def test_public_graph_promotion_requires_current_evidence() -> None:
    manifest = load_manifest()
    release_gate = manifest["next_release_gate"]
    assert isinstance(release_gate, dict)

    required = release_gate["required_before_public_graph_promotion"]
    assert isinstance(required, list)
    assert "current-SHA observation" in required
    assert "positive-count test receipt" in required
    assert "provenance classification" in required
    assert "no unresolved critical blocker" in required


def test_private_references_remain_explicitly_private() -> None:
    manifest = load_manifest()
    private = manifest["private_architecture_references"]
    assert isinstance(private, list)
    assert len(private) == len(set(private))
    assert all(isinstance(repository, str) for repository in private)
    assert all(repository.startswith("GlacierEQ/") for repository in private)
    assert "GlacierEQ/FILEBOSS" in private
    assert "GlacierEQ/MEGA-PDF" in private
    assert "GlacierEQ/job-app" in private
