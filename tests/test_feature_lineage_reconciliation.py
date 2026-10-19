"""Feature-level recovery has no destructive or unjustified inference path."""
from __future__ import annotations

import copy
import json

import pytest

from job_app_helix.feature_lineage_reconciliation import LineageError, reconcile_features


def _observation(i, role, truth="verified", trait="backpressure", *, sensitivity="ENGINEERING", outcome="first-build"):
    return {"observation_id": i, "capability_id": "queue-runtime", "facet_id": "bounded-workers",
            "outcome_id": outcome, "intent": "Avoid stalled workers while retaining useful work",
            "implementation": "synthetic test source", "observed_at": "2026-08-01", "role": role,
            "truth": truth, "sensitivity": sensitivity,
            "evidence_refs": ["synthetic:source:" + i],
            "source": {"repository": "Example/Worker", "commit": "a"*40,
                       "path": "src/worker.py", "blob_sha": "b"*40},
            "traits": [{"trait_id": trait, "description": "Bounded work admission", "truth": truth if truth in ("declared", "observed", "verified") else "declared", "evidence_refs": ["synthetic:test:"+i]}],
            "failures": []}


def _payload(*observations):
    return {"schema": "glaciereq.feature-lineage.v1", "estate_snapshot": "synthetic-2026-10-18", "observations": list(observations)}


def test_history_is_composed_not_overwritten():
    historic = _observation("old", "historical")
    current = _observation("current", "current", trait="receipt-chain")
    r = reconcile_features(_payload(historic, current))
    facet = r["features"][0]
    assert len(facet["vertical_history"]) == 2
    assert {x["trait_id"] for x in facet["synthesis_candidates"]} == {"backpressure", "receipt-chain"}
    assert facet["hidden_harm_candidates"][0]["classification"] == "CURRENT_PRESERVATION_UNVERIFIED"
    assert facet["status"] == "COMPOSITION_REVIEW_REQUIRED"
    assert r["mutation_performed"] is False


def test_missing_trait_is_not_declared_an_actual_regression():
    r = reconcile_features(_payload(_observation("old", "historical"), _observation("new", "current", trait="receipts")))
    assert all(x["classification"] != "CURRENT_FAILURE_EVIDENCED" for x in r["features"][0]["hidden_harm_candidates"])


def test_actual_current_failure_is_distinguished_from_missing_proof():
    current = _observation("new", "current", trait="receipts")
    current["failures"] = [{"trait_id": "backpressure", "description": "confirmed deadlock", "truth": "observed", "evidence_refs": ["synthetic:run:7"]}]
    facet = reconcile_features(_payload(_observation("old", "historical"), current))["features"][0]
    assert {x["classification"] for x in facet["hidden_harm_candidates"]} == {"CURRENT_PRESERVATION_UNVERIFIED", "CURRENT_FAILURE_EVIDENCED"}


def test_multiple_recordings_of_one_outcome_do_not_inflate_achievement():
    r = reconcile_features(_payload(_observation("old", "historical"), _observation("copy", "backup")))
    assert r["observation_count"] == 2
    assert r["distinct_substantive_outcome_count"] == 1
    assert r["features"][0]["substantive_outcome_ids"] == ["first-build"]


def test_private_input_cannot_be_projected_as_public():
    facet = reconcile_features(_payload(_observation("old", "historical", sensitivity="LEGAL_PRIVATE")))["features"][0]
    assert facet["sensitivity"] == "INTERNAL_ONLY"


def test_declared_ambition_does_not_gain_executable_proof():
    data = _observation("idea", "historical", truth="declared")
    candidate = reconcile_features(_payload(data))["features"][0]["synthesis_candidates"][0]
    assert candidate["candidate_truth"] == "declared"
    assert candidate["promotion_state"].startswith("not_promoted")


def test_ties_preserve_multiple_donors_not_arbitrary_winner():
    left = _observation("left", "historical")
    right = _observation("right", "successor")
    right["source"]["repository"] = "Example/Elsewhere"
    candidates = reconcile_features(_payload(left, right))["features"][0]["synthesis_candidates"]
    assert len(candidates[0]["coequal_donors"]) == 2


def test_reordered_input_yields_identical_content_receipt():
    left, right = _observation("left", "historical"), _observation("right", "successor")
    a = reconcile_features(_payload(left, right))
    b = reconcile_features(_payload(right, left))
    assert a == b
    assert len(a["receipt_sha256"]) == 64


def test_invalid_or_unsigned_source_is_rejected():
    bad = _observation("bad", "historical")
    bad["source"]["blob_sha"] = "old-code"
    with pytest.raises(LineageError, match="exact 40-hex"):
        reconcile_features(_payload(bad))


def test_no_evidence_no_claim():
    bad = _observation("bad", "historical")
    bad["traits"][0]["evidence_refs"] = []
    with pytest.raises(LineageError, match="evidence_refs"):
        reconcile_features(_payload(bad))


def test_duplicate_observation_is_rejected():
    old = _observation("dup", "historical")
    with pytest.raises(LineageError, match="duplicate observation_id"):
        reconcile_features(_payload(old, copy.deepcopy(old)))


def test_source_rows_are_not_mutated():
    payload = _payload(_observation("first", "historical"))
    before = json.dumps(payload,sort_keys=True)
    reconcile_features(payload)
    assert json.dumps(payload,sort_keys=True) == before


def test_declared_source_cannot_launder_verified_trait():
    candidate = _observation("idea", "historical", truth="declared")
    candidate["traits"][0]["truth"] = "verified"
    with pytest.raises(LineageError, match="beyond its source truth"):
        reconcile_features(_payload(candidate))
