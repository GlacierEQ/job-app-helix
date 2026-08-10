#!/usr/bin/env python3
"""Fail-closed validation for repository excellence and CANONICAL admission."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD_DIR = ROOT / "manifests" / "repo_excellence"
POLICY_PATH = RECORD_DIR / "canonicalization_policy.json"
SHA40 = re.compile(r"^[a-f0-9]{40}$")
ALLOWED_STATES = {
    "DISCOVERED",
    "IDENTITY_RESOLVED",
    "PROBLEM_VERIFIED",
    "TARGET_CONTRACTED",
    "SEEDED",
    "VERTICAL_SLICE",
    "IMPLEMENTED",
    "TESTED",
    "ADVERSARIAL_VERIFIED",
    "OPERABLE",
    "PROOF_REPRODUCED",
    "PROMOTED",
    "CANONICAL",
    "EVOLVING",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_projection(record: dict, projection_ref: str) -> None:
    path = ROOT / projection_ref
    require(path.is_file(), f"missing declared projection: {projection_ref}")
    projection = load_json(path)
    implementation = projection.get("implementation", {})
    identity = record["identity"]
    require(
        implementation.get("repository") == identity["repository"],
        f"{projection_ref}: repository identity drift",
    )
    require(
        implementation.get("canonical_head") == identity["canonical_head"],
        f"{projection_ref}: canonical head drift",
    )
    require(
        implementation.get("state") == record["state"],
        f"{projection_ref}: implementation state drift",
    )


def validate_canonical(record: dict, policy: dict) -> None:
    identity = record.get("identity", {})
    require(record.get("state") in {"CANONICAL", "EVOLVING"}, "canonical validator state mismatch")
    require(SHA40.fullmatch(str(identity.get("canonical_head", ""))) is not None, "canonical head is not immutable")
    require(record.get("canonical_role"), "canonical role missing")
    require(record.get("capability_id"), "canonical capability_id missing")

    gates = record.get("gates", {})
    for gate in policy["required_record_gates"]:
        require(gates.get(gate) is True, f"CANONICAL requires gate {gate}=true")

    pointer = record.get("canonical_position_receipt", {})
    receipt_path = pointer.get("path")
    require(isinstance(receipt_path, str) and receipt_path, "canonical position receipt path missing")
    full_receipt_path = ROOT / receipt_path
    require(full_receipt_path.is_file(), f"canonical position receipt missing: {receipt_path}")
    receipt = load_json(full_receipt_path)

    require(receipt.get("schema") == "glaciereq.repo-canonical-position-receipt.v1", "canonical receipt schema drift")
    require(receipt.get("status") == "PASS", "canonical receipt is not PASS")
    require(receipt.get("transition") == policy["transition"], "canonical transition receipt drift")

    repository = receipt.get("repository", {})
    require(repository.get("full_name") == identity.get("repository"), "canonical receipt repository drift")
    require(repository.get("repository_id") == identity.get("repository_id"), "canonical receipt repository id drift")
    require(repository.get("canonical_head") == identity.get("canonical_head"), "canonical receipt head drift")
    require(repository.get("default_branch") == identity.get("default_branch"), "canonical receipt default branch drift")
    require(repository.get("canonical_role") == record.get("canonical_role"), "canonical receipt role drift")
    require(repository.get("capability_id") == record.get("capability_id"), "canonical receipt capability drift")

    lineage = receipt.get("lineage", {})
    require(lineage.get("action") in policy["allowed_lineage_actions"], "canonical lineage action is not admitted")
    require(lineage.get("source_commit") == identity.get("canonical_head"), "lineage source commit drift")
    require(SHA40.fullmatch(str(lineage.get("source_blob_sha", ""))) is not None, "lineage source blob is not content-addressed")
    require("NEW_REPO" in lineage.get("excluded_actions", []), "duplicate-repository rejection missing from lineage")

    decision = receipt.get("decision", {})
    for flag in policy["required_receipt_flags"]:
        require(decision.get(flag) is True, f"canonical receipt requires {flag}=true")
    require(decision.get("canonicalization_blockers") == [], "canonicalization blockers remain")

    retained = set(decision.get("retained_noncanonicalization_blockers", []))
    record_blockers = {row.get("id") for row in record.get("blockers", []) if isinstance(row, dict)}
    require(record_blockers <= retained, "record blocker is not classified by canonical receipt")

    require(record.get("evolution", {}).get("next_gate") == policy["required_next_gate"], "CANONICAL next gate must be EVOLVING")

    refs = record.get("projection_refs", [])
    require(isinstance(refs, list) and refs, "CANONICAL record requires at least one declared projection_ref")
    for projection_ref in refs:
        validate_projection(record, projection_ref)

    claim = receipt.get("claim_boundary", {})
    require(claim.get("github_adoption_claimed") is False, "repository canonicalization cannot create adoption claim")
    require(claim.get("github_capability_production_deployment_claimed") is False, "repository canonicalization cannot create deployment claim")


def validate_record(record: dict, policy: dict) -> None:
    require(record.get("schema") == "glaciereq.repo-excellence.record.v1", "repo excellence schema drift")
    require(record.get("state") in ALLOWED_STATES, f"unknown repository excellence state: {record.get('state')}")
    identity = record.get("identity", {})
    require(identity.get("repository"), "repository identity missing")
    require(identity.get("repository_id"), "repository id missing")
    require(identity.get("default_branch"), "default branch missing")
    if record.get("state") in {"CANONICAL", "EVOLVING"}:
        validate_canonical(record, policy)


def main() -> None:
    policy = load_json(POLICY_PATH)
    require(policy.get("schema") == "glaciereq.repo-excellence-canonicalization-policy.v1", "canonicalization policy schema drift")
    records = sorted(path for path in RECORD_DIR.glob("*.json") if path.name != POLICY_PATH.name)
    require(records, "repo excellence registry is empty")
    for path in records:
        validate_record(load_json(path), policy)
        print(f"REPO EXCELLENCE PASS: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
