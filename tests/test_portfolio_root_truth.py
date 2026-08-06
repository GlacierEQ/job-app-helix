from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_portfolio_root_truth.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_portfolio_root_truth", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_root_truth_validation_passes() -> None:
    receipt = load_validator().validate()
    assert receipt["status"] == "PASS"
    assert receipt["counts"]["total_repositories"] == 67
    assert receipt["counts"]["workspace_repositories"] == 66
    assert receipt["counts"]["company_tracks"] >= 49
    assert receipt["counts"]["flagship_systems"] >= 17
    assert receipt["counts"]["projections"] >= 5
    assert len(receipt["source_digest"]) == 64
    assert len(receipt["receipt_sha256"]) == 64
    assert all(receipt["invariants"].values())


def test_every_projection_resolves_declared_sources() -> None:
    manifest = json.loads((ROOT / "manifests" / "portfolio_root_truth.json").read_text(encoding="utf-8"))
    source_ids = {source["id"] for source in manifest["sources"]}
    assert len(source_ids) == len(manifest["sources"])
    for projection in manifest["projections"]:
        assert projection["required_sources"]
        assert set(projection["required_sources"]) <= source_ids


def test_root_manifest_forbids_competing_truth() -> None:
    manifest = json.loads((ROOT / "manifests" / "portfolio_root_truth.json").read_text(encoding="utf-8"))
    model = manifest["truth_model"]
    assert model["control_plane"] == "GlacierEQ/job-app-helix"
    assert model["stale_on_source_head_change"] is True
    assert model["fail_closed_on_missing_or_unsupported_evidence"] is True
    assert "do not become independent sources" in model["projection_rule"]


def test_public_projections_cannot_publish_private_records() -> None:
    manifest = json.loads((ROOT / "manifests" / "portfolio_root_truth.json").read_text(encoding="utf-8"))
    public_ids = {"public_portal", "resume_shapeshifter", "machine_runtime"}
    rows = {projection["id"]: projection for projection in manifest["projections"]}
    assert public_ids <= rows.keys()
    for projection_id in public_ids:
        assert rows[projection_id]["may_publish_private_records"] is False
