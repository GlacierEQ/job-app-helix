from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.promotion_invariants import (
    assess_leaf_promotion,
    enforce_nonpromoted_state,
    source_tree_sha,
)


def _seed_leaf(tmp_path: Path, *, scaffold: bool = True) -> Path:
    leaf = tmp_path / "leaf"
    (leaf / "src").mkdir(parents=True)
    (leaf / "tests").mkdir()
    (leaf / "machine").mkdir()
    body = '"""SCAFFOLD STUB"""\nVALUE = 1\n' if scaffold else "VALUE = 1\n"
    (leaf / "src" / "mechanism.py").write_text(body, encoding="utf-8")
    test_body = "def test_value():\n    assert 1 == 1\n"
    (leaf / "tests" / "test_behavior.py").write_text(test_body, encoding="utf-8")
    state = {
        "principal_state": "PROMOTED",
        "scaffold": False,
        "wave": {"phase": "PROMOTED"},
    }
    (leaf / "machine" / "excellence-state.json").write_text(
        json.dumps(state),
        encoding="utf-8",
    )
    return leaf


def _write_valid_proof(leaf: Path) -> None:
    proof = {
        "schema": "glaciereq.implementation-proof.v1",
        "repository": "GlacierEQ/leaf",
        "source_sha": source_tree_sha(leaf),
        "result": "PASS",
        "scaffold": False,
        "behavioral_cases": 3,
        "adversarial_cases": 1,
    }
    proof_path = leaf / "machine" / "implementation-proof.json"
    proof_path.write_text(json.dumps(proof), encoding="utf-8")


def test_scaffold_marker_blocks_false_promoted_state(tmp_path: Path) -> None:
    leaf = _seed_leaf(tmp_path, scaffold=True)
    assessment = assess_leaf_promotion(leaf)
    assert not assessment.eligible
    assert "SCAFFOLD_EVIDENCE_PRESENT" in assessment.reasons
    assert "STATE_SCAFFOLD_CONTRADICTION" in assessment.reasons
    assert "PROMOTED_WITHOUT_IMPLEMENTATION_PROOF" in assessment.reasons


def test_missing_implementation_proof_blocks_non_scaffold_leaf(tmp_path: Path) -> None:
    leaf = _seed_leaf(tmp_path, scaffold=False)
    assessment = assess_leaf_promotion(leaf)
    assert not assessment.eligible
    assert "IMPLEMENTATION_PROOF_MISSING" in assessment.reasons


def test_stale_implementation_proof_is_rejected(tmp_path: Path) -> None:
    leaf = _seed_leaf(tmp_path, scaffold=False)
    _write_valid_proof(leaf)
    proof_path = leaf / "machine" / "implementation-proof.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof["source_sha"] = "0" * 64
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    assessment = assess_leaf_promotion(leaf)
    assert not assessment.eligible
    assert "IMPLEMENTATION_PROOF_SOURCE_SHA" in assessment.reasons


def test_valid_proof_earns_promotion_eligibility(tmp_path: Path) -> None:
    leaf = _seed_leaf(tmp_path, scaffold=False)
    _write_valid_proof(leaf)
    assessment = assess_leaf_promotion(leaf)
    assert assessment.eligible
    assert assessment.reasons == ()


def test_enforcement_downgrades_false_promotion(tmp_path: Path) -> None:
    leaf = _seed_leaf(tmp_path, scaffold=True)
    assessment = assess_leaf_promotion(leaf)
    state_path = leaf / "machine" / "excellence-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    corrected = enforce_nonpromoted_state(state, assessment)
    assert corrected["principal_state"] == "OPERABLE"
    assert corrected["scaffold"] is True
    assert corrected["promotion_eligible"] is False
    assert corrected["wave"]["phase"] == "SCAFFOLD_PROVEN"
