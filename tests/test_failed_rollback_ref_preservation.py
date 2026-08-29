from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "obsolete_branches.json"

EXPECTED = {
    "feat/readme-intelligence-mesh": "bfa9547ff2fcb95b8bc8e88856174b2fe9156958",
    "fix/public-product-standard": "c2f60eaf794c81ff3c03318acc1b63c3faed64fa",
}


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_failed_rollback_refs_are_preserved_at_exact_heads() -> None:
    manifest = _manifest()
    restored = {
        entry["name"]: entry
        for entry in manifest["restored_refs_after_failed_transaction"]
    }
    assert set(restored) == set(EXPECTED)
    for name, sha in EXPECTED.items():
        assert restored[name]["expected_head_sha"] == sha
        assert restored[name]["state"] == "RESTORED_AFTER_FAILED_TRANSACTION"
        assert restored[name]["preservation_policy"] == (
            "DO_NOT_RETIRE_WITHOUT_OPERATOR_AUTHORIZATION")


def test_restored_refs_cannot_reenter_retirement_or_delete_queue() -> None:
    manifest = _manifest()
    retired = {entry["name"] for entry in manifest["retired_refs"]}
    deletion_queue = {entry["name"] for entry in manifest["branches"]}
    preserved = {entry["name"] for entry in manifest["preserved_active_refs"]}

    for name in EXPECTED:
        assert name not in retired
        assert name not in deletion_queue
        assert name in preserved
