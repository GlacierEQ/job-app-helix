from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "migrate_legacy_authority_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("legacy_authority_migrator", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacy_state() -> dict:
    return {
        "schema": "glaciereq.repo-excellence-state.v1",
        "repository": "GlacierEQ/example",
        "principal_state": "PROMOTED",
        "gates": {
            "PROOF_RECEIPT_BOUND": {"status": "PASS", "evidence": "proof"},
            "AUTHORITY_BOUND": {"status": "PASS", "evidence": "legacy technical grant"},
            "PROJECTION_TRUTH_CLOSED": {"status": "PASS", "evidence": "projection"},
            "CANONICAL_POSITION_RESOLVED": {"status": "PASS", "evidence": "legacy selection"},
            "EVOLUTION_CURSOR_DEFINED": {"status": "PASS", "evidence": "continue"},
        },
        "history": [
            {
                "from": "PROOF_REPRODUCED",
                "to": "PROMOTED",
                "gate": "AUTHORITY_BOUND",
                "result": "PASS",
            }
        ],
    }


def test_state_migration_preserves_legacy_evidence_but_removes_active_authority_gates() -> None:
    module = load_module()
    migrated = module.migrate_state_payload(legacy_state())

    assert migrated["principal_state"] == "PROMOTED"
    assert "AUTHORITY_BOUND" not in migrated["gates"]
    assert "CANONICAL_POSITION_RESOLVED" not in migrated["gates"]
    assert migrated["gates"]["PROJECTION_TRUTH_CLOSED"]["status"] == "PASS"
    assert migrated["project_direction_authority"] == "OPERATOR"
    assert migrated["machine_state_creates_project_authority"] is False
    assert migrated["compatibility_semantics"]["PROMOTED"] == (
        "evidence_bounded_outward_claim_readiness_only"
    )
    assert migrated["historical_legacy_gates"]["AUTHORITY_BOUND"]["status"] == "PASS"
    assert migrated["historical_legacy_gates"]["CANONICAL_POSITION_RESOLVED"]["status"] == "PASS"
    assert migrated["history"][0]["gate"] == "AUTHORITY_BOUND"
    assert migrated["history"][0]["historical_semantics"] == (
        "technical evidence only; no project authority"
    )


def test_legacy_machine_grant_becomes_non_authoritative_compatibility_record() -> None:
    module = load_module()
    legacy = {
        "repository": "GlacierEQ/example",
        "source_sha": "a" * 64,
        "proof_receipt_digest": "b" * 64,
        "not_after": 9999999999.0,
        "mac": "legacy-mac",
        "issuer": "legacy-local-issuer",
        "verified": True,
        "secret_ref": "legacy-fixture-ref",
    }
    current = module.migrate_grant_payload(legacy)

    assert current["status"] == "EVIDENCE_BOUND_NON_AUTHORITATIVE"
    assert current["repository"] == "GlacierEQ/example"
    assert current["source_sha"] == "a" * 64
    assert current["proof_receipt_digest"] == "b" * 64
    assert current["project_direction_authority"] is False
    assert current["repository_lifecycle_authority"] is False
    assert current["cross_repository_authority"] is False
    assert "mac" not in current
    assert "secret_ref" not in current
    assert "not_after" not in current


def test_migration_is_idempotent() -> None:
    module = load_module()
    once = module.migrate_state_payload(legacy_state())
    twice = module.migrate_state_payload(once)
    assert twice == once
