from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from job_app_helix.repo_excellence import ExcellenceContractError, allowed_transition
from job_app_helix.repo_excellence_evolution import validate_evolving_repo_excellence_record

ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = ROOT / "manifests/repo_excellence/apex-github-worker.json"


def _record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def test_apex_evolving_record_is_measured_content_addressed_and_claim_bounded() -> None:
    validated = validate_evolving_repo_excellence_record(_record())

    assert validated["state"] == "EVOLVING"
    assert validated["identity"]["canonical_head"] == (
        "f791c85a81768e72446619b39b5312ef1c768a02"
    )
    assert validated["identity"]["current_evolved_head"] == (
        "346b330bbfd705579b3a4d10d298a89493a98ee6"
    )
    assert validated["evolution_receipt"]["winner"] == "candidate"
    assert validated["evolution_receipt"]["tests_passed"] == 21
    assert validated["evolution_receipt"]["tests_failed"] == 0
    assert validated["company_evidence"]["stage"] == "CLAIM_PROMOTED"
    assert validated["company_evidence"]["claim_ceiling"] == "proof_bound_company_specific"
    assert validated["evolution"]["next_gate"] == "NEXT_MEASURED_EVOLUTION"
    assert allowed_transition("CANONICAL", "EVOLVING", validated["gates"])
    assert not allowed_transition("EVOLVING", "CANONICAL", validated["gates"])


def test_evolving_rejects_receipt_byte_drift() -> None:
    record = _record()
    record["evolution_receipt"]["blob_sha"] = "0" * 40
    with pytest.raises(ExcellenceContractError, match="Git blob SHA"):
        validate_evolving_repo_excellence_record(record)


def test_evolving_rejects_fake_winner_or_head() -> None:
    record = _record()
    record["evolution_receipt"]["winner"] = "baseline"
    with pytest.raises(ExcellenceContractError, match="candidate winner"):
        validate_evolving_repo_excellence_record(record)

    record = _record()
    record["identity"]["current_evolved_head"] = "a" * 40
    with pytest.raises(ExcellenceContractError, match="evolution current head drift"):
        validate_evolving_repo_excellence_record(record)


def test_evolving_rejects_company_claim_inflation() -> None:
    record = _record()
    mutated = copy.deepcopy(record)
    mutated["company_evidence"]["stage"] = "GITHUB_ADOPTED"
    with pytest.raises(ExcellenceContractError):
        validate_evolving_repo_excellence_record(mutated)

    mutated = copy.deepcopy(record)
    mutated["company_evidence"]["claim_ceiling"] = "github_production"
    with pytest.raises(ExcellenceContractError):
        validate_evolving_repo_excellence_record(mutated)
