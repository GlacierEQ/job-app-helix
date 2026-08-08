from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_compiled_recruiter_site.py"
SOURCE_COMMIT = "d" * 40


def _builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("compiled_recruiter_site", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _projection() -> dict:
    return {
        "schema": "glaciereq.estate-public-projection.v2",
        "source_digest": "e" * 64,
        "boundary": {
            "private_repository_identities_omitted": True,
            "legal_private_records_omitted": True,
            "support_only_systems_omitted_from_accomplishment_projection": True,
            "experiment_systems_omitted_from_accomplishment_projection": True,
            "unresolved_lineage_omitted_from_accomplishment_projection": True,
            "native_estate_cardinality_intentionally_not_published": True,
            "observed_pressure_and_inferred_bottleneck_are_distinct": True,
            "role_projection_is_capability_fit_not_employer_endorsement": True,
        },
        "company_projections": [
            {
                "company_id": "openai",
                "display_name": "OpenAI",
                "target_roles": ["Agent Infrastructure Engineer"],
                "operating_problem": "Refresh current role evidence.",
                "dossier_next_gate": "Refresh current role evidence.",
                "recruiter_thesis": "Evidence-bound agent infrastructure.",
                "observed_operating_pressure": "Source-backed pressure.",
                "inferred_bottleneck": "GlacierEQ inference.",
                "inferred_brick_wall": "GlacierEQ brick-wall inference.",
                "application_move": "Lead with proof-bound orchestration.",
                "research_as_of": "2026-08-05",
                "freshness_state": "HISTORICAL_SOURCE_SNAPSHOT_REQUIRES_REFRESH_BEFORE_LIVE_APPLICATION",
                "official_sources": [
                    {
                        "title": "Official source",
                        "url": "https://example.test/source",
                        "publisher": "Example",
                        "source_sha256": "f" * 64,
                        "observed_signal": "Observed signal.",
                    }
                ],
                "inference_boundary": "Facts and inferences remain distinct.",
                "canonical_systems": ["sys-helix"],
                "capabilities": ["deterministic-orchestration", "provenance-and-evidence"],
                "minimal_proof_surface": ["sys-helix"],
                "audience_projection": {
                    "recruiter": ["sys-helix"],
                    "company_reviewer": ["sys-helix"],
                    "senior_engineer": ["sys-helix"],
                },
                "role_projection": {
                    "Agent Infrastructure Engineer": {
                        "profile_capabilities": ["deterministic-orchestration", "provenance-and-evidence"],
                        "coverage_state": "MAPPED_ROLE",
                        "systems": [
                            {
                                "system_id": "sys-helix",
                                "fit_score": 100.0,
                                "matched_capabilities": ["deterministic-orchestration", "provenance-and-evidence"],
                                "promotion_score": 91.0,
                            }
                        ],
                    }
                },
                "ranked_evidence": [
                    {
                        "system_id": "sys-helix",
                        "source_repository": "GlacierEQ/job-app-helix",
                        "promotion_state": "PROMOTED",
                        "visibility": "public",
                        "visibility_decision": "PUBLIC_ELIGIBLE",
                        "promotion_score": 91.0,
                        "capabilities": ["deterministic-orchestration", "provenance-and-evidence"],
                    }
                ],
                "non_affiliation": "No affiliation implied.",
            }
        ],
    }


def _write(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "projection.json"
    path.write_text(json.dumps(_projection() if payload is None else payload), encoding="utf-8")
    return path


def test_compiled_site_routes_public_estate_projection(tmp_path: Path) -> None:
    builder = _builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT, _write(tmp_path))
    index = (output / "index.html").read_text(encoding="utf-8")
    projection = (output / "estate-projection.json").read_text(encoding="utf-8")
    assert 'id="compiler"' in index
    assert 'href="#compiler"' in index
    assert "Observed · source-backed" in index
    assert "GlacierEQ inference" in index
    assert "connect-src 'self'" in index
    assert "connect-src 'none'" not in index
    assert (output / "compiler.css").is_file()
    assert (output / "compiler.js").is_file()
    assert "native_repository_count" not in projection
    assert "canonical_accomplishments" not in projection


def test_compiled_manifest_hashes_projection_assets(tmp_path: Path) -> None:
    builder = _builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT, _write(tmp_path))
    manifest = json.loads((output / "deployment-manifest.json").read_text(encoding="utf-8"))
    rows = {row["path"]: row for row in manifest["files"]}
    for relative in ("compiler.css", "compiler.js", "estate-projection.json"):
        path = output / relative
        assert rows[relative]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_compiler_javascript_is_same_origin_and_no_inner_html() -> None:
    script = (ROOT / "site" / "compiler.js").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert 'fetch("estate-projection.json"' in script
    assert 'credentials: "same-origin"' in script


def test_false_public_boundary_fails_closed(tmp_path: Path) -> None:
    builder = _builder()
    payload = _projection()
    payload["boundary"]["legal_private_records_omitted"] = False
    with pytest.raises(builder.ProjectionError, match="boundary"):
        builder.build(tmp_path / "site", SOURCE_COMMIT, _write(tmp_path, payload))


@pytest.mark.parametrize("forbidden", ["native_repository_count", "canonical_accomplishments"])
def test_public_estate_counts_are_rejected(tmp_path: Path, forbidden: str) -> None:
    builder = _builder()
    payload = _projection()
    payload["company_projections"][0][forbidden] = 598
    with pytest.raises(builder.ProjectionError, match="Forbidden estate cardinality"):
        builder.build(tmp_path / "site", SOURCE_COMMIT, _write(tmp_path, payload))


def test_wrapper_without_projection_preserves_existing_static_site(tmp_path: Path) -> None:
    builder = _builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT)
    index = (output / "index.html").read_text(encoding="utf-8")
    assert 'id="compiler"' not in index
    assert "connect-src 'none'" in index
