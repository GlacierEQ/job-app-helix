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
    spec = importlib.util.spec_from_file_location(
        "compiled_recruiter_site",
        BUILDER_PATH,
    )
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
    boundary = {
        "private_repository_identities_omitted": True,
        "legal_private_records_omitted": True,
        "support_only_systems_omitted_from_accomplishment_projection": True,
        "experiment_systems_omitted_from_accomplishment_projection": True,
        "unresolved_lineage_omitted_from_accomplishment_projection": True,
        "native_estate_cardinality_intentionally_not_published": True,
        "observed_pressure_and_inferred_bottleneck_are_distinct": True,
        "role_projection_is_capability_fit_not_employer_endorsement": True,
        "semantic_capability_proof_is_exact_head_and_public_only": True,
    }
    role = "Agent Infrastructure Engineer"
    capabilities = [
        "deterministic-orchestration",
        "provenance-and-evidence",
    ]
    system = {
        "system_id": "sys-helix",
        "source_repository": "GlacierEQ/job-app-helix",
        "promotion_state": "PROMOTED",
        "visibility": "public",
        "visibility_decision": "PUBLIC_ELIGIBLE",
        "promotion_score": 91.0,
        "capabilities": capabilities,
    }
    company = {
        "company_id": "openai",
        "display_name": "OpenAI",
        "target_roles": [role],
        "operating_problem": "Refresh current role evidence.",
        "dossier_next_gate": "Refresh current role evidence.",
        "recruiter_thesis": "Evidence-bound agent infrastructure.",
        "observed_operating_pressure": "Source-backed pressure.",
        "inferred_bottleneck": "GlacierEQ inference.",
        "inferred_brick_wall": "GlacierEQ brick-wall inference.",
        "application_move": "Lead with proof-bound orchestration.",
        "research_as_of": "2026-08-05",
        "freshness_state": "HISTORICAL_SOURCE_SNAPSHOT",
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
        "reference_systems": ["sys-helix"],
        "capabilities": capabilities,
        "minimal_proof_surface": ["sys-helix"],
        "audience_projection": {
            "recruiter": ["sys-helix"],
            "company_reviewer": ["sys-helix"],
            "senior_engineer": ["sys-helix"],
        },
        "role_projection": {
            role: {
                "profile_capabilities": capabilities,
                "coverage_state": "MAPPED_ROLE",
                "systems": [
                    {
                        "system_id": "sys-helix",
                        "fit_score": 100.0,
                        "matched_capabilities": capabilities,
                        "promotion_score": 91.0,
                    }
                ],
            }
        },
        "ranked_evidence": [system],
        "capability_proofs": [
            {
                "capability_id": "provenance-and-evidence",
                "system_id": "sys-helix",
                "source_repository": "GlacierEQ/job-app-helix",
                "head_sha": "a" * 40,
                "proof_state": "SOURCE_AND_EXACT_HEAD_CHECKS_VERIFIED",
                "admission_state": "REFERENCE_ONLY",
                "evidence_refs": ["src/job_app_helix/estate_compiler.py"],
                "proof_receipts": [
                    {
                        "kind": "check_run",
                        "id": 12345,
                        "name": "CI",
                        "head_sha": "a" * 40,
                        "conclusion": "success",
                    }
                ],
            }
        ],
        "non_affiliation": "No affiliation implied.",
    }
    return {
        "schema": "glaciereq.estate-public-projection.v2",
        "source_digest": "e" * 64,
        "boundary": boundary,
        "company_projections": [company],
    }


def _write(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "projection.json"
    value = _projection() if payload is None else payload
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_compiled_site_routes_public_estate_projection(
    tmp_path: Path,
) -> None:
    builder = _builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT, _write(tmp_path))

    index = (output / "index.html").read_text(encoding="utf-8")
    projection = (output / "estate-projection.json").read_text(
        encoding="utf-8"
    )
    assert 'id="compiler"' in index
    assert 'href="#compiler"' in index
    assert index.index('id="compiler"') < index.index('id="package"')
    assert "Start with the company problem. Compile the proof." in index
    assert 'id="compiler-chain-pressure"' in index
    assert 'id="compiler-chain-capability"' in index
    assert 'id="compiler-chain-systems"' in index
    assert 'id="compiler-chain-proof"' in index
    assert 'id="compiler-capability-proofs"' in index
    assert 'id="compiler-capability-proof-summary"' in index
    assert "Capability proof lens" in index
    assert "Observed · source-backed" in index
    assert "GlacierEQ inference" in index
    assert "connect-src 'self'" in index
    assert "connect-src 'none'" not in index
    assert (output / "compiler.css").is_file()
    assert (output / "compiler.js").is_file()
    assert (output / "capability_proof_lens.css").is_file()
    assert (output / "capability_proof_lens.js").is_file()
    assert "native_repository_count" not in projection
    assert "reference_accomplishments" not in projection


def test_compiled_manifest_hashes_projection_assets(
    tmp_path: Path,
) -> None:
    builder = _builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT, _write(tmp_path))
    manifest = json.loads(
        (output / "deployment-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    rows = {row["path"]: row for row in manifest["files"]}
    for relative in (
        "compiler.css",
        "compiler.js",
        "capability_proof_lens.css",
        "capability_proof_lens.js",
        "estate-projection.json",
    ):
        path = output / relative
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        assert rows[relative]["sha256"] == expected


def test_compiler_javascript_is_same_origin_safe_and_routable() -> None:
    script = (ROOT / "site" / "compiler.js").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert 'fetch("estate-projection.json"' in script
    assert 'credentials: "same-origin"' in script
    assert "renderCompanies" in script
    assert "companySelect.appendChild(option)" in script
    assert "URLSearchParams" in script
    assert "window.history.replaceState" in script
    assert 'document.createElement("meter")' in script


def test_capability_proof_lens_is_same_origin_and_depth_aware() -> None:
    script = (ROOT / "site" / "capability_proof_lens.js").read_text(
        encoding="utf-8"
    )
    assert "innerHTML" not in script
    assert 'fetch("estate-projection.json"' in script
    assert 'credentials: "same-origin"' in script
    assert "MutationObserver" in script
    assert 'depth === "senior_engineer"' in script
    assert "evidenceHref" in script
    assert "proof_receipts" in script
    assert "source_repository.startsWith(\"GlacierEQ/\")" in script


def test_false_public_boundary_fails_closed(tmp_path: Path) -> None:
    builder = _builder()
    payload = _projection()
    payload["boundary"]["legal_private_records_omitted"] = False
    with pytest.raises(builder.ProjectionError, match="boundary"):
        builder.build(
            tmp_path / "site",
            SOURCE_COMMIT,
            _write(tmp_path, payload),
        )


def test_capability_proof_head_drift_fails_closed(tmp_path: Path) -> None:
    builder = _builder()
    payload = _projection()
    payload["company_projections"][0]["capability_proofs"][0][
        "proof_receipts"
    ][0]["head_sha"] = "b" * 40
    with pytest.raises(builder.ProjectionError, match="head_sha drifted"):
        builder.build(
            tmp_path / "site",
            SOURCE_COMMIT,
            _write(tmp_path, payload),
        )


@pytest.mark.parametrize(
    "unsafe_path",
    ["../secret.txt", "/etc/passwd", "src//connector.py", "src/./connector.py"],
)
def test_capability_proof_unsafe_evidence_path_fails_closed(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    builder = _builder()
    payload = _projection()
    payload["company_projections"][0]["capability_proofs"][0][
        "evidence_refs"
    ] = [unsafe_path]
    with pytest.raises(builder.ProjectionError, match="evidence_refs are unsafe"):
        builder.build(
            tmp_path / "site",
            SOURCE_COMMIT,
            _write(tmp_path, payload),
        )


@pytest.mark.parametrize(
    "forbidden",
    ["native_repository_count", "reference_accomplishments"],
)
def test_public_estate_counts_are_rejected(
    tmp_path: Path,
    forbidden: str,
) -> None:
    builder = _builder()
    payload = _projection()
    payload["company_projections"][0][forbidden] = 598
    with pytest.raises(
        builder.ProjectionError,
        match="Forbidden estate cardinality",
    ):
        builder.build(
            tmp_path / "site",
            SOURCE_COMMIT,
            _write(tmp_path, payload),
        )


def test_wrapper_without_projection_preserves_static_site(
    tmp_path: Path,
) -> None:
    builder = _builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT)
    index = (output / "index.html").read_text(encoding="utf-8")
    assert 'id="compiler"' not in index
    assert "connect-src 'none'" in index
