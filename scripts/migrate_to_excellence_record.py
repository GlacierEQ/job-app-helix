from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))

from job_app_helix.repo_excellence import (  # noqa: E402
    HISTORICAL_STATE_UPGRADES,
    PRINCIPAL_STATES,
    SIDE_EXIT_STATES,
    validate_repo_excellence_record,
)


LEGACY_HIGH_STATES_REQUIRING_REAL_RECEIPTS = {
    "PROOF_REPRODUCED",
    "PROMOTED",
    "SOURCE_BOUND",
    "EVOLVING",
}


def translate_legacy_state(raw: str) -> tuple[str, str | None]:
    """Translate old lifecycle labels into upward work states.

    This migration does not mint proof. Historical high states are preserved in a
    separate field and resume at OPERABLE until their exact receipts are imported.
    Historical contraction states become recovery work, never retirement authority.
    """

    if raw in HISTORICAL_STATE_UPGRADES:
        return HISTORICAL_STATE_UPGRADES[raw], raw
    if raw in LEGACY_HIGH_STATES_REQUIRING_REAL_RECEIPTS:
        return "OPERABLE", raw
    if raw in PRINCIPAL_STATES or raw in SIDE_EXIT_STATES:
        return raw, None
    return "DISCOVERED", raw


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def migrate() -> None:
    repos = [Path(path) for path in glob.glob("repos/*/machine/excellence-state.json")]
    success = 0

    for state_path in repos:
        try:
            state_data = _load_json(state_path)
            repo_name = state_data.get("repository", state_path.parts[1])

            scores_path = state_path.with_name("excellence-scores.json")
            scores_data = _load_json(scores_path) if scores_path.exists() else {}
            axes = scores_data.get("axes", {})
            t_arch = axes.get("target_architecture", {})
            c_proof = axes.get("current_proof", {}).get("grade", "C")
            c_fit = axes.get("company_fit", {}).get("score", 0.0)
            c_conf = axes.get("reference_confidence", {}).get("score", 0.0)

            t_arch_val = 10.0 if t_arch.get("grade") == "A" else (8.0 if t_arch.get("grade") == "B" else 5.0)
            if c_proof not in {"A", "B", "C", "D", "Q"}:
                c_proof = "C"

            raw_state = str(state_data.get("principal_state", "DISCOVERED"))
            state_val, historical_state = translate_legacy_state(raw_state)
            old_gates = state_data.get("gates", {})

            record = {
                "schema": "glaciereq.repo-excellence.record.v2",
                "identity": {
                    "repository": repo_name,
                    "repository_id": str(repo_name).replace("GlacierEQ/", ""),
                    "source_head": "UNRESOLVED",
                    "default_branch": "main",
                    "lineage_action": "RECONSTRUCT_LINEAGE",
                },
                "state": state_val,
                "reference_role": "INDEPENDENT_SYSTEM",
                "scores": {
                    "target_architecture": float(t_arch_val),
                    "current_proof": str(c_proof),
                    "company_fit": float(c_fit),
                    "reference_confidence": float(c_conf),
                },
                "gates": {
                    "problem_verified": old_gates.get("PROBLEM_VERIFIED", {}).get("status") == "PASS",
                    "unique_value_known": old_gates.get("TARGET_CONTRACT_FROZEN", {}).get("status") == "PASS",
                    "source_identity_known": old_gates.get("IDENTITY_RESOLVED", {}).get("status") == "PASS",
                    "central_mechanism_implemented": old_gates.get("CENTRAL_MECHANISM_PRESENT", {}).get("status") == "PASS",
                    "deterministic_tests_pass": old_gates.get("DETERMINISTIC_PROOF_GREEN", {}).get("status") == "PASS",
                    "adversarial_tests_pass": old_gates.get("ADVERSARIAL_SURVIVAL", {}).get("status") == "PASS",
                    "runtime_behavior_observed": old_gates.get("OPERABLE_AND_OBSERVABLE", {}).get("status") == "PASS",
                    "security_authority_bounded": old_gates.get("AUTHORITY_BOUND", {}).get("status") == "PASS",
                    "proof_receipt_bound_to_sha": old_gates.get("PROOF_RECEIPT_BOUND", {}).get("status") == "PASS",
                    "reusable_capabilities_extracted": old_gates.get("DONOR_PLAN_RESOLVED", {}).get("status") == "PASS",
                    "projections_truth_consistent": False,
                    "evolution_cursor_defined": old_gates.get("EVOLUTION_CURSOR_DEFINED", {}).get("status") == "PASS",
                },
                "evolution": {
                    "next_gate": "RECONSTRUCT_PURPOSE_AND_CAPABILITY",
                    "cursor": "Recover full purpose, lineage, lost capability, complementary donors, and the next strongest implementation checkpoint.",
                },
                "migration": {
                    "historical_principal_state": historical_state,
                    "source": str(state_path),
                    "retirement_authority_preserved": False,
                    "proof_state_promoted_by_migration": False,
                },
            }

            validated = validate_repo_excellence_record(record)
            if validated.get("retirement_authorized") is not False:
                raise ValueError("migration unexpectedly authorized retirement")

            state_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            success += 1
        except Exception as exc:
            print(f"Failed {state_path}: {exc}")

    print(f"Successfully migrated and validated {success}/{len(repos)} repositories.")


if __name__ == "__main__":
    migrate()
