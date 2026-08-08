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
SOURCE_COMMIT = "b" * 40


def _load_builder() -> ModuleType:
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
        "schema": "glaciereq.public-portfolio-projection.v2",
        "truth_boundary": {
            "native_estate_cardinality_intentionally_not_published": True,
            "private_repository_identities_omitted": True,
            "restricted_namespaces_omitted": True,
            "projection_is_derived_not_hand_curated": True,
            "observed_pressure_and_inferred_bottleneck_are_distinct": True,
            "role_projection_is_capability_fit_not_employer_endorsement": True,
        },
        "systems": [
            {
                "system_id": "job_app_helix",
                "canonical_repository": "GlacierEQ/job-app-helix",
                "flagship_level": "L5",
                "role": "Portfolio compiler",
            }
        ],
        "capabilities": [
            {
                "capability": "deterministic_verification",
                "donor_system_count": 1,
                "repetition_state": "SINGLE_SYSTEM_SIGNAL",
                "donors": [{"system_id": "job_app_helix"}],
            }
        ],
        "companies": [
            {
                "company_id": "openai",
                "display_name": "OpenAI",
                "track_state": "MAPPED_NOT_RECRUITER_READY",
                "target_roles": ["Applied AI Engineer"],
                "recruiter_thesis": "Evidence-bound AI systems.",
                "second_depth_stage": "PROBLEM_BOUNDED",
                "claim_ceiling": "externally_bounded_problem_alignment",
                "next_gate": "Refresh the public role and source snapshot.",
                "intelligence": {
                    "research_as_of": "2026-08-05",
                    "freshness_state": (
                        "HISTORICAL_SOURCE_SNAPSHOT_REQUIRES_REFRESH_BEFORE_LIVE_APPLICATION"
                    ),
                    "observed_current_pressure": "Official-source observed pressure.",
                    "inferred_bottleneck": "Explicit GlacierEQ inference.",
                    "inferred_brick_wall": "Explicit GlacierEQ inference.",
                    "leverage_mechanism": "Use proof-bound orchestration.",
                    "expected_impact": "Reduce unreviewable automation.",
                    "application_move": "Lead with evidence-bound agent infrastructure.",
                    "next_deep_dive": "Refresh current public role evidence.",
                    "official_sources": [
                        {
                            "title": "Official source",
                            "url": "https://example.test/source",
                            "source_sha256": "a" * 64,
                            "observed_signal": "Observed public signal.",
                            "publisher": "Example",
                        }
                    ],
                    "inference_boundary": "Facts and inferences remain distinct.",
                },
                "systems": [
                    {
                        "system_id": "job_app_helix",
                        "capabilities": [
                            "agent_orchestration",
                            "deterministic_verification",
                        ],
                        "promotion_score": {
                            "score": 88.0,
                            "coverage": 1.0,
                            "complete": True,
                            "components": {
                                "originality": 100.0,
                                "technical_depth": 90.0,
                                "verification": 90.0,
                                "transferability": 80.0,
                                "target_relevance": 80.0,
                            },
                            "public_visibility_derived_separately": True,
                        },
                    }
                ],
                "audience_projection": {
                    "recruiter": ["job_app_helix"],
                    "company_reviewer": ["job_app_helix"],
                    "senior_engineer": ["job_app_helix"],
                },
                "role_projection": {
                    "Applied AI Engineer": {
                        "profile_capabilities": [
                            "agent_orchestration",
                            "deterministic_verification",
                        ],
                        "coverage_state": "MAPPED_ROLE",
                        "systems": [
                            {
                                "system_id": "job_app_helix",
                                "fit_score": 100.0,
                                "matched_capabilities": [
                                    "agent_orchestration",
                                    "deterministic_verification",
                                ],
                                "promotion_score": 88.0,
                            }
                        ],
                    }
                },
            }
        ],
        "projection_id": "c" * 64,
    }


def _write_projection(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "projection.json"
    path.write_text(
        json.dumps(_projection() if payload is None else payload),
        encoding="utf-8",
    )
    return path


def test_compiled_site_adds_public_projection_without_estate_leak(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT, _write_projection(tmp_path))

    index = (output / "index.html").read_text(encoding="utf-8")
    projection = (output / "estate-projection.json").read_text(encoding="utf-8")
    assert 'id="compiler"' in index
    assert 'href="#compiler"' in index
    assert "connect-src 'self'" in index
    assert "connect-src 'none'" not in index
    assert "Observed · source-backed" in index
    assert "GlacierEQ inference" in index
    assert (output / "compiler.css").is_file()
    assert (output / "compiler.js").is_file()
    assert (output / "estate-projection.json").is_file()
    assert "native_repository_count" not in projection
    assert '"repository_count"' not in projection
    assert "private_repository_count" not in projection


def test_compiled_deployment_manifest_hashes_new_projection_assets(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT, _write_projection(tmp_path))

    manifest = json.loads(
        (output / "deployment-manifest.json").read_text(encoding="utf-8")
    )
    rows = {row["path"]: row for row in manifest["files"]}
    for relative in ("compiler.css", "compiler.js", "estate-projection.json"):
        path = output / relative
        assert relative in rows
        assert rows[relative]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_compiler_javascript_never_uses_inner_html() -> None:
    script = (ROOT / "site" / "compiler.js").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert 'fetch("estate-projection.json"' in script
    assert 'credentials: "same-origin"' in script


def test_projection_false_truth_boundary_fails_closed(tmp_path: Path) -> None:
    builder = _load_builder()
    payload = _projection()
    payload["truth_boundary"]["private_repository_identities_omitted"] = False
    with pytest.raises(builder.ProjectionError, match="truth boundary"):
        builder.build(tmp_path / "site", SOURCE_COMMIT, _write_projection(tmp_path, payload))


@pytest.mark.parametrize("forbidden", ["native_repository_count", "repository_count"])
def test_projection_estate_cardinality_fails_closed(
    tmp_path: Path,
    forbidden: str,
) -> None:
    builder = _load_builder()
    payload = _projection()
    payload["companies"][0][forbidden] = 598
    with pytest.raises(builder.ProjectionError, match="Forbidden estate cardinality"):
        builder.build(tmp_path / "site", SOURCE_COMMIT, _write_projection(tmp_path, payload))


def test_wrapper_without_projection_preserves_canonical_static_site(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT)

    index = (output / "index.html").read_text(encoding="utf-8")
    assert 'id="compiler"' not in index
    assert "connect-src 'none'" in index
    assert not (output / "estate-projection.json").exists()
