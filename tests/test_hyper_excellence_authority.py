from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from job_app_helix.repo_excellence import (
    REQUIRED_EXCELLENT_GATES,
    ExcellenceContractError,
    validate_repo_excellence_record,
)

ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = ROOT / "scripts" / "hyper_excellence_engine.py"


def load_engine_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("hyper_excellence_engine", ENGINE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def promoted_record() -> dict[str, object]:
    return {
        "schema": "glaciereq.repo-excellence.record.v1",
        "identity": {
            "repository": "GlacierEQ/example",
            "repository_id": "123456",
            "canonical_head": "a" * 40,
            "default_branch": "main",
            "lineage_action": "verified",
        },
        "state": "PROMOTED",
        "canonical_role": "SPECIALIST_COMPONENT",
        "scores": {
            "target_architecture": 10.0,
            "current_proof": "A",
            "company_fit": 10.0,
            "canonical_confidence": 1.0,
        },
        "gates": {gate: True for gate in REQUIRED_EXCELLENT_GATES},
        "evolution": {"next_gate": "canonicalize"},
        "proof_receipt": {
            "source_sha": "c" * 40,
            "canonical_merge_sha": "a" * 40,
            "identity": "receipt-example-001",
        },
    }


def test_promoted_record_requires_every_excellence_gate() -> None:
    payload = promoted_record()
    gates = payload["gates"]
    assert isinstance(gates, dict)
    gates["deterministic_tests_pass"] = False

    with pytest.raises(ExcellenceContractError, match="requires every excellence gate"):
        validate_repo_excellence_record(payload)


def test_promoted_record_rejects_synthetic_proof_placeholders() -> None:
    payload = promoted_record()
    receipt = payload["proof_receipt"]
    assert isinstance(receipt, dict)
    receipt["source_sha"] = "HYPER_VALIDATED_SHA256"

    with pytest.raises(ExcellenceContractError, match=r"placeholder proof_receipt\.source_sha"):
        validate_repo_excellence_record(payload)


def test_promoted_record_rejects_non_digest_proof() -> None:
    payload = promoted_record()
    receipt = payload["proof_receipt"]
    assert isinstance(receipt, dict)
    receipt["source_sha"] = "not-a-real-source-digest"

    with pytest.raises(ExcellenceContractError, match="40- or 64-hex digest"):
        validate_repo_excellence_record(payload)


def test_promoted_record_rejects_canonical_merge_from_another_head() -> None:
    payload = promoted_record()
    receipt = payload["proof_receipt"]
    assert isinstance(receipt, dict)
    receipt["canonical_merge_sha"] = "b" * 40

    with pytest.raises(
        ExcellenceContractError,
        match=r"proof_receipt\.canonical_merge_sha to match identity\.canonical_head",
    ):
        validate_repo_excellence_record(payload)


def test_promoted_record_allows_distinct_artifact_source_when_merge_is_bound() -> None:
    payload = promoted_record()
    validated = validate_repo_excellence_record(payload)
    assert validated["proof_receipt"]["source_sha"] == "c" * 40
    assert validated["proof_receipt"]["canonical_merge_sha"] == "a" * 40


def test_promoted_record_rejects_non_git_canonical_head() -> None:
    payload = promoted_record()
    identity = payload["identity"]
    assert isinstance(identity, dict)
    identity["canonical_head"] = "RESOLVED"

    with pytest.raises(
        ExcellenceContractError,
        match=r"identity\.canonical_head to be an exact 40-hex Git commit",
    ):
        validate_repo_excellence_record(payload)


def test_quarantined_engine_cannot_bootstrap_missing_state(tmp_path: Path) -> None:
    module = load_engine_module()
    engine_type = module.HyperExcellenceEngine

    with pytest.raises(ExcellenceContractError, match="synthetic bootstrap is disabled"):
        engine_type(tmp_path)

    assert not (tmp_path / "machine").exists()


def test_quarantined_engine_rejects_invalid_utf8_without_traceback_path(tmp_path: Path) -> None:
    module = load_engine_module()
    engine_type = module.HyperExcellenceEngine
    state_file = tmp_path / "machine" / "excellence-state.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_bytes(b"\xff\xfe")

    with pytest.raises(
        ExcellenceContractError,
        match=r"unreadable machine/excellence-state\.json",
    ):
        engine_type(tmp_path)


def test_quarantined_engine_never_mutates_or_promotes(tmp_path: Path) -> None:
    module = load_engine_module()
    engine_type = module.HyperExcellenceEngine

    state_file = tmp_path / "machine" / "excellence-state.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps(promoted_record(), indent=2), encoding="utf-8")
    before = state_file.read_bytes()

    engine = engine_type(tmp_path)
    with pytest.raises(ExcellenceContractError, match="automatic promotion is quarantined"):
        engine.enforce_all_gates()

    assert state_file.read_bytes() == before
    assert not (tmp_path / "machine" / "promotion_authority.json").exists()
    assert not (tmp_path / "tests").exists()
    assert not (tmp_path / "src").exists()
