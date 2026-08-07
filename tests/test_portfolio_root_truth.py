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
    assert receipt["status"] == "PASS"
    assert receipt["scope"] == "CONTROL_PLANE_SOURCES_ONLY"
    assert receipt["projection_freshness"]["all_projections_current"] is False
    assert receipt["projection_freshness"]["state"] == "PENDING_CONSUMER_RECEIPTS"
    assert set(receipt["projection_freshness"]["projections"]) == EXPECTED_PROJECTIONS
    assert receipt["counts"]["total_repositories"] == 67
    assert receipt["counts"]["workspace_repositories"] == 66
    assert receipt["counts"]["company_tracks"] == 48
    assert receipt["counts"]["flagship_systems"] == 17
    assert receipt["counts"]["projections"] == len(EXPECTED_PROJECTIONS)
    assert len(receipt["source_digest"]) == 64
    assert len(receipt["receipt_sha256"]) == 64
    assert all(receipt["invariants"].values())


def test_every_projection_resolves_declared_sources() -> None:
    manifest = load_json("manifests/portfolio_root_truth.json")
    source_ids = {source["id"] for source in manifest["sources"]}
    projection_ids = {projection["id"] for projection in manifest["projections"]}
    assert len(source_ids) == len(manifest["sources"])
    assert projection_ids == EXPECTED_PROJECTIONS
    for projection in manifest["projections"]:
        assert projection["required_sources"]
        assert set(projection["required_sources"]) <= source_ids


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


def test_public_projections_cannot_publish_private_records() -> None:
    manifest = load_json("manifests/portfolio_root_truth.json")
    public_ids = {"public_portal", "resume_shapeshifter", "machine_runtime"}
    rows = {projection["id"]: projection for projection in manifest["projections"]}
    assert public_ids <= rows.keys()
    for projection_id in public_ids:
        assert rows[projection_id]["may_publish_private_records"] is False


def test_public_projection_admission_is_fail_closed() -> None:
    validator = load_validator()
    assert validator.public_projection_eligible("L5", "PROMOTED", "public") is True
    assert validator.public_projection_eligible("L4", "REFERENCE_ONLY", "public") is True
    assert validator.public_projection_eligible("L0", "PROMOTED", "public") is False
    assert validator.public_projection_eligible("L4", "QUARANTINED", "public") is False
    assert validator.public_projection_eligible("L4", "EXCLUDED", "public") is False
    assert validator.public_projection_eligible("L4", "PROMOTED", "private") is False
