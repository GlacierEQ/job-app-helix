from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from job_app_helix.repo_excellence import ExcellenceContractError, validate_repo_excellence_record

ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = ROOT / "manifests/repo_excellence/apex-github-worker.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    framed = b"blob " + str(len(payload)).encode() + b"\0" + payload
    return hashlib.sha1(framed, usedforsecurity=False).hexdigest()


def test_apex_canonical_anchor_receipt_remains_exact_and_semantically_bound() -> None:
    record = _load(RECORD_PATH)
    validated = validate_repo_excellence_record(record)
    pointer = validated["canonical_position_receipt"]
    receipt_path = ROOT / pointer["path"]
    receipt = _load(receipt_path)

    assert validated["state"] == "EVOLVING"
    assert _git_blob_sha(receipt_path) == pointer["blob_sha"]
    assert receipt["repository"]["full_name"] == validated["identity"]["repository"]
    assert receipt["repository"]["canonical_head"] == validated["identity"]["canonical_head"]
    assert receipt["repository"]["canonical_role"] == validated["canonical_role"]
    assert receipt["repository"]["capability_id"] == validated["capability_id"]
    assert receipt["lineage"]["action"] == validated["identity"]["lineage_action"]
    assert receipt["lineage"]["source_blob_sha"] == pointer["source_blob_sha"]
    assert receipt["decision"]["canonicalization_blockers"] == []
    assert receipt["decision"]["retained_noncanonicalization_blockers"] == [
        blocker["id"] for blocker in validated["blockers"]
    ]
    assert receipt["claim_boundary"]["company_stage_unchanged"] == (
        validated["company_evidence"]["stage"]
    )
    assert receipt["claim_boundary"]["company_claim_ceiling_unchanged"] == (
        validated["company_evidence"]["claim_ceiling"]
    )


def test_apex_evolving_projection_preserves_anchor_and_current_head() -> None:
    record = _load(RECORD_PATH)
    validated = validate_repo_excellence_record(record)
    assert validated["projection_refs"] == [
        "manifests/company_projections/github_merge_authority.json"
    ]
    projection = _load(ROOT / validated["projection_refs"][0])
    implementation = projection["implementation"]
    identity = validated["identity"]

    assert implementation["repository"] == identity["repository"]
    assert implementation["canonical_head"] == identity["canonical_head"]
    assert implementation["evolved_head"] == identity["current_evolved_head"]
    assert implementation["capability"] == validated["capability_id"]
    assert implementation["state"] == "EVOLVING"
    assert projection["stage"] == "CLAIM_PROMOTED"
    assert projection["claim_ceiling"] == "proof_bound_company_specific"
    assert projection["stage"] == validated["company_evidence"]["stage"]
    assert projection["claim_ceiling"] == validated["company_evidence"]["claim_ceiling"]


def test_repository_evolution_cannot_silently_advance_company_claim() -> None:
    record = _load(RECORD_PATH)
    mutated = copy.deepcopy(record)
    mutated["company_evidence"]["stage"] = "GITHUB_ADOPTED"
    with pytest.raises(ExcellenceContractError, match="cannot advance company stage"):
        validate_repo_excellence_record(mutated)

    mutated = copy.deepcopy(record)
    mutated["company_evidence"]["claim_ceiling"] = "github_adopted"
    with pytest.raises(ExcellenceContractError, match="cannot advance company claim ceiling"):
        validate_repo_excellence_record(mutated)
