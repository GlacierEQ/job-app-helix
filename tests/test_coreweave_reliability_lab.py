from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "manifests" / "company_dossiers" / "additional_targets.json"
AUDIT = (
    ROOT
    / "manifests"
    / "application_intelligence"
    / "coreweave_reliability_lab_audit.json"
)

EXPECTED_REPOSITORIES = {
    "GlacierEQ/coreweave-state-fusion": (
        "12c7735836b1bd062129d4252a2f977524880e66"
    ),
    "GlacierEQ/coreweave-temporal-router": (
        "7473183474e107b75847ecdcc750f9f1b669f220"
    ),
    "GlacierEQ/coreweave-circuit-breaker": (
        "6a1a0b86efbfcb0070996647943bf3f255f8f1ed"
    ),
    "GlacierEQ/coreweave-shadow-monitor": (
        "76664f4acde2424be4d7932af1f5dc22c9475f65"
    ),
    "GlacierEQ/coreweave-entropy-engine": (
        "cec62d79fb2930945a021953aaf3cb1f75b462e6"
    ),
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def coreweave_company() -> dict[str, Any]:
    dossier = load(DOSSIER)
    return next(
        company
        for company in dossier["companies"]
        if company["company_id"] == "coreweave"
    )


def test_coreweave_family_is_private_experiment_only() -> None:
    company = coreweave_company()
    assert company["track_state"] == "PRIVATE_RELIABILITY_LAB_EXPERIMENTS"
    assert company["experiment_family"] == "coreweave-reliability-lab"
    repositories = company["repositories"]
    assert {row[0] for row in repositories} == set(EXPECTED_REPOSITORIES)
    assert all(row[2] == "PRIVATE_EXPERIMENT" for row in repositories)
    assert all(row[3] == "private" for row in repositories)


def test_coreweave_audit_is_bound_to_observed_source_blobs() -> None:
    audit = load(AUDIT)
    assert audit["state"] == "PRIVATE_EXPERIMENTS_NOT_RECRUITER_READY"
    decision = audit["family_decision"]
    assert decision["independent_accomplishment_count"] == 0
    assert decision["treat_as_one_rd_family"] is True
    assert decision["recruiter_promotion_allowed"] is False
    rows = {row["repository"]: row for row in audit["repositories"]}
    assert set(rows) == set(EXPECTED_REPOSITORIES)
    for repository, blob_sha in EXPECTED_REPOSITORIES.items():
        assert rows[repository]["source"]["blob_sha"] == blob_sha
        assert rows[repository]["required_next_evidence"]
        assert rows[repository]["defects_or_claim_gaps"]


def test_coreweave_truth_boundary_forbids_unverified_claims() -> None:
    boundary = load(AUDIT)["truth_boundary"]
    assert boundary == {
        "company_affiliation_claimed": False,
        "production_deployment_claimed": False,
        "comparative_performance_claimed": False,
        "failure_prediction_accuracy_claimed": False,
        "novelty_priority_claimed": False,
    }
