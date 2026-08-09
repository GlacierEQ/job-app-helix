from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_compiled_recruiter_site.py"
HEAD = "a" * 40


def _builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("proof_boundary_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _company() -> dict:
    return {
        "ranked_evidence": [
            {
                "system_id": "sys-public",
                "source_repository": "GlacierEQ/public-donor",
                "visibility": "public",
                "visibility_decision": "PUBLIC_ELIGIBLE",
                "promotion_state": "REFERENCE_ONLY",
            }
        ],
        "capability_proofs": [
            {
                "capability_id": "bounded-query-facade",
                "system_id": "sys-public",
                "source_repository": "GlacierEQ/public-donor",
                "head_sha": HEAD,
                "proof_state": "SOURCE_AND_EXACT_HEAD_CHECKS_VERIFIED",
                "admission_state": "REFERENCE_ONLY",
                "evidence_refs": ["src/connector.py"],
                "proof_receipts": [
                    {
                        "kind": "check_run",
                        "id": 101,
                        "name": "CI",
                        "head_sha": HEAD,
                        "conclusion": "success",
                    }
                ],
            }
        ],
    }


def test_deployment_boundary_accepts_matching_verified_public_proof() -> None:
    builder = _builder()
    builder._validate_capability_proofs(_company(), "$.company")


def test_deployment_boundary_rejects_repository_not_bound_to_public_evidence() -> None:
    builder = _builder()
    company = _company()
    company["capability_proofs"][0]["source_repository"] = "GlacierEQ/private-case-source"
    with pytest.raises(builder.ProjectionError, match="does not match public ranked_evidence"):
        builder._validate_capability_proofs(company, "$.company")


def test_deployment_boundary_rejects_unverified_proof_state() -> None:
    builder = _builder()
    company = _company()
    company["capability_proofs"][0]["proof_state"] = "UNVERIFIED"
    with pytest.raises(builder.ProjectionError, match="proof_state is not verified"):
        builder._validate_capability_proofs(company, "$.company")
