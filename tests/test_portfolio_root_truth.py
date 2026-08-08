from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_portfolio_root_truth.py"
EXPECTED_PROJECTIONS = {
    "public_portal",
    "resume_shapeshifter",
    "company_application_packets",
    "machine_runtime",
    "cloud_indexes",
}
ESTATE_SOURCE_IDS = {
    "estate_compiler_policy",
    "estate_projection_policy",
    "estate_facts",
    "external_company_intelligence",
}
PUBLIC_SAFE_ESTATE_SOURCE_IDS = {
    "estate_compiler_policy",
    "estate_projection_policy",
    "external_company_intelligence",
}


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_portfolio_root_truth", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_root_truth_validation_passes() -> None:
    receipt = load_validator().validate()
    company_dossiers = load_json("manifests/company_dossiers.json")
    required_company_tracks = company_dossiers["required_company_tracks"]

    assert receipt["status"] == "PASS"
    assert receipt["scope"] == "CONTROL_PLANE_SOURCES_ONLY"
    assert receipt["projection_freshness"]["all_projections_current"] is False
    assert receipt["projection_freshness"]["state"] == "PENDING_CONSUMER_RECEIPTS"
    assert set(receipt["projection_freshness"]["projections"]) == EXPECTED_PROJECTIONS
    assert receipt["counts"]["total_repositories"] == 67
    assert receipt["counts"]["workspace_repositories"] == 66
    assert len(required_company_tracks) == 76
    assert receipt["counts"]["company_tracks"] == len(required_company_tracks)
    assert receipt["counts"]["flagship_systems"] == 17
    assert receipt["counts"]["projections"] == len(EXPECTED_PROJECTIONS)
    assert receipt["counts"]["required_sources"] == 14
    assert "manifests/company_second_depth.json" in receipt["source_hashes"]
    assert "manifests/estate_compiler.json" in receipt["source_hashes"]
    assert "manifests/estate_projection_policy.json" in receipt["source_hashes"]
    assert "manifests/estate_facts.json" in receipt["source_hashes"]
    assert (
        "manifests/application_intelligence/company_bottleneck_atlas.external.json"
        in receipt["source_hashes"]
    )
    assert len(receipt["source_digest"]) == 64
    assert len(receipt["receipt_sha256"]) == 64
    assert all(receipt["invariants"].values())


def test_every_projection_resolves_declared_sources() -> None:
    manifest = load_json("manifests/portfolio_root_truth.json")
    source_ids = {source["id"] for source in manifest["sources"]}
    projection_ids = {projection["id"] for projection in manifest["projections"]}
    assert len(source_ids) == len(manifest["sources"])
    assert "company_second_depth" in source_ids
    assert source_ids >= ESTATE_SOURCE_IDS
    assert projection_ids == EXPECTED_PROJECTIONS
    for projection in manifest["projections"]:
        assert projection["required_sources"]
        assert set(projection["required_sources"]) <= source_ids
        assert "company_second_depth" in projection["required_sources"]


def test_public_estate_projection_boundary_is_fail_closed() -> None:
    manifest = load_json("manifests/portfolio_root_truth.json")
    rows = {projection["id"]: projection for projection in manifest["projections"]}
    public_ids = {"public_portal", "resume_shapeshifter", "machine_runtime"}

    for projection_id in public_ids:
        sources = set(rows[projection_id]["required_sources"])
        assert sources >= PUBLIC_SAFE_ESTATE_SOURCE_IDS
        assert "estate_facts" not in sources
        assert rows[projection_id]["may_publish_private_records"] is False
        boundary = rows[projection_id].get("boundary", "")
        assert "private" in boundary.lower()

    assert "estate_facts" in rows["company_application_packets"]["required_sources"]
    assert "estate_facts" in rows["cloud_indexes"]["required_sources"]


def test_estate_compiler_policy_matches_public_v2_artifact_boundary() -> None:
    policy = load_json("manifests/estate_compiler.json")
    privacy = policy["privacy"]
    outputs = policy["outputs"]

    assert privacy["internal_receipts_remain_runner_local"] is True
    assert privacy["workflow_uploads"] == ["public-safe-company-projection-v2.json"]
    assert outputs["public_safe_projection"] == "public-safe-company-projection-v2.json"


def test_flagships_exactly_match_required_named_registry() -> None:
    registry = load_json("manifests/flagship_registry.json")
    required = registry["required_named_flagships"]
    actual = [row["system_id"] for row in registry["flagships"]]
    assert len(required) == len(set(required))
    assert len(actual) == len(set(actual))
    assert set(actual) == set(required)
    assert len(actual) == 17


def test_root_manifest_forbids_competing_truth() -> None:
    manifest = load_json("manifests/portfolio_root_truth.json")
    model = manifest["truth_model"]
    assert model["control_plane"] == "GlacierEQ/job-app-helix"
    assert model["stale_on_source_head_change"] is True
    assert model["fail_closed_on_missing_or_unsupported_evidence"] is True
    assert "do not become independent sources" in model["projection_rule"]
    assert "authenticated-estate" in model["portfolio_authority"]


def test_public_projections_cannot_publish_private_records() -> None:
    manifest = load_json("manifests/portfolio_root_truth.json")
    public_ids = {"public_portal", "resume_shapeshifter", "machine_runtime"}
    rows = {projection["id"]: projection for projection in manifest["projections"]}
    assert public_ids <= rows.keys()
    for projection_id in public_ids:
        assert rows[projection_id]["may_publish_private_records"] is False
        assert "company_second_depth" in rows[projection_id]["required_sources"]


def test_public_projection_admission_is_fail_closed() -> None:
    validator = load_validator()
    assert validator.public_projection_eligible("L5", "PROMOTED", "public") is True
    assert validator.public_projection_eligible("L4", "REFERENCE_ONLY", "public") is True
    assert validator.public_projection_eligible("L0", "PROMOTED", "public") is False
    assert validator.public_projection_eligible("L4", "QUARANTINED", "public") is False
    assert validator.public_projection_eligible("L4", "EXCLUDED", "public") is False
    assert validator.public_projection_eligible("L4", "PROMOTED", "private") is False
