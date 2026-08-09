from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .estate_compiler import public_safe_projection

PUBLIC_FIELDS = (
    "observed_operating_pressure",
    "inferred_bottleneck",
    "inferred_brick_wall",
    "leverage_mechanism",
    "expected_impact",
    "application_move",
    "next_deep_dive",
    "official_sources",
    "research_as_of",
    "freshness_state",
    "inference_boundary",
    "intelligence_state",
    "dossier_next_gate",
)
PUBLIC_ADMISSION_STATES = {"PROMOTED", "REFERENCE_ONLY"}


def public_intelligence_projection(
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    public = public_safe_projection(bundle)
    internal = {
        row["company_id"]: row
        for row in bundle["company_projection_registry"]["projections"]
    }
    for projection in public["company_projections"]:
        source = internal[str(projection["company_id"])]
        safe_ids = {
            row["system_id"]
            for row in projection.get("ranked_evidence", [])
        }
        for key in PUBLIC_FIELDS:
            projection[key] = source.get(key)
        projection["minimal_proof_surface"] = [
            system_id
            for system_id in source.get("minimal_proof_surface", [])
            if system_id in safe_ids
        ]
        projection["audience_projection"] = {
            audience: [
                system_id
                for system_id in systems
                if system_id in safe_ids
            ]
            for audience, systems in source.get(
                "audience_projection",
                {},
            ).items()
        }
        projection["role_projection"] = _public_role_projection(
            source,
            safe_ids,
        )
        projection["ranked_evidence"] = _public_ranked_evidence(
            projection,
            source,
        )
        projection["capability_proofs"] = _public_capability_proofs(
            bundle,
            projection,
            safe_ids,
        )

    public["schema"] = "glaciereq.estate-public-projection.v2"
    public["boundary"] = {
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
    return public


def _public_role_projection(
    source: Mapping[str, Any],
    safe_ids: set[str],
) -> dict[str, Any]:
    return {
        role: {
            "profile_capabilities": data.get("profile_capabilities", []),
            "coverage_state": data.get("coverage_state"),
            "systems": [
                row
                for row in data.get("systems", [])
                if row.get("system_id") in safe_ids
            ],
        }
        for role, data in source.get("role_projection", {}).items()
    }


def _public_ranked_evidence(
    projection: Mapping[str, Any],
    source: Mapping[str, Any],
) -> list[dict[str, Any]]:
    by_system = {
        row["system_id"]: row
        for row in source.get("ranked_evidence", [])
    }
    result: list[dict[str, Any]] = []
    for row in projection.get("ranked_evidence", []):
        system_id = row["system_id"]
        internal = by_system.get(system_id, {})
        result.append(
            {
                **row,
                "promotion_score": internal.get(
                    "promotion_score",
                    row.get("promotion_score"),
                ),
                "promotion_score_components": internal.get(
                    "promotion_score_components"
                ),
                "capabilities": internal.get("capabilities", []),
            }
        )
    return result


def _is_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_safe_repo_path(value: object) -> bool:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        return False
    normalized = value.replace("\\", "/")
    return all(segment not in {"", ".", ".."} for segment in normalized.split("/"))


def _public_capability_proofs(
    bundle: Mapping[str, Any],
    projection: Mapping[str, Any],
    safe_ids: set[str],
) -> list[dict[str, Any]]:
    company_id = str(projection["company_id"])
    allowed_capabilities = {
        value
        for value in projection.get("capabilities", [])
        if isinstance(value, str)
    }
    safe_evidence_pairs = {
        (row.get("system_id"), row.get("source_repository"))
        for row in projection.get("ranked_evidence", [])
        if isinstance(row, Mapping)
        and row.get("system_id") in safe_ids
        and row.get("visibility") == "public"
        and row.get("visibility_decision") == "PUBLIC_ELIGIBLE"
        and row.get("promotion_state") in PUBLIC_ADMISSION_STATES
        and isinstance(row.get("source_repository"), str)
    }
    registry = bundle.get("capability_donor_registry", {})
    rows = registry.get("capabilities", []) if isinstance(registry, Mapping) else []
    if not isinstance(rows, list):
        raise ValueError("capability donor registry must expose a capability list")

    packets: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for capability in rows:
        if not isinstance(capability, Mapping):
            continue
        capability_id = capability.get("capability_id")
        if not isinstance(capability_id, str) or capability_id not in allowed_capabilities:
            continue
        proof_refs = capability.get("proof_refs", [])
        if not isinstance(proof_refs, list):
            raise ValueError(f"{capability_id}: proof_refs must be a list")
        for proof in proof_refs:
            if not isinstance(proof, Mapping):
                continue
            if proof.get("source") != "semantic_capability_map":
                continue
            if proof.get("company_id") != company_id:
                continue
            system_id = proof.get("system_id")
            if not isinstance(system_id, str) or system_id not in safe_ids:
                continue
            repository = proof.get("repository")
            if not isinstance(repository, str) or not repository.startswith("GlacierEQ/"):
                raise ValueError(f"{capability_id}: public semantic donor repository is unsafe")
            if (system_id, repository) not in safe_evidence_pairs:
                raise ValueError(
                    f"{capability_id}: semantic donor does not match public ranked evidence"
                )
            head_sha = proof.get("head_sha")
            if not _is_sha(head_sha):
                raise ValueError(f"{capability_id}: public semantic donor head is invalid")
            admission_state = proof.get("admission_state")
            if admission_state not in PUBLIC_ADMISSION_STATES:
                raise ValueError(f"{capability_id}: semantic donor is not publicly admitted")
            proof_state = proof.get("proof_state")
            if not isinstance(proof_state, str) or "VERIFIED" not in proof_state:
                raise ValueError(f"{capability_id}: semantic donor proof state is not verified")

            evidence_refs = proof.get("evidence_refs", [])
            if not isinstance(evidence_refs, list) or not evidence_refs:
                raise ValueError(f"{capability_id}: semantic donor evidence is missing")
            if not all(_is_safe_repo_path(ref) for ref in evidence_refs):
                raise ValueError(f"{capability_id}: semantic donor evidence refs are unsafe")

            receipts = proof.get("proof_receipts", [])
            if not isinstance(receipts, list) or not receipts:
                raise ValueError(f"{capability_id}: semantic donor receipts are missing")
            public_receipts: list[dict[str, Any]] = []
            for receipt in receipts:
                if not isinstance(receipt, Mapping):
                    raise ValueError(f"{capability_id}: semantic donor receipt is invalid")
                if receipt.get("kind") != "check_run":
                    raise ValueError(f"{capability_id}: unsupported public receipt kind")
                receipt_id = receipt.get("id")
                receipt_name = receipt.get("name")
                if not isinstance(receipt_id, int) or receipt_id <= 0:
                    raise ValueError(f"{capability_id}: receipt id is invalid")
                if not isinstance(receipt_name, str) or not receipt_name:
                    raise ValueError(f"{capability_id}: receipt name is invalid")
                if receipt.get("head_sha") != head_sha:
                    raise ValueError(f"{capability_id}: receipt head does not match donor head")
                if receipt.get("conclusion") != "success":
                    raise ValueError(f"{capability_id}: only successful receipts are public")
                public_receipts.append(
                    {
                        "kind": "check_run",
                        "id": receipt_id,
                        "name": receipt_name,
                        "head_sha": head_sha,
                        "conclusion": "success",
                    }
                )

            key = (capability_id, system_id)
            if key in seen:
                continue
            seen.add(key)
            packets.append(
                {
                    "capability_id": capability_id,
                    "system_id": system_id,
                    "source_repository": repository,
                    "head_sha": head_sha,
                    "proof_state": proof_state,
                    "admission_state": admission_state,
                    "evidence_refs": list(evidence_refs),
                    "proof_receipts": public_receipts,
                }
            )

    return sorted(
        packets,
        key=lambda row: (
            str(row["capability_id"]),
            str(row["source_repository"]),
        ),
    )
